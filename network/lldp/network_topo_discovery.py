from scapy.all import *
import networkx as nx
import matplotlib.pyplot as plt
def lldp_callback(pkt):
    if pkt.haslayer(LLDPDU):
        chassis_id = pkt[LLDPDU].tlvlist[0].chassis_id.subtype
        port_id = pkt[LLDPDU].tlvlist[1].port_id.subtype
        # 处理 LLDP 信息，可以将其存储到一个数据结构中
        print(pkt)
sniff(prn=lldp_callback, filter="ether proto 0x88cc", store=0)


# 创建一个空的有向图
G = nx.DiGraph()

# 添加节点和边
for device in devices:
    G.add_node(device.id, label=device.id)  # 添加设备节点
    for neighbor in device.neighbors:
        G.add_edge(device.id, neighbor.id)  # 添加邻居节点

# 绘制网络拓扑图
pos = nx.spring_layout(G)  # 使用 Spring Layout 算法布局节点位置
nx.draw_networkx_nodes(G, pos, node_color='r', node_size=500)
nx.draw_networkx_edges(G, pos, edge_color='b')
nx.draw_networkx_labels(G, pos, font_color='w')

plt.axis('off')
plt.show()