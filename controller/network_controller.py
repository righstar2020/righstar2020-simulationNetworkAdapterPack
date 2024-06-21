from flask import Flask,jsonify,request
import asyncio
from controller.flask_async import run_async
from system.simulator import get_current_topo_data,update_current_topo_dynamic_data,get_current_topo_dynamic_data
from controller.global_vars import DBUtil,main_event_loop,taskQueue,taskResultQueue,client_connect_server
from controller.global_vars import async_http_request
from flask import Blueprint  #导入蓝图模块
network_blue = Blueprint('network',__name__,url_prefix='/network') #创建一个蓝图

@network_blue.route('/get_topo_data', methods=['GET'])
@run_async
async def get_topo_data():
    """异步视图"""
    try:
        current_topo_name,current_topo_id,current_topo_data=get_current_topo_data()
        data = {
            'topo_name':current_topo_name,
            'topo_data':current_topo_data
        }
        return jsonify({'status':'success',"data": data})
    except Exception as e:
        return jsonify({'status':'error',"message":str(e)}), 404
    
@network_blue.route('/get_network_dynamic_topo_data', methods=['GET'])
@run_async
async def get_network_dynamic_topo_data():
    """异步视图"""
    try:
        current_topo_name,current_topo_id,current_topo_data=get_current_topo_data()
        data = {
            'topo_name':current_topo_name,
            'topo_data':get_current_topo_dynamic_data()
        }
        return jsonify({'status':'success',"data": data})
    except Exception as e:
        return jsonify({'status':'error',"message": "No data available"}), 404