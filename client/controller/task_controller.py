
from attacker.signal.scan import ScanHost
from attacker.action.ddos_attack import DDoSAttack
from defender.signal.server_c import HostServer


class TaskController:
    def __init__(self, client):
        self.client = client
        self.scanHost = ScanHost()
        self.hostServer = HostServer()
        self.ddosAttack = DDoSAttack()

    async def execute_task(self, task_data):
        task_result = task_data
        scanHost = self.scanHost
        hostServer = self.hostServer
        ddosAttack = self.ddosAttack
        if task_data['player'] == 'attacker':
            if task_data['task_name'] == 'host_scan':
                # 执行扫描任务
                if task_data['params']['target_ip']!=None:
                    task_result['result'] = await scanHost.start_scan(task_data['params']['target_ip'])
                    task_result['status'] = 'success'
                return task_result
            if task_data['task_name'] == 'host_attack':
                # 执行攻击任务
                if task_data['params']['target_ip']!=None:
                    task_result['result'] = await ddosAttack.ddos_attack(task_data['params']['target_ip'],
                                                                         task_data['params']['attack_type'],
                                                                         int(task_data['params']['duration']))
                    task_result['status'] = 'success'
                return task_result
        elif task_data['player'] == 'defender':
            # 防御者动作
            if task_data['task_name'] == 'host_deception':
                request_delay_min=int(task_data['params']['request_delay_min'])
                request_delay_max=int(task_data['params']['request_delay_max'])
                target_port=int(task_data['params']['port'])
                if request_delay_min == None:
                    return task_result
                if request_delay_max == None:
                    return task_result
                if target_port == None:
                    return task_result
                task_result['result'] = await hostServer.start_server_on_port_delay_response(target_port,
                                                                                             request_delay_min,
                                                                                             request_delay_max)
                task_result['status']='success'
                return task_result
