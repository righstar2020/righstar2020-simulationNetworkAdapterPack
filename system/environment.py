import psutil
from system.command import execute_cmd
#计算CPU和内存使用率
async def get_cpu_memory_usage():
    # 获取CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)  # interval参数指定了采样时间，单位是秒

    # 获取内存信息
    memory_info = psutil.virtual_memory()
    memory_total = memory_info.total / (1024.0 ** 3)  # 总内存，转换为GB
    memory_used = memory_info.used / (1024.0 ** 3)  # 已用内存，转换为GB
    memory_percent = memory_info.percent  # 内存使用百分比

    # print(f"CPU 使用率: {cpu_percent}%")
    # print(f"内存总大小: {memory_total:.2f} GB")
    # print(f"内存已用: {memory_used:.2f} GB ({memory_percent}%)")
    return cpu_percent,memory_percent
    
async def env_monitor_loop():
    """
        持续监听丢包率和延迟以及带宽总用量
    """
    iperf3_json_data = execute_cmd("iperf3 -c 10.0.0.1 -J")
    return iperf3_json_data
#iperf3计算到达目标节点的丢包率
async def get_iperf3_test_data():
    iperf3_json_data = execute_cmd("iperf3 -c 10.0.0.1 -J -t 1")
    return iperf3_json_data

#ping计算到达目标节点的延迟
async def get_ping_delay_data(ip='10.0.0.1'):
    delay_time = execute_cmd(f"ping -c 1 {ip} | grep -oP 'time=\K[\d.]+'")
    return delay_time
