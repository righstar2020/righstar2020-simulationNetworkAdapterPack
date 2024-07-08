
import logging
from controller.global_vars import client_connect_server
from controller.global_vars import DBUtil
from system.simulator import get_current_topo_data,update_current_topo_dynamic_data,get_current_topo_dynamic_data
from service.swicth_task_service import SwitchTaskService 
logging.basicConfig(level=logging.INFO)
class TaskService:
    def __init__(self) -> None:
        self.conn = None
        self.SwitchTaskService = SwitchTaskService()
        pass

    async def init_task_service(self):
        pass
    async def send_player_task(self,task):
        task_r = {}
        if task.get('client_type') == 'swicth':
            task_r = await self.SwitchTaskService.create_swicth_task(task)
            #更新拓扑状态
            await self.update_network_topo_dynamic_swicth(task) 
        else:
            task_r = await client_connect_server.create_task(task)
            await self.update_network_topo_dynamic_host(task)
        return task_r
    async def create_task_list(self, task_data_list):
        task_list_return = []
        for task_data in task_data_list:
           task_return = await self.send_player_task(task_data)
           task_list_return.append(task_return)
        return task_list_return
    async def update_network_topo_dynamic_host(self,task):
        logging.info("update network topo dynamic:host")
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
                    if node['dpid'] == task['swicth_dpid']:
                        new_network_dynamic_data['nodes'][node_id]['defend_source']=task['swicth_dpid']
                    
            update_current_topo_dynamic_data(new_network_dynamic_data)          
        except Exception as e:
            logging.info(e)
    
    async def update_network_topo_dynamic_swicth(self,task):
        logging.info("update network topo dynamic:swicth")
        try:
            _,topo_id,_ = get_current_topo_data()
            old_network_dynamic_data = get_current_topo_dynamic_data()
            new_network_dynamic_data = old_network_dynamic_data
            #进行一些处理
            for node in old_network_dynamic_data['nodes'].values():
                if node['node_type'] == 'swicth':
                    if node['dpid'] == task['swicth_dpid']:
                        new_network_dynamic_data['nodes'][node['id']]['defend_source']=task['swicth_dpid']
            update_current_topo_dynamic_data(new_network_dynamic_data)          
        except Exception as e:
            logging.info(e)