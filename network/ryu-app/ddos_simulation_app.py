

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser as parser
from sampling_entropy_calculator_app import SamplingEntropyCalculator
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.controller import ofp_event
from ryu.ofproto import inet
from ryu.lib.packet import ether_types, ipv4
from ryu.lib.packet import ether_types, icmp, ipv4
from ryu.lib import hub
import ipaddress
import queue


class DDoSSimulationAPP(SamplingEntropyCalculator):
    
    def __init__(self, *args, **kwargs):
        super(DDoSSimulationAPP, self).__init__(*args, **kwargs)
        self.is_DDoS_attacking=False
        #异常DDoS行为次数
        self.DDoSing_count=0
        self.datapath=None
        #开启监控器统计协程
        self.logger.info('开启流量采样器!')
        #self.monitor_thread = hub.spawn(self._monitor)
    def _monitor(self):
        while True:
            if self.datapath!=None:
                self._request_sampling_packets(self.datapath)
            #每5s请求一次统计数据包
            hub.sleep(5)

    def _request_sampling_packets(self, datapath,hard_timeout=0):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # 设置采样流表项
        match = parser.OFPMatch()  # 匹配所有数据包
        #ofproto.OFPCML_NO_BUFFER设置将数据包发送到控制器
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)  #
        ]
        #注意设置优先级比自动转发高
        self.add_flow(datapath=datapath,priority= 99, match = match, actions = actions)
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    idle_timeout=0,  # 不设置空闲超时
                                    hard_timeout=0,  # 不设置硬超时
                                    flags=ofproto.OFPFF_SEND_FLOW_REM,  
                                    buffer_id=ofproto.OFP_NO_BUFFER,
                                    out_port=ofproto.OFPP_ANY,
                                    out_group=ofproto.OFPG_ANY
                                    )
        datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapath = datapath
        self._request_sampling_packets(datapath)
        #记录datapath
    def add_flow_white_table(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.logger.info('添加IP白名单')
        # 添加允许白名单IP地址的规则
        for ip in self.white_ip_table:
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip)
            actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath=datapath, priority=4,match= match, actions=actions)  # 设置较高优先级

        # 添加默认丢弃所有其它IP流量的规则
        match_all = parser.OFPMatch()
        actions_drop = []
        self.add_flow(datapath=datapath,  priority=2, match=match_all,actions= actions_drop)  # 设置较低优先级，但高于正常的转发优先级
    
    #清除白名单流表
    def clear_white_table(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for ip in self.ip_white_list:
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip)
            self.del_flow(datapath,match=match,priority=4)

        match_all = parser.OFPMatch()
        self.del_flow(datapath,match=match_all,priority=2)
    #添加ICMP封禁
    def add_flow_ICMP_drop(self,ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # 禁止ICMP协议
        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=inet.IPPROTO_ICMP)
        actions_drop = []
        self.add_flow(datapath=datapath, priority=3,match=match_icmp, actions=actions_drop)  # 设置较低优先级确保白名单规则先匹配
    def clear_flow_ICMP_drop(self,ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # 删除ICMP协议封禁
        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=inet.IPPROTO_ICMP)
        self.del_flow(datapath,match=match_icmp,priority=3)
    def del_flow(self,datapath,match,priority):
        # 删除特定流表
        mod = parser.OFPFlowMod(
                        datapath=datapath,
                        command=datapath.ofproto.OFPFC_DELETE,
                        out_port=datapath.ofproto.OFPP_ANY,
                        out_group=datapath.ofproto.OFPG_ANY,
                        idle_timeout=0,  # 不设置空闲超时
                        hard_timeout=0,  # 不设置硬超时
                        match=match,  # 匹配条件
                        priority=priority,  # 之前设置的流表项优先级
                    )
        datapath.send_msg(mod)
   
    def create_defense_flow_rule(self,ev):
        self.add_flow_white_table(ev)
        icmp_rate=self.current_protocol_rate.get('icmp',0)
        self.logger.info(f'icmp rate:{icmp_rate}')
        if icmp_rate>0.5:
            self.add_flow_ICMP_drop(ev)
    def clear_defense_flow_rule(self,ev):
        self.clear_white_table(ev)
        self.clear_flow_ICMP_drop(ev)
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        super(DDoSSimulationAPP, self).packet_in_handler(ev)
        #检测DDoS是否发生
        if self.detect_ddos_by_entropy():
            #self.logger.info('检测到流量异常行为!')
            self.DDoSing_count+=1
            #self.logger.info(f'DDoS count:{self.DDoSing_count}')
        #超过5次流量熵异常行为则认为发生了DDoS
        if  self.DDoSing_count>10:
            if not self.is_DDoS_attacking:
                self.logger.info('创建防御流表规则')
                self.logger.info(f'DDoS count:{self.DDoSing_count}')
                self.create_defense_flow_rule(ev)
                self.is_DDoS_attacking = True
        else:
            if self.is_DDoS_attacking:
                if not self.detect_ddos_by_entropy():
                    self.logger.info('流量恢复正常,清除防御协议')
                    #self.clear_defense_flow_rule(ev)
                    self.is_DDoS_attacking=False
                    self.DDoSing_count=0
