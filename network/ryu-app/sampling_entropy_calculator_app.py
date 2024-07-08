from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser as parser
from ryu.app import simple_switch_13
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
import json
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication
#from flask import Flask, jsonify
import threading,time
import queue
import math

class SamplingEntropyCalculator(app_manager.RyuApp):
    # OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    # _CONTEXTS = {
    #     'wsgi': WSGIApplication
    # }
    SAMPLE_RATE = 5  # 设置采样率，每N个数据包采样一个
    def __init__(self, *args, **kwargs):
        super(SamplingEntropyCalculator, self).__init__(*args, **kwargs)
        #白名单
        self.white_ip_table={}
        #存储数据不要存太多采样数据，防止内存溢出
        self.sample_queue = queue.Queue(100)  # 创建一个队列对象
        self.packet_count = 0 #当前收集的包数量
        self.sample_count = 0 #当前采样计数
        self.sample_static_count=0
        self.mac_to_port={}
        #曾经出现过的IP都会被记录
        self.source_ips= {}
        self.destination_ports={}
        #计算熵信息
        self.source_ips_entropy_queue = queue.Queue(8)  
        self.destination_ports_entropy_queue = queue.Queue(8)
        self.protocol_rate_queue = queue.Queue(8)
        #发送给远程监控器的数据
        self.source_ips_entropy_queue_remote = queue.Queue(20)  
        self.destination_ports_entropy_queue_remote = queue.Queue(20)
        #协议计数
        self.protocol_count = {}
        #统计不同协议的数量(TCP,UDP,ICMP)
        self.protocol_statistic={
            "TCP":0,
            "UDP":0,
            "ICMP":0,
            "other":0
        }
        
        self.current_source_ips_entropy = queue.Queue()  
        self.current_destination_ports_entropy = queue.Queue()  
        self.current_protocol_rate = {}

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        
        mod = parser.OFPFlowMod(datapath=datapath, 
                        priority=priority,
                        match=match, 
                        instructions=inst,
                        idle_timeout=0,  # 不设置空闲超时
                        hard_timeout=0,  # 不设置硬超时
                        flags=ofproto.OFPFF_SEND_FLOW_REM,  
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        out_port=ofproto.OFPP_ANY,
                        out_group=ofproto.OFPG_ANY)
        datapath.send_msg(mod)
    def packet_in_handler(self, ev):
        #每个数据包进行路由表学习，保证数据包能够正常转发
        self.swicth_mac_to_port(ev)
        #采样率
        self.sample_count += 1
        if self.sample_count % self.SAMPLE_RATE!=0:
            return 
        self.sample_count = 0
        msg = ev.msg
        #采样全部入口数据包
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        #icmp是网络层的协议不属于UDP和TCP
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        if tcp_pkt is not None:
            self.protocol_statistic["TCP"]+=1
        elif udp_pkt is not None:
            self.protocol_statistic["UDP"]+=1
        elif icmp_pkt is not None:
            self.protocol_statistic["ICMP"]+=1
        else:
            self.protocol_statistic["other"]+=1
        
        if ipv4_pkt is not None:
            src_ip = ipv4_pkt.src
            dst_ip = ipv4_pkt.dst
            # self.logger.info(f"packet src_ip dst_port:{src_ip},{dst_ip}")
            # self.logger.info(f"protocol:{tcp_pkt},{udp_pkt}")
            sample_data = {
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'dst_port': 0,
            } 
            #判断ipv4_pkt是何种协议ICMP
            if icmp_pkt!=None:
                sample_data['protocol']='icmp'
            elif tcp_pkt!=None:
                sample_data['protocol']='tcp'
            elif udp_pkt!=None:
                sample_data['protocol']='udp'
            else:
                sample_data['protocol']='other'

            if tcp_pkt is not None or udp_pkt is not None:
                dst_port = tcp_pkt.src_port if tcp_pkt else udp_pkt.src_port
                sample_data['dst_port']=dst_port
            if not self.sample_queue.full():
                self.sample_queue.put(sample_data)  # 将采样数据放入队列
        #TODO 检测IPv6数据包

        self.packet_count += 1
        #每50个包统计一次
        if self.packet_count >50:
            self.packet_count=0
            self.process_sample_queue()
    #交换机路由表学习
    def swicth_mac_to_port(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        

        # learn a mac address to avoid FLOOD next time.
        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 0, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 0, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)



    def process_sample_queue(self):
        #统计次数
        # while True:
        try:
            while not self.sample_queue.empty():
                sample_data = self.sample_queue.get()  # 阻塞等待，最长1秒
                src_ip = sample_data['src_ip']
                dst_ip = sample_data['dst_ip']
                dst_port = sample_data['dst_port']
                protocol = sample_data['protocol']
                #判断src_ip和dst_port是否存在
                self.source_ips[src_ip] =  self.source_ips.get(src_ip, 0)+1
                self.destination_ports[dst_port] = self.destination_ports.get(dst_port, 0) + 1
                if protocol != None:
                     self.protocol_count[protocol] = self.protocol_count.get(protocol, 0) + 1 
            #计算源IP和目的端口的熵
            source_ips_entropy = self.calculate_entropy(self.source_ips)
            destination_ports_entropy = self.calculate_entropy(self.destination_ports)
            if not self.source_ips_entropy_queue.full():
                self.source_ips_entropy_queue.put(source_ips_entropy)
            if not self.destination_ports_entropy_queue.full(): 
                self.destination_ports_entropy_queue.put(destination_ports_entropy)
            #发送给远程监控器
            if not self.source_ips_entropy_queue_remote.full():
                self.source_ips_entropy_queue_remote.put(source_ips_entropy)
            if not self.destination_ports_entropy_queue_remote.full(): 
                self.destination_ports_entropy_queue_remote.put(destination_ports_entropy)
            self.logger.info(f"current source ips entropy: {source_ips_entropy}")
            self.logger.info(f"current destination ports entropy: {destination_ports_entropy}")
            # #计算不同协议的比例
            current_protocol_rate = self.calculate_protocol_ratio(self.protocol_count)
            if not self.protocol_rate_queue.full():
                self.protocol_rate_queue.put(current_protocol_rate)
            self.logger.info(f"current protocol rate: {current_protocol_rate}")
            #更新流量熵
            self.current_source_ips_entropy.put(source_ips_entropy)
            self.current_destination_ports_entropy.put(destination_ports_entropy)
            #更新协议比例
            self.current_protocol_rate = current_protocol_rate
            self.sample_static_count+=1
            #每3秒清空一次信息(3s为一个流量统计窗口)
            if  self.sample_static_count>3:
                self.sample_static_count=0
                #如果熵比较低且稳定则把ip加入白名单
                if source_ips_entropy<0.5 and destination_ports_entropy<0.5:
                    self.logger.info("source ips entropy is low and stable, add ip to whitelist")
                    self.logger.info("destination ports entropy is low and stable, add port to whitelist")
                    #添加ip到白名单
                    for ip in self.source_ips.keys():
                        self.white_ip_table[ip]=True
                    self.logger.info(f"current whitelist:{self.white_ip_table}")
                #对记录信息进行清空
                self.source_ips={}
                self.destination_ports={}
                self.current_protocol_rate={}
        except self.sample_queue.empty():
            pass  # 若队列为空，忽略并继续循环
    #检测到发生DDoS攻击
    def detect_ddos_by_entropy(self):
        source_ips_entropy=0
        destination_ports_entropy=0
        if not self.current_source_ips_entropy.empty():
            source_ips_entropy=self.current_source_ips_entropy.get()
        if not self.current_destination_ports_entropy.empty():
            destination_ports_entropy=self.current_destination_ports_entropy.get()
        #判断是否发生DDoS攻击
        if source_ips_entropy > 1 or destination_ports_entropy > 1:
            return True
        return False
    #计算不同协议的比例
    def calculate_protocol_ratio(self,protocol_count):
        total_packets = sum(protocol_count.values())
        protocol_ratio = {}
        for protocol, count in protocol_count.items():
            ratio = count / total_packets
            protocol_ratio[protocol] = ratio
        return protocol_ratio
    #计算熵的函数
    def calculate_entropy(self,counts):
        total = sum(counts.values())
        entropy = 0
        for count in counts.values():
            if count > 0:
                probability = count / total
                entropy -= probability * math.log2(probability)
        return entropy
    def __del__(self):
        self.processing_thread.join()  # 在应用程序结束时等待处理线程完成
        #self.flask_thread.join()  # 在应用程序结束时等待 Flask 线程完成




