#监控仿真网络及环境状态
import psutil
import asyncio
class MonitorService:
    def __init__(self) -> None:
        self.conn = None
        self.tiny_db = None
    