
import logging
from controller.global_vars import client_connect_server
from controller.global_vars import DBUtil
from system.simulator import get_current_topo_data,update_current_topo_dynamic_data,get_current_topo_dynamic_data

logging.basicConfig(level=logging.INFO)
class TaskService:
    def __init__(self) -> None:
        self.conn = None
        pass

    async def init_task_service(self):
        pass
    async def send_player_task(self,task):
        task_r = await client_connect_server.put_task_data(task)
        await self.update_network_topo_dynamic(task)
        return task_r
    async def update_network_topo_dynamic(self,task):
        logging.info("update network topo dynamic")
        try:
            _,topo_id,_ = get_current_topo_data()
            old_network_dynamic_data = get_current_topo_dynamic_data()
            new_network_dynamic_data = old_network_dynamic_data
            #进行一些处理
            for node in old_network_dynamic_data['nodes'].values():
                node_id = node['id']
                if task['player'] == 'attacker':
                    if node['ip'] == task['client_ip']:
                        new_network_dynamic_data['nodes'][node_id]['attack_source']=task['client_ip']
                    if node['ip'] == task['params']['target_ip']:
                        new_network_dynamic_data['nodes'][node_id]['victim_source']=task['params']['target_ip']
                if task['player'] == 'defender':
                    if node['ip'] == task['client_ip']:
                        new_network_dynamic_data['nodes'][node_id]['defend_source']=task['client_ip']
            update_current_topo_dynamic_data(new_network_dynamic_data)          
            await DBUtil.async_upsert_by_key('network_topo_data','topo_id',topo_id,new_network_dynamic_data)
        except Exception as e:
            logging.info(e)