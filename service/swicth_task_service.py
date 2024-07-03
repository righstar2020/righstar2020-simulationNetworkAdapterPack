
import logging,time,hashlib,uuid
from controller.global_vars import client_connect_server
from controller.global_vars import DBUtil
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
        #返回任务数据
        return task_data
    async def execute_swicth_task(self,task):
        #执行交换机任务
        dpid = task['params'].get('dpid')
        if dpid ==None:
            return task
        if task['task_name'] == 'host_protocol_forbid':
            task['result'] = self.icmp_drop(dpid)
        if task['task_name'] == 'host_protocol_forbid':
            task['result'] = self.icmp_drop(dpid)
        return task
    
    async def ip_white_table(self,dpid):
        pass
    async def icmp_drop(self,dpid):
        pass