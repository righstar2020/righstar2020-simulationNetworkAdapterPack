from flask import jsonify,request
from flask import Blueprint  #导入蓝图模块
import asyncio
from controller.flask_async import run_async
import logging
from controller.global_vars import DBUtil,main_event_loop,taskQueue,taskResultQueue,client_connect_server
from service.task_service import TaskService
# Blueprint两个参数（'蓝图名字',蓝图所在位置',url前缀)，注意：url前缀对该蓝图下所有route都起作用
task_blue = Blueprint('task',__name__,url_prefix='/task') #创建一个蓝图

task_service = TaskService()

@task_blue.route('/get_task_queue', methods=['GET'])
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

@task_blue.route('/get_task_result_queue', methods=['GET'])
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

@task_blue.route('/get_task_result_by_task_id', methods=['GET'])
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

@task_blue.route('/get_attacker_task', methods=['GET'])
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


@task_blue.route('/get_task_result_from_db', methods=['GET'])
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

@task_blue.route("/send_player_task",methods=['POST'])
@run_async
async def send_player_task():
    #向client发送任务
    try:
        task = request.get_json()
        if task is None:
            return jsonify({"status":"error","message": "No task"}), 404
        task_r = await task_service.send_player_task(task)
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404

@task_blue.route("/send_test_task",methods=['GET'])
@run_async
async def send_test_task():
    #向client发送任务
    try:
        task_r = await client_connect_server.send_test_task()
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 404


@task_blue.route("/send_player_task_list",methods=['POST'])
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