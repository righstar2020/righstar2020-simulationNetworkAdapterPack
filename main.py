
#启动Flask服务器
# app.py
from flask import Flask,jsonify,request
from conn.client_connect import ClientConnectServer
from db.tiny_db import  TinyDBUtil
import asyncio
import threading
import aiohttp
from asyncio import Queue
from flask_async import run_async
import logging
import time
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
# 保留error及以上级别的日志
DBUtil = TinyDBUtil()
main_event_loop = asyncio.get_event_loop()
taskQueue = Queue()
taskResultQueue = Queue()
client_connect_server = ClientConnectServer()

@app.route('/get_task_queue', methods=['GET'])
@run_async
async def get_task_queue():
    """异步视图，从队列中获取并返回一条消息"""
    try:
        task = await taskQueue.get()  # 直接使用await获取队列中的消息
        taskQueue.task_done()  # 标记消息处理完成
        return jsonify({'status':'success',"data": task})
    except asyncio.QueueEmpty:
        return jsonify({'status':'error',"message": "No data available"}), 404
    except:
        return jsonify({'status':'error',"message": "No data available"}), 404

@app.route('/get_task_result_queue', methods=['GET'])
@run_async
async def get_task_result_queue():
    """异步视图，从队列中获取并返回一条消息"""
    try:
        taskResult = await taskResultQueue.get()  # 直接使用await获取队列中的消息
        taskResultQueue.task_done()  # 标记消息处理完成
        return jsonify({'status':'success',"data":taskResult})
    except asyncio.QueueEmpty:
        return jsonify({"status":"error","message": "No data available"}), 404
    except:
        return jsonify({"status":"error","message": "No data available"}), 404

@app.route('/get_task_result_by_task_id', methods=['GET'])
@run_async
async def get_task_result_by_task_id():
    """异步视图，从数据库中获取并返回任务数据"""
    task_id = int(request.args.get('task_id', None))
    try:
        if task_id!=None:
            result = await DBUtil.async_read_by_key_value('task_result','task_id',task_id)  # 查询json数据库并按时间顺序排序   
            if result!=None:
                return jsonify({'status':'success',"data": result})
        return jsonify({"status":"error","message": "task no exit:"+task_id}), 404
    except asyncio.QueueEmpty as e:
        logging.error(f"get_task_result_by_task_id QueueEmpty err:{e}")
        return jsonify({"status":"error","message": "No data  available."}), 404
    except Exception as e:
        logging.error(f"get_task_result_by_task_id err:{e}")
        return jsonify({"status":"error","message": "No data  available"}), 404

@app.route('/get_attacker_task', methods=['GET'])
@run_async
async def get_attacker_task():
    """异步视图，从数据库中获取并返回任务数据"""
    try:
        result = await DBUtil.async_read_by_key_value('task_result','player','attacker')  # 查询json数据库并按时间顺序排序   
        if result!=None:
            return jsonify({'status':'success',"data": result})
        return jsonify({"status":"error","message": "attacker task no exit"}), 404
    except asyncio.QueueEmpty as e:
        logging.error(f"get_task_result_by_task_id QueueEmpty err:{e}")
        return jsonify({"status":"error","message": "No data  available."}), 404
    except Exception as e:
        logging.error(f"get_task_result_by_task_id err:{e}")
        return jsonify({"status":"error","message": "No data  available"}), 404


@app.route('/get_task_result_from_db', methods=['GET'])
@run_async
async def get_task_result_from_db():
    """异步视图，从数据库中获取并返回一条消息"""
    # 获取查询参数中的limit值，如果没有提供，默认为10
    limit = int(request.args.get('limit', 10))
    try:
        taskResult = await DBUtil.async_read_sort_by_timestamp('task_result',limit=limit)  # 查询json数据库并按时间顺序排序   
        return jsonify({'status':'success',"data": taskResult})
    except asyncio.QueueEmpty as e:
        logging.error(f"get_task_result_from_db QueueEmpty err:{e}")
        return jsonify({"status":"error","message": "No data  available."}), 404
    except Exception as e:
        logging.error(f"get_task_result_from_db err:{e}")
        return jsonify({"status":"error","message": "No data  available"}), 404

@app.route("/get_traffic_entropy",methods=['GET'])
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
    except asyncio.QueueEmpty:
        return jsonify({"status":"error","message": "No data  available"}), 404
    except:
        return jsonify({"status":"error","message": "No data  available"}), 404

@app.route("/get_traffic_flow",methods=['GET'])
@run_async
async def get_traffic_flow():
    #获取全域流量数据
    try:
        result = await async_http_request('http://localhost:8008/activeflows/ALL/mn_ipv4_traffic/json')
        #更流量数据到数据库
        #先获取数据
        try:
            update_data = await DBUtil.async_read_by_key_value('env_status_data','status_name','traffic_flow')
            update_data = update_data[0]
            timstamp = int(round(time.time() * 1000))
            toatl_traffic_bytes = 0
            if len(result)>0:
                for flow in result:
                    if flow['value']!=None:
                        toatl_traffic_bytes += flow['value']
                update_data['status_data']['tcp'][str(timstamp)] = str(int(toatl_traffic_bytes))
            await DBUtil.async_upsert_by_key('env_status_data','status_name','traffic_entropy',update_data)
        except Exception as e:
            logging.warning(f"error to update traffic_flow data:{e}")
        return jsonify({'status':'success',"data": result})
    except asyncio.QueueEmpty:
        return jsonify({"status":"error","message": "No data  available"}), 404
    except:
        return jsonify({"status":"error","message": "No data  available"}), 404

@app.route("/send_player_task",methods=['POST'])
@run_async
async def send_player_task():
    #向client发送任务
    try:
        task = request.get_json()
        if task is None:
            return jsonify({"status":"error","message": "No task"}), 404
        task_r = await client_connect_server.put_task_data(task)
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404

@app.route("/send_test_task",methods=['GET'])
@run_async
async def send_test_task():
    #向client发送任务
    try:
        task_r = await client_connect_server.send_test_task()
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404


@app.route("/send_player_task_list",methods=['POST'])
@run_async
async def send_player_task_list():
    #向client发送任务队列
    try:
        task_list = request.get_json()
        if task_list is None:
            return jsonify({"status":"error","message": "No task list"}), 404
        task_list_return = await client_connect_server.put_task_data_list(task_list)
        return jsonify({'status':'success',"data": task_list_return})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404


async def async_http_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
def add_background_coroutine_tasks(loop, coroutine_func, *args):
    """添加协程任务"""
    asyncio.run_coroutine_threadsafe(coroutine_func(*args), loop)

def main():
    #启动一个事件循环子线程,并使线程作为daemon(主线程退出则子线程退出)
    threading.Thread(target=start_loop, args=(main_event_loop,), daemon=True).start()
    #初始化数据库
    add_background_coroutine_tasks(main_event_loop,DBUtil.init_db)
    #启动client监听服务器
    add_background_coroutine_tasks(main_event_loop,
                                   client_connect_server.start,
                                   taskQueue,
                                   taskResultQueue,
                                   DBUtil)
    app.run(host="10.0.0.101",port=5000,debug=True, use_reloader=False)  #注意：use_reloader=False 防止重载时创建多个事件循环 
    pass
if __name__ == '__main__':
    main()
    