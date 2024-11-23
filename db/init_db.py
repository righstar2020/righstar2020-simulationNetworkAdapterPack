
from db.tiny_db import TinyDBUtil
import time
import asyncio
async def init_db():
    """
        初始化数据库
        如果数据表不存在则创建，并清空历史任务记录.
        创建(清空)环境监控条目
    """
    dbUtil = TinyDBUtil()
    #-----------------创建网络拓扑表--------------------------
    await dbUtil.async_write("network_topo_data")
    #-----------------创建palyer数据表（这个表可以不清空）----------------
    await dbUtil.async_upsert_by_key("player_data", 
                              {
                                  "player_id": "attacker",
                                  'player_type':'attacker',
                                  'operations':{},
                                  'operaton_history':{},
                                  'timestamp':int(round(time.time() * 1000))                       
                              },"player_id","attacker")
    await dbUtil.async_upsert_by_key("player_data", {
                                  "player_id": "defender",
                                  'player_type':'defender',
                                  'operations':{},
                                  'operaton_history':{},
                                  'timestamp':int(round(time.time() * 1000))                        
                              },"player_id","defender")
    #-----------------清空历史任务表--------------------------
    await dbUtil.async_clear_table("operation_task_data")
    #--------------清空环境监控表--------------------
    await dbUtil.async_upsert_by_key("env_status_data", 
                              {
                                  "status_id": "001",
                                  'status_type':'env',
                                  'status_name':'vm_status',
                                  'status_data':{
                                      'cpu_rate':'0',
                                      'memery_rate':'0'
                                  },
                                  'timestamp':int(round(time.time() * 1000))                       
                              },'status_name','vm_status')
    
    await dbUtil.async_upsert_by_key("env_status_data", 
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
                                  'timestamp':int(round(time.time() * 1000))                      
                              },'status_name','traffic_flow')
    await dbUtil.async_upsert_by_key("env_status_data", 
                              {
                                  "status_id": "002",
                                  'status_type':'traffic',
                                  'status_name':'traffic_entropy',
                                  'status_data':{
                                      'source_ips_entropy':[],
                                      'destination_ports_entropy':[]
                                  },
                                  'timestamp':int(round(time.time() * 1000))                        
                              },'status_name','traffic_entropy')
 
    
