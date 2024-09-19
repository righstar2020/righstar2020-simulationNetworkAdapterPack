

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
from ryu.lib.dpid import str_to_dpid
from ryu.lib.packet import ether_types, icmp, ipv4
from ryu.lib import hub
import json
from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import route
from ryu.app.wsgi import WSGIApplication


class DDoSSimulationAPP(SamplingEntropyCalculator):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication
    }
    def __init__(self, *args, **kwargs):
        super(DDoSSimulationAPP, self).__init__(*args, **kwargs)
        self.is_DDoS_attacking=False
        #异常DDoS行为次数
        self.DDoSing_count=0
        self.datapath=None
        #开启监控器统计协程
        self.logger.info('开启流量采样器!')
        self.datapathInfoMap = {
            #'000000001':{}
        }
        self.trafficEngineerRuleMap = {
            # '0000000000001':{
            #     'ip_white_table':true,
            #     'icmp_drop':true
            # }
        }
        self.datapathInfoMapStr = {

        }
        wsgi = kwargs['wsgi']
        wsgi.register(TrafficEngineerController, {'traffic_engineer_app': self})
        wsgi.register(TrafficEntropyController, {'traffic_entropy_api_app': self})
    
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
    def _add_flow_miss_rule(self,datapath):
        # 安装流表缺失时把数据包发送给控制器(例如有新的IP数据包到来时)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        #流表缺失为最低优先级
        self.add_flow(datapath, 0, match, actions)
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
    #添加TCP封禁
    def add_flow_TCP_drop(self,ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=inet.IPPROTO_TCP)
        actions_drop = []
        self.add_flow(datapath=datapath, priority=3,match=match_icmp, actions=actions_drop)  # 设置较低优先级确保白名单规则先匹配
    
    #添加UDP封禁
    def add_flow_UDP_drop(self,ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=inet.IPPROTO_UDP)
        actions_drop = []
        self.add_flow(datapath=datapath, priority=3,match=match_icmp, actions=actions_drop)  # 设置较低优先级确保白名单规则先匹配
  
    def clear_flow_ICMP_drop(self,ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # 删除ICMP协议封禁
        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=inet.IPPROTO_ICMP)
        self.del_flow(datapath,match=match_icmp,priority=3)
    
   
    def create_defense_flow_rule(self,ev):
        self.add_flow_white_table(ev)
        icmp_rate=self.current_protocol_rate.get('icmp',0)
        self.logger.info(f'icmp rate:{icmp_rate}')
        if icmp_rate>0.3:
            self.add_flow_ICMP_drop(ev)
    def clear_defense_flow_rule(self,ev):
        self.clear_white_table(ev)
        self.clear_flow_ICMP_drop(ev)
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapath = datapath
        #更新datapath信息
        self.datapathInfoMap[datapath.id] = {
            'datapath': datapath,
            'ofproto': ofproto,
            'parser': parser,
            'traffic_sampling':False
        }
        #初始化防御规则
        self.trafficEngineerRuleMap[datapath.id] = {
            'ip_white_table':False,
            'ICMP':False,
            'TCP':False,
            'UDP':False
        }
        self._add_flow_miss_rule(datapath) #流表缺失事件
        all_sampling = False
        if all_sampling :
            self._request_sampling_packets(datapath) #全部交换机进行流量采样
        else:    
            sampling_switch_id_list = ['1','3','5','6','10','12','13']
            for dpid in sampling_switch_id_list:
                if datapath.id == dpid:
                    self._request_sampling_packets(datapath)
                    self.datapathInfoMap[datapath.id]['traffic_sampling'] = True
          

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        super(DDoSSimulationAPP, self).packet_in_handler(ev)
        datapath = ev.msg.datapath
        #更新datapath信息
        if self.trafficEngineerRuleMap.get(ev.msg.datapath.id) !=None:
            switch_defend_rule = self.trafficEngineerRuleMap.get(ev.msg.datapath.id)
            if switch_defend_rule.get('ip_white_table') == True:
                self.ip_white_table(ev)
            if switch_defend_rule.get('ICMP') == True:
                self.add_flow_ICMP_drop(ev)
                #每台交换机只执行一次协议封禁的下发
                self.trafficEngineerRuleMap[ev.msg.datapath.id]['ICMP'] = False
            if switch_defend_rule.get('TCP') == True:
                self.add_flow_TCP_drop(ev)
                #只执行一次协议封禁的下发
                self.trafficEngineerRuleMap[ev.msg.datapath.id]['TCP'] = False
            
            if switch_defend_rule.get('UDP') == True:
                self.add_flow_UDP_drop(ev)
                #只执行一次协议封禁的下发
                self.trafficEngineerRuleMap[ev.msg.datapath.id]['UDP'] = False
            
    def ip_white_table(self,ev):
       #检测DDoS是否发生
        if self.detect_ddos_by_entropy():
            #self.logger.info('检测到流量异常行为!')
            self.DDoSing_count+=1
            #self.logger.info(f'DDoS count:{self.DDoSing_count}')
        else:
            if self.DDoSing_count>20:
                self.DDoSing_count=20
            else:
                self.DDoSing_count-=1 #十次正常熵后则恢复正常

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
                    self.clear_defense_flow_rule(ev)
                    self.is_DDoS_attacking=False
                    self.DDoSing_count=0


