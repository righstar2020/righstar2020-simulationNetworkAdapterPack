# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from ryu.ofproto.ofproto_v1_3 import OFPC_FLOW_STATS
from ryu.ofproto.ofproto_v1_3 import OFP_DEFAULT_PRIORITY
from ryu.ofproto.ofproto_v1_3 import OFPFC_ADD
from ryu.ofproto.ofproto_v1_3 import OFPG_ANY
from ryu.ofproto.ofproto_v1_3 import OFPPC_NO_PACKET_IN
from ryu.ofproto.ofproto_v1_3 import OFPFF_SEND_FLOW_REM
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch
from ryu.ofproto.ofproto_v1_3_parser import OFPInstruction
from ryu.ofproto.ofproto_v1_3 import OFP_DEFAULT_PRIORITY
from ryu.ofproto.ofproto_v1_3 import OFPFC_ADD
from ryu.ofproto.ofproto_v1_3 import OFPG_ANY
from ryu.ofproto.ofproto_v1_3 import OFPP_ALL
from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import ipv4
from collections import Counter
import math

class TrafficEntropyMonitor(simple_switch_13.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        super(TrafficEntropyMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.src_ip_entropy={}
        self.dst_port_entropy={}
        self.Traffic_Counter_TABLE_ID=None
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            #1秒监听一次
            hub.sleep(1)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPFlowStatsRequest(datapath, 0, ofp.OFPTT_ALL, ofp.OFPP_ANY, ofp.OFPG_ANY, 0, 0, 666)
        datapath.send_msg(req)
        #下发流表规则进行统计
        if self.Traffic_Counter_TABLE_ID==None:
            self.Traffic_Counter_TABLE_ID=666

             # 创建一个尽可能匹配所有数据包的流表项
            match = parser.OFPMatch(wildcards=OFPP_ALL)


            # 添加统计动作（这里以Meter为例，实际上有些交换机可能不支持Meter用于精确的统计，此时可以考虑Counter）
            actions = [parser.OFPActionMeter(meter_id=777)]

            # 创建并添加流表项
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=OFP_DEFAULT_PRIORITY,
                                    match=match, instructions=inst, table_id=self.Traffic_Counter_TABLE_ID,
                                    flags=OFPFF_SEND_FLOW_REM | OFPPC_NO_PACKET_IN)
            datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                             ev.msg.datapath.id,
                             stat.match['in_port'], stat.match['eth_dst'],
                             stat.instructions[0].actions[0].port,
                             stat.packet_count, stat.byte_count)
        stats = [flow_stat for flow_stat in ev.msg.body]

        # 收集源IP地址及其出现次数
        src_ips = [ipv4.ipv4_addr_to_int(flow_stat.match.get_field('ipv4_src').value) for flow_stat in stats if 'ipv4_src' in flow_stat.match.fields]
        for flow_stat in stats:
            if 'ipv4_src' in flow_stat.match.fields:
                print(f"{flow_stat}")
            print(f"{flow_stat}")
        src_ip_counter = Counter(src_ips)

        # 计算源IP地址熵
        total_packets = sum(src_ip_counter.values())
        src_ip_probabilities = [count / total_packets for count in src_ip_counter.values()]
        self.src_ip_entropy[ev.msg.datapath.id] = -sum(p * math.log2(p) for p in src_ip_probabilities if p > 0)

        # 收集目的端口及其出现次数
        dst_ports = [flow_stat.match.get_field('in_port').value for flow_stat in stats if 'in_port' in flow_stat.match.fields]
        dst_port_counter = Counter(dst_ports)

        # 计算目的端口熵
        dst_port_probabilities = [count / total_packets for count in dst_port_counter.values()]
        self.dst_port_entropy[ev.msg.datapath.id] = -sum(p * math.log2(p) for p in dst_port_probabilities if p > 0)

        # 输出熵值
        print(f"Source IP entropy for DPID {ev.msg.datapath.id}: {self.src_ip_entropy[ev.msg.datapath.id]}")
        print(f"Destination port entropy for DPID {ev.msg.datapath.id}: {self.dst_port_entropy[ev.msg.datapath.id]}") 

        

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
        for stat in sorted(body, key=attrgetter('port_no')):
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)

