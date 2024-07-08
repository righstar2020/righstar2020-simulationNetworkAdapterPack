
import logging,time,hashlib,uuid
from controller.global_vars import client_connect_server
from controller.global_vars import DBUtil,async_http_post
from system.simulator import get_current_topo_data,update_current_topo_dynamic_data,get_current_topo_dynamic_data

logging.basicConfig(level=logging.INFO)
class SwitchTaskService:
    def __init__(self) -> None:
        self.conn = None
        pass
    def generate_task_id(self):
        # 结合当前时间戳和uuid的随机部分来生成一个字符串
        combined_string = str(int(time.time())) + str(uuid.uuid4())
        # 使用SHA-256算法生成哈希值
        hash_object = hashlib.sha256(combined_string.encode())
        hex_dig = hash_object.hexdigest()
        # 取哈希值的前6位
        task_id = hex_dig[:6]  
        return task_id
    async def create_swicth_task(self, task_data):
        task_data['task_id'] = str(self.generate_task_id())
        task_data['status'] = 'running'
        task_data['timestamp'] = int(round(time.time() * 1000)) #更新时间戳
        #写入任务记录数据库
        try:
            await DBUtil.async_write("operation_task_data",task_data)
            logging.info(f"new task write success!-->task id:{task_data['task_id']},player:{task_data['player']}")
        except Exception as e:
            logging.warning(f"Failed to write task to database: {e}")
            task_data['status'] = 'error'
            task_data['message'] = str(e)
        #执行switch操作任务
        try:
            task_data = await self.execute_swicth_task(task_data)
        except Exception as e:
            logging.warning(f"Failed to execute switch task: {e}")
            task_data['status'] = 'error'
            task_data['message'] = str(e)
        #任switch任务执行完成更新数据库
        await self.update_swicth_task(task_data)
        #返回任务数据
        return task_data
    async def update_swicth_task(self, task_data):
        #按task_id更新交换机任务状态
        try:
            await DBUtil.async_upsert_by_key('operation_task_data',task_data,'task_id',task_data['task_id'])
        except Exception as e:
            logging.warning(f"Failed to write task result to database: {e}")    
        logging.info(f"task result write success!-->task id:{task_data['task_id']}")
    async def execute_swicth_task(self,task):
        #执行交换机任务
        dpid = task['params']['dpid']
        task['status'] = 'error'
        if dpid ==None:
            return task
        if task['task_name'] == 'host_protocol_forbid':
            if task['params']['protocol']!=None:
                task['status'],task['result'] = await self.icmp_drop(dpid,task['params']['protocol'])
        return task
    
   
    async def icmp_drop(self,dpid,protocol):
        post_data = {
            'dpid':dpid,
            'protocol':protocol
        }
        drop_icmp_result = await async_http_post('http://127.0.0.1:8080/engineer/protocol_forbid',post_data)
        logging.info(f"icmp drop result:{drop_icmp_result}")
        return drop_icmp_result['status'],drop_icmp_result['data']

    async def ip_white_table(self,dpid):
        pass