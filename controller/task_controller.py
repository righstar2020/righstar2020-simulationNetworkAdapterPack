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

@task_blue.route('/get_task_result_by_task_id', methods=['GET'])
@run_async
async def get_task_result_by_task_id():
    """异步视图，从数据库中获取并返回任务数据"""
    task_id = int(request.args.get('task_id', None))
    try:
        if task_id!=None:
            result = await DBUtil.async_read_by_key_value('operation_task_data','task_id',task_id)  # 查询json数据库并按时间顺序排序   
            if result!=None:
                return jsonify({'status':'success',"data": result})
        return jsonify({"status":"error","message": "task no exit:"+task_id})
    except asyncio.QueueEmpty as e:
        logging.error(f"get_task_result_by_task_id QueueEmpty err:{e}")
        return jsonify({"status":"error","message": "No data  available."})
    except Exception as e:
        logging.error(f"get_task_result_by_task_id err:{e}")
        return jsonify({"status":"error","message": "No data  available"})

@task_blue.route('/get_attacker_task', methods=['GET'])
@run_async
async def get_attacker_task():
    """异步视图，从数据库中获取并返回任务数据"""
    try:
        result = await DBUtil.async_read_by_key_value('operation_task_data','player','attacker')  # 查询json数据库并按时间顺序排序   
        if result!=None:
            return jsonify({'status':'success',"data": result})
        return jsonify({"status":"error","message": "attacker task no exit"})
    except Exception as e:
        logging.error(f"get_task_result_by_task_id err:{e}")
        return jsonify({"status":"error","message": "No data  available"})


@task_blue.route('/get_all_task', methods=['GET'])
@run_async
async def get_all_task():
    try:
        taskResult = await DBUtil.async_read_sort_by_timestamp('operation_task_data')  # 查询json数据库并按时间顺序排序   
        return jsonify({'status':'success',"data": taskResult})
    except Exception as e:
        logging.error(f"get_task_result_from_db err:{e}")
        return jsonify({"status":"error","message": "No data  available"})

@task_blue.route("/send_player_task",methods=['POST'])
@run_async
async def send_player_task():
    #向client发送任务
    try:
        task = request.get_json()
        if task is None:
            return jsonify({"status":"error","message": "No task"})
        task_r = await task_service.send_player_task(task)
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})
    
@task_blue.route("/send_player_task_list",methods=['POST'])
@run_async
async def send_player_task_list():
    #向client发送任务队列
    try:
        task_list = request.get_json()
        if task_list is None:
            return jsonify({"status":"error","message": "No task list"})
        task_list_return = await task_service.create_task_list(task_list)
        return jsonify({'status':'success',"data": task_list_return})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})
    
@task_blue.route("/send_test_task",methods=['GET'])
@run_async
async def send_test_task():
    #向client发送任务
    try:
        task_r = await client_connect_server.send_test_task()
        return jsonify({'status':'success',"data": task_r})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})


