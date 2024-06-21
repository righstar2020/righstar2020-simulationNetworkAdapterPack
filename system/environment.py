import psutil
def get_cpu_memory_usage():
    # 获取CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)  # interval参数指定了采样时间，单位是秒

    # 获取内存信息
    memory_info = psutil.virtual_memory()
    memory_total = memory_info.total / (1024.0 ** 3)  # 总内存，转换为GB
    memory_used = memory_info.used / (1024.0 ** 3)  # 已用内存，转换为GB
    memory_percent = memory_info.percent  # 内存使用百分比

    print(f"CPU 使用率: {cpu_percent}%")
    print(f"内存总大小: {memory_total:.2f} GB")
    print(f"内存已用: {memory_used:.2f} GB ({memory_percent}%)")
    return cpu_percent,memory_percent
    