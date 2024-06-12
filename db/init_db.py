
from db.tiny_db import TinyDBUtil
import asyncio
async def create_db_table():
    tiny_db = TinyDBUtil()
    await tiny_db.async_write("network_topo_data", 
                              {
                                  "topo_id": "topo_1",
                                  'links':{},
                                  'nodes':{},
                                  'config_info':{},
                                  'timestamp':'2021-01-01 00:00:00'                        
                              })
    await tiny_db.async_write("player_data", 
                              {
                                  "player_id": "player_1",
                                  'player_type':'attacker',
                                  'operations':{},
                                  'operaton_history':{},
                                  'timestamp':'2021-01-01 00:00:00'                        
                              })
    await tiny_db.async_write("player_data", {
                                  "player_id": "player_2",
                                  'player_type':'defender',
                                  'operations':{},
                                  'operaton_history':{},
                                  'timestamp':'2021-01-01 00:00:00'                        
                              })
    await tiny_db.async_write("operation_task_data", 
                              {
                                  "task_id": "001",
                                  'operation_link_id':'001',
                                  'task_type':'signal',
                                  'task_name':'端口扫描',
                                  'player':'attacker',
                                  'client_ip':'10.0.0.1',
                                  'params':{},
                                  'timestamp':'2021-01-01 00:00:00'                        
                              })
    await tiny_db.async_write("env_status_data", 
                              {
                                  "status_id": "001",
                                  'status_type':'env',
                                  'status_name':'vm_status',
                                  'status_data':{
                                      'cpu_rate':'50',
                                      'memery_rate':'50'
                                  },
                                  'timestamp':'2021-01-01 00:00:00'                        
                              })
    await tiny_db.async_write("env_status_data", 
                              {
                                  "status_id": "001",
                                  'status_type':'traffic',
                                  'status_name':'traffic_flow',
                                  'status_data':{
                                      'tcp':{
                                          '1718191634419':'50'
                                       },
                                      'udp':{},
                                      'icmp':{}
                                  },
                                  'timestamp':'1718191634419'                        
                              })
    await tiny_db.async_write("env_status_data", 
                              {
                                  "status_id": "002",
                                  'status_type':'traffic',
                                  'status_name':'traffic_entropy',
                                  'status_data':{
                                      'ip_entropy':[],
                                      'port_entropy':[]
                                  },
                                  'timestamp':'1718191634419'                        
                              })
 
    

def main():
    asyncio.run(create_db_table())

if __name__ == '__main__':
    main()