class TrafficEngineerController(ControllerBase):
    
    def __init__(self, req, link, data, **config):
        super(TrafficEngineerController, self).__init__(req, link, data, **config)
        self.traffic_engineer_app = data['traffic_engineer_app']
    """
        网络数据接口
    """
    @route('get_datapath_info', '/engineer/get_datapath_info',
           methods=['GET'])
    def get_datapath_info(self, req, **kwargs):
        response = {'status': 'error',
                'data': ''}
        if self.traffic_engineer_app.datapathInfoMapStr != None:
            all_datapath_info = self.traffic_engineer_app.datapathInfoMapStr
            response = {'status': 'success','data': all_datapath_info}
        body = json.dumps(response)
        return Response(content_type='application/json', body=body)
    @route('get_protocol_count', '/engineer/get_protocol_count',
           methods=['GET'])
    def get_protocol_count(self, req, **kwargs):
        response = {'status': 'error',
                'data': ''}
        if self.traffic_engineer_app.protocol_statistic != None:
            protocol_statistic = self.traffic_engineer_app.protocol_statistic
            response = {'status': 'success','data': protocol_statistic}
        body = json.dumps(response)
        return Response(content_type='application/json', body=body)
    """
        流量工程接口
    """
    @route('icmp_drop', '/engineer/protocol_forbid',
           methods=['POST'])
    def protocol_forbid(self, req, **kwargs):
        dpid = req.json['dpid']
        protocol = req.json['protocol']
        response = {'status': 'error',
                'data': dpid}
        if dpid != None:
            #对所有交换机都执行协议封禁操作
            for key in self.traffic_engineer_app.trafficEngineerRuleMap.keys():
                if self.traffic_engineer_app.trafficEngineerRuleMap.get(key) !=None:
                    self.traffic_engineer_app.trafficEngineerRuleMap[key][protocol] = True
                else:
                    self.traffic_engineer_app.trafficEngineerRuleMap[key]={protocol:True}
            response = {'status': 'success','data':dpid}
        body = json.dumps(response)
        return Response(content_type='application/json', body=body)
    
    @route('ip_white_table', '/engineer/set_ip_white_table',
           methods=['POST'])
    def set_ip_white_table(self, req, **kwargs):
        dpid = req.json['dpid']
        response = {'status': 'error','data': {'dpid':dpid}}
        if dpid != None:
            self.traffic_engineer_app.trafficEngineerRuleMap[dpid]['ip_white_table'] = True
        response = {'status': 'success','data': {'dpid':dpid}}
        body = json.dumps(response)
        return Response(content_type='application/json', body=body)
    
    @route('ip_white_table', '/engineer/set_ip_white_table',
           methods=['GET'])
    def set_ip_white_table(self, req, **kwargs):
        dpid = dict(req.GET).get('dpid')
        response = {'status': 'error','data': {'dpid':dpid}}
        if dpid != None:
            if self.traffic_engineer_app.trafficEngineerRuleMap.get(dpid) !=None:
                self.traffic_engineer_app.trafficEngineerRuleMap[dpid]['ip_white_table'] = True
            else:
                self.traffic_engineer_app.trafficEngineerRuleMap[dpid]={'ip_white_table':True}
            response = {'status': 'success','data': {'dpid':dpid}}
        body = json.dumps(response)
        return Response(content_type='application/json', body=body)
    


class TrafficEntropyController(ControllerBase):
    """
        流量熵指标接口
    """
    def __init__(self, req, link, data, **config):
        super(TrafficEntropyController, self).__init__(req, link, data, **config)
        self.traffic_entropy_api_app = data['traffic_entropy_api_app']

    @route('traffic_entropy', '/monitor/traffic_entropy',
           methods=['GET'])
    def get_traffic_entropy(self, req, **kwargs):
        return self._traffic_entropy(req, **kwargs)
    
    def _traffic_entropy(self, req, **kwargs):
        if self.traffic_entropy_api_app.source_ips_entropy_queue == None:
            return Response(content_type='application/json', body='[]')
        if self.traffic_entropy_api_app.destination_ports_entropy_queue == None:
            return Response(content_type='application/json', body='[]') 
        source_ips_entropy = []
        while not self.traffic_entropy_api_app.source_ips_entropy_queue_remote.empty():
            source_ips_entropy.append(self.traffic_entropy_api_app.source_ips_entropy_queue_remote.get())
        destination_ports_entropy = []
        while not self.traffic_entropy_api_app.destination_ports_entropy_queue_remote.empty(): 
            destination_ports_entropy.append(self.traffic_entropy_api_app.destination_ports_entropy_queue_remote.get())
        body = json.dumps({'source_ips_entropy': source_ips_entropy,
                'destination_ports_entropy': destination_ports_entropy})
        return Response(content_type='application/json', body=body)