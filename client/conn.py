import asyncio
import json
import time
import random
import logging
from asyncio import TimeoutError
from controller.task_controller import TaskController

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Client:
    MAX_RETRIES = 5  # 最大重试次数
    RETRY_DELAY = 5  # 重试间隔时间（秒）

    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.taskQueue = None
        self.taskResultQueue = None
        self.taskController = None
        self.is_reconnecting = False  # 使用布尔值简化锁定逻辑
    def _init_params(self):
        """初始化参数"""
        #必须在同一事件循环中初始化
         #要在协程内定义对象
        self.reader = None
        self.writer = None
        self.taskQueue = asyncio.Queue()
        self.taskResultQueue = asyncio.Queue()
        self.taskController = TaskController(self)
    async def _establish_connection(self):
        """内部方法，仅用于建立连接，不包含重试逻辑"""
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.server_ip, self.server_port), timeout=40)
            logging.info(f'Connected to {self.server_ip}:{self.server_port} success!')
        except Exception as e:
            logging.error(f'Connection info: {self.server_ip, self.server_port}')
            logging.error(f'Connection attempt failed: {e}')
            raise Exception("Failed to connect to the server.")

    async def connect_to_server(self):
        """连接到服务器并实现重试逻辑"""
        if self.is_reconnecting:
            return
        self.is_reconnecting = True
        retries = 0
        while retries <= self.MAX_RETRIES:
            try:
                await self._establish_connection()
                self.is_reconnecting = False
                return
            except Exception as e:
                logging.error(f'Connection timed out. Retrying in {self.RETRY_DELAY} seconds... (Attempt #{retries + 1})')
                retries += 1
                await asyncio.sleep(self.RETRY_DELAY)
        logging.critical('Failed to establish connection after maximum retries.')
        raise Exception("Failed to connect to the server.")

    async def _safe_send(self, message):
        """安全发送消息，处理可能的连接关闭情况"""
        if self.writer and not self.writer.is_closing():
            self.writer.write(message.encode() + b'\n')  # 确保消息末尾有换行
            await asyncio.wait_for(self.writer.drain(), timeout=600)

    async def send_heartbeat(self):
        """客户端心跳发送函数"""
        logging.info("send heartbeat started.")
        while True:
            await asyncio.sleep(20)
            try:
                heartbeat_data = {"type": "heartbeat", "timestamp": int(time.time())}
                logging.info(f"send_heartbeat-->: {heartbeat_data}")
                await self._safe_send(json.dumps(heartbeat_data))
            except Exception as e:
                logging.warning(f"Heartbeat failed, attempting to reconnect: {e}")
                await self.connect_to_server()

    # 其他方法如 receive_messages, process_tasks, send_results 保持原逻辑，但确保在适当的地方使用 _safe_send 和更好的异常处理
    async def receive_messages(self):
        """接收服务器消息并放入任务队列"""
        logging.info("receive messages started.")
        while True:
            try:
                data_raw = await self.reader.readline()
                try:
                    data=json.loads(data_raw.decode().strip())
                    logging.info(f"data from server :{data}.")
                    if data.get("type") == "heartbeat":
                        #如果是心跳包直接忽略
                        pass
                    elif data.get("type") == "task":
                        self.taskQueue.put_nowait(data)  # 将消息放入任务队列
                    else:
                        logging.warning(f"unkown type:{data}")
                except Exception as e:
                    logging.warning(f"receive_messages-->Unable to decode data: {data_raw}")                
            except Exception as e:
                logging.warning(f"receive_messages-->Connection lost: Attempting to reconnect...")
                #等待一个心跳后重试
                await asyncio.sleep(5)
                # 尝试重新连接
                await self.connect_to_server()

    async def process_tasks(self):
        """处理任务队列中的任务并将结果放入结果队列"""
        logging.info("process tasks started.")
        while True:
            try:
                task_data = await self.taskQueue.get()
                try:
                    logging.info(f"process tasks:{task_data}.")
                    processed_result = await self.taskController.execute_task(task_data)
                    processed_result['task_id'] = task_data['task_id']
                    await self.taskResultQueue.put(processed_result)  # 处理结果放入结果队列
                    logging.info(f"process tasks success:{processed_result}.")
                except Exception as e:
                    logging.warning(f"process tasks fail-->: {e}")
                    processed_result = {'task_id': task_data['task_id'], 'result': 'error', 'status':'error','message': str(e)}
                    await self.taskResultQueue.put(processed_result)
            except Exception as e:
                logging.critical(f"Error occurred while processing task:{e}",)
                continue

            
            
    async def send_results(self):
        """从结果队列中取出结果并发送回服务器"""
        while True:
            result = await self.taskResultQueue.get()
            try:
                logging.info(f"send process results:{result}.")
                logging.info(f"send results-->: {result}")
                await self._safe_send(json.dumps(result))
            except Exception as e:
                logging.warning(f"send_results-->Connection lost: Attempting to reconnect...")
                #结果放回队列
                await self.taskResultQueue.put(result)
                #等待一个心跳后重试
                await asyncio.sleep(random.uniform(5, 10))
                # 尝试重新连接
                await self.connect_to_server()
    async def put_task_result(self, task_data):
        """将任务结果放入结果队列"""
        await self.taskResultQueue.put(task_data)
    async def run(self):
        """客户端主运行逻辑，包含连接重试逻辑"""
        self._init_params()
        tasks = []
        try:
            while True:
                await self.connect_to_server()
                tasks.extend([
                    asyncio.create_task(self.receive_messages()),
                    asyncio.create_task(self.process_tasks()),
                    asyncio.create_task(self.send_results()),
                    asyncio.create_task(self.send_heartbeat())
                ])
                await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            logging.info("Client shutdown completed.")

