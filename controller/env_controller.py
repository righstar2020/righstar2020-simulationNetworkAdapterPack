from flask import Flask,jsonify,request
import asyncio
from controller.flask_async import run_async
import logging
import time
from system.simulator import topo_data,current_topo_name,reload_simulator_by_topo
from system.command import execute_cmd
from controller.global_vars import DBUtil,main_event_loop,taskQueue,taskResultQueue,client_connect_server
from controller.global_vars import async_http_request,async_http_put
from flask import Blueprint  #导入蓝图模块
env_blue = Blueprint('env',__name__,url_prefix='/env') #创建一个蓝图
sflow_init = False #是否初始化sflow

@env_blue.route("/get_traffic_flow",methods=['GET'])
@run_async
async def get_traffic_flow():
    #获取全域流量数据
    global sflow_init
    try:
        if not sflow_init:
            sflow_init = True
            flow_rule={
                "value": "bytes",
                "keys": "ipsource,ipdestination"
            }
            # logging.info(f"init sflow flow rule:{flow_rule}")
            # rule_result = await async_http_put('http://localhost:8008/flow/mn_ipv4_traffic/json',flow_rule) #先初始化流监听规则
            # logging.info(f"init sflow flow rule result:{rule_result}")
            cmd = """
                curl -X 'PUT' \
                    'http://127.0.0.1:8008/flow/mn_ipv4_traffic/json' \
                    -H 'accept: */*' \
                    -H 'Content-Type: application/json' \
                    -d '{
                    "value": "bytes",
                    "keys": "ipsource,ipdestination"
                    }'
            """
            result = execute_cmd(cmd)
            logging.info(f"init sflow flow rule result:{result}")
        result = await async_http_request('http://localhost:8008/activeflows/ALL/mn_ipv4_traffic/json')
        #更流量数据到数据库
        #先获取数据
        try:
            update_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_flow')
            update_data = update_data[0]
            timstamp = int(round(time.time() * 1000))
            total_traffic_bytes = 0
            if len(result) > 0:
                update_data['status_data']['tcp'] = {}
                for flow in result:
                    if flow['value'] is not None:
                        total_traffic_bytes += flow['value']
                #现在可以安全地赋值了，因为已确保'tcp'是一个字典
                update_data['status_data']['tcp'][str(timstamp)] = str(int(total_traffic_bytes))

            await DBUtil.async_upsert_by_key('env_status_data',data=update_data, fieldName='status_name', value='traffic_flow')
        except Exception as e:
            print(f"Error Type: {type(e)}, Error Message: {e}")
            logging.warning(f"error to update traffic_flow data:{e}")
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404

@env_blue.route("/get_traffic_entropy",methods=['GET'])
@run_async
async def get_traffic_entropy():
    #获取全域流量熵
    try:
        result = await async_http_request('http://127.0.0.1:8080/monitor/traffic_entropy')
        # 更新流量熵指标到数据库
        #先获取数据
        try:
            update_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_entropy')
            update_data = update_data[0]
            if len(result["source_ips_entropy"])>0:
                update_data['status_data']['ip_entropy'].extend(result["source_ips_entropy"])
            if len(result["source_ips_entropy"])>0:
                update_data['status_data']['port_entropy'].extend(result["destination_ports_entropy"])
            await DBUtil.async_upsert_by_key('env_status_data','status_name','traffic_entropy',update_data)
        except Exception as e:
            logging.warning(f"error to update traffic_entropy data:{e}")
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404