import asyncio
import logging
import json
import uuid
import time
import hashlib
from db.tiny_db import  TinyDBUtil
from asyncio import StreamReader,StreamWriter
logging.basicConfig(filename='./server.log',level=logging.INFO)

class ClientConnectServer:
    def __init__(self):
        self.ip = None
        self.port = None
        self.timeout = None
        self.socket = None
        self.task_distributor = None
        self.heartbeat_monitor_task = None
        self.task_queue = None # 任务队列
        self.task_result_queue = None  # 结果队列
        self.connected_clients = {}  # 以IP地址为主键的客户端信息字典
    def _init_params(self, taskQueue = None, taskResultQueue =None,DBUtil = None):
        """初始化参数"""
        #必须在同一事件循环中初始化
        self.taskQueue = taskQueue
        self.taskResultQueue = taskResultQueue
        self.dbUtil = DBUtil
        if self.taskQueue == None:
            self.taskQueue = asyncio.Queue()  # 任务队列
        if self.taskResultQueue == None:
            self.taskResultQueue = asyncio.Queue()  # 结果队列
        if self.dbUtil == None:
            self.dbUtil = TinyDBUtil()
            self.dbUtil.init_db()
        self.connected_clients = {}  # 以IP地址为主键的客户端信息字典

    async def send_test_task(self):
        # 示例任务数据结构，添加到队列时应包含客户端IP
        attacker_task_data = { 
            'player':'attacker',
            'client_ip':'10.0.0.1',#攻击者主机
            'task_type':'signal',
            'task_name':'host_scan',
            'status':'running',
            'params':{
                'target_ip':'10.0.0.4'
            }
        }
        defender_task_data = { 
            'player':'defender',
            'client_ip':'10.0.0.4',#防御者主机
            'task_type':'signal',
            'task_name':'host_deception',#主机伪装
            'status':'running',
            'params':{
                'target_ip':'10.0.0.4',
                'port':80,
                'request_delay_min':1,
                'request_delay_max':5
            }
        }
        attacker_task = await self.create_task(attacker_task_data)
        defender_task = await self.create_task(defender_task_data)
        
        return {"attacker_task_data":attacker_task,"defender_task_data":defender_task}
    async def _safe_send(self,writer:StreamWriter, data):
        """安全发送消息，处理可能的连接关闭情况"""
        if writer and not writer.is_closing():
            data_str = json.dumps(data)
            writer.write(data_str.encode() + b'\n')  # 确保消息末尾有换行
            await asyncio.wait_for(writer.drain(), timeout=30)
    async def handle_heartbeat(self, writer:StreamWriter,client_ip: str) -> None:
        """处理心跳包，更新心跳时间"""
        logging.info(f"Heartbeat from {client_ip}.")
        self.connected_clients[client_ip]['last_heartbeat_time'] = time.time()
        
    async def handle_task_result(self, task_result,client_ip) -> None:
        """任务处理结果"""
        await self.update_task(task_result)
        logging.info(f"Task result from {client_ip} stored.")
    
    async def handle_rpc(self, reader:StreamReader, writer:StreamWriter, client_address: tuple) -> None:
        """处理单个客户端的RPC请求"""
        client_ip = client_address[0]
        client_port = client_address[1]
        self.connected_clients[client_ip] = {
            'writer': writer,
            'reader': reader,
            'client_ip':client_ip,
            'client_port':client_port,
            'last_heartbeat_time': time.time()
        }
        logging.info(f"{client_address} connected.")
        try:
            while True:
                try:
                    data_raw = await reader.readline()
                    data=json.loads(data_raw.decode().strip())
                    logging.info(f"data from {client_ip}:{data}")
                    if data.get("type") == "heartbeat":
                        await self.handle_heartbeat(writer,client_ip)
                    if data.get("type") == "task_result":
                        await self.handle_task_result(data,client_ip)

                except Exception as e:
                    logging.warning(f"err: {e}")
                    if reader.exception:
                        break
            
        finally:
            del self.connected_clients[client_ip]
            logging.info(f"Connection closed from {client_address}.")
    async def heartbeat_monitor(self):
        logging.info(f"heartbeat monitor start.")
        while True:
            await asyncio.sleep(5)  # 每5秒检查一次
            logging.info(f"server heartbeat! client count:{len(self.connected_clients)}.")
            # """需要返回数据以保持连接""" 
            # for client_ip, client_info in self.connected_clients.items():
            #     writer = client_info['writer']
            #     logging.info(f"server heartbeat  send to {client_ip}.")
            #     try:
            #         await self._safe_send(writer,{'data':'ok','type':'heartbeat'})
            #     except Exception as e:
            #         logging.warning(f"err: {e}.")
            # clients_to_remove = [ip for ip, client in self.connected_clients.items() if client.get('last_heartbeat_time', 0) + 40 < time.time()]
            # for ip in clients_to_remove:
            #     logging.info(f"Removing inactive client: {ip}")
            #     del self.connected_clients[ip]
    async def distribute_tasks(self):
        logging.info(f"distribute tasks start.")
        """分发任务给客户端"""
        while True:
            task_data = await self.taskQueue.get()
            if task_data.get('client_type') == 'switch':
                #some task executed by switch
                await self.distribute_swicth_tasks(task_data)
                continue

            client_ip = task_data.get('client_ip')
            client_info = self.connected_clients.get(client_ip)       
            if client_info:
                client_writer = client_info['writer']
                try:
                    await self._safe_send(client_writer,{'data':task_data,'type':'task'})
                    logging.info(f"Task sent to client {client_ip}: {task_data}")
                except Exception as e:
                    logging.warning(f"Failed to send task to {client_ip}: {e}")
                    # 将任务重新放回队列
                    await self.taskQueue.put(task_data)
            else:
                logging.warning(f"No active connection for IP: {client_ip}, task {task_data['task_id']} cannot be distributed.")
                #主机断连则直接返回执行错误
                task_result_data = task_data
                task_result_data['status'] = 'error'
                task_result_data['message'] = 'No active connection for IP:'+client_ip
                await self.update_task(task_result_data)
    async def distribute_swicth_tasks(self,task):
        """处理交换机执行的任务"""
        
        pass
    async def update_task(self, task_data):
        #按task_id更新任务状态
        try:
            await self.dbUtil.async_upsert_by_key('operation_task_data',task_data,'task_id',task_data['task_id'])
        except Exception as e:
            logging.warning(f"Failed to write task result to database: {e}")
        
        logging.info(f"task result write success!-->task id:{task_data['task_id']}")
    async def create_task_list(self, task_data_list):
        task_list_return = []
        for task_data in task_data_list:
           task_return = await self.create_task(task_data)
           task_list_return.append(task_return)
        return task_list_return
    async def check_task_vaild(self, task_data):
        if task_data.get('task_type') == None or task_data.get('params') == None:
            return False
        if task_data.get('task_name') == None or task_data.get('client_ip') == None :
            return False
        return True


    def generate_task_id(self):
        # 结合当前时间戳和uuid的随机部分来生成一个字符串
        combined_string = str(int(time.time())) + str(uuid.uuid4())
        # 使用SHA-256算法生成哈希值
        hash_object = hashlib.sha256(combined_string.encode())
        hex_dig = hash_object.hexdigest()
        # 取哈希值的前6位
        task_id = hex_dig[:6]  
        return task_id
    async def create_task(self, task_data):
        task_data['task_id'] = str(self.generate_task_id())
        task_data['status'] = 'running'
        await self.taskQueue.put(task_data)
        #写入任务记录数据库
        try:
            await self.dbUtil.async_write("operation_task_data",task_data)
        except Exception as e:
            logging.warning(f"Failed to write task to database: {e}")
        logging.info(f"new task write success!-->task id:{task_data['task_id']},player:{task_data['player']}")
        #返回任务ID
        return task_data
    async def get_task_result_data(self):
        return await self.taskResultQueue.get()
    async def get_task_result_data(self):
        return await self.taskResultQueue.get()
    async def get_connected_clients(self):
        return self.connected_clients
    async def start_server(self, host: str = '10.0.0.252', port: int = 8888) -> None:
        server = await asyncio.start_server(
            lambda r, w: self.handle_rpc(r, w, w.get_extra_info('peername')),
            host, port)
        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')
        self.heartbeat_monitor_task = asyncio.create_task(self.heartbeat_monitor())
        self.task_distributor = asyncio.create_task(self.distribute_tasks())
        await server.serve_forever()
    async def start(self,*arg):
        """启动服务"""
        self._init_params(*arg)
        await self.start_server()