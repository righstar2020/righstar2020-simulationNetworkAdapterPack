from flask import Flask,jsonify,request
import asyncio
from controller.flask_async import run_async
import logging
import time
from system.simulator import topo_data,current_topo_name,reload_simulator_by_topo
from system.command import execute_cmd
from system.environment import get_cpu_memory_usage,get_iperf3_test_data,get_ping_delay_data
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
            # 流量单位字节(bytes)
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
        # try:
        #     update_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_flow')
        #     update_data = update_data[0]
        #     timstamp = int(round(time.time() * 1000))
        #     total_traffic_bytes = 0
        #     if len(result) > 0:
        #         update_data['status_data']['tcp'] = {}
        #         for flow in result:
        #             if flow['value'] is not None:
        #                 total_traffic_bytes += flow['value']
        #         #现在可以安全地赋值了，因为已确保'tcp'是一个字典
        #         update_data['status_data']['tcp'][str(timstamp)] = str(int(total_traffic_bytes))

        #     await DBUtil.async_upsert_by_key('env_status_data',data=update_data, fieldName='status_name', value='traffic_flow')
        # except Exception as e:
        #     print(f"Error Type: {type(e)}, Error Message: {e}")
        #     logging.warning(f"error to update traffic_flow data:{e}")
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})
@env_blue.route("/get_history_traffic_flow",methods=['GET'])
@run_async
async def get_history_traffic_flow():
    #获取历史流量数据
    try:
        history_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_flow')
        #取后1000个数据
        tcp_flow = dict(list(history_data[0]['status_data']['tcp'].items())[-1000:])
        result = {
            "tcp":tcp_flow
        }
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}) 

@env_blue.route("/get_traffic_entropy",methods=['GET'])
@run_async
async def get_traffic_entropy():
    #获取全域流量熵
    try:
        result = await async_http_request('http://127.0.0.1:8080/monitor/traffic_entropy')
        # 更新流量熵指标到数据库
        # try:
        #     update_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_entropy')
        #     update_data = update_data[0]
        #     if len(result["source_ips_entropy"])>0:
        #         update_data['status_data']['source_ips_entropy'].extend(result["source_ips_entropy"])
        #     if len(result["destination_ports_entropy"])>0:
        #         update_data['status_data']['destination_ports_entropy'].extend(result["destination_ports_entropy"])
        #     await DBUtil.async_upsert_by_key('env_status_data','status_name','traffic_entropy',update_data)
        # except Exception as e:
        #     logging.warning(f"error to update traffic_entropy data:{e}")
            
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})

@env_blue.route("/get_protocol_count",methods=['GET'])
@run_async
async def get_protocol_count():
    #获取协议比例
    try:
        result = await async_http_request('http://127.0.0.1:8080/engineer/get_protocol_count')
        data = result.get('data')
        if data != None:
            return jsonify({'status':'success',"data": data})
        return jsonify({"status":"error","message": 'no data'})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})

   
@env_blue.route("/get_history_traffic_entropy",methods=['GET'])
@run_async
async def get_all_traffic_entropy_data():
    #获取历史流量熵，返回最新的1000条数据
    try:
        history_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_entropy')
        result = {
            "source_ips_entropy":history_data[0]['status_data']['ip_entropy'][-1000:],
            "destination_ports_entropy":history_data[0]['status_data']['port_entropy'][-1000:]
        }
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}) 

@env_blue.route("/get_cpu_memory_usage_status",methods=['GET'])
@run_async
async def get_cpu_memory_usage_status():
    try:
        cpu_percent,memory_percent = await get_cpu_memory_usage()
        result = {
            "cpu_percent":cpu_percent,
            "memory_percent":memory_percent
        }
        return jsonify({'status':'success',"data": result})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})
    
@env_blue.route("/get_network_status",methods=['GET'])
@run_async
async def get_network_status():
    try:
        iperf3_json_data = await get_iperf3_test_data()
        return jsonify({'status':'success',"data": iperf3_json_data})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})
@env_blue.route("/get_network_delay_by_ip",methods=['GET'])
@run_async
async def get_network_delay_by_ip():
    ip = request.args.get('ip')
    try:
        ip_delay_data={
        }
        if ip == None:
            ip_delay_data['10.0.0.1'] = await get_ping_delay_data(ip)
        else:
            ip_delay_data[ip] = await get_ping_delay_data(ip)
        return jsonify({'status':'success',"data": ip_delay_data})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})