
#启动Flask服务器
# app.py
from flask import Flask
import asyncio,threading,logging
from system.command import execute_cmd
from controller.env_controller import env_blue
from controller.network_controller import network_blue
from controller.task_controller import task_blue
from controller.global_vars import DBUtil,main_event_loop,taskQueue,taskResultQueue,client_connect_server
logging.basicConfig(level=logging.INFO)#保留error及以上级别的日志
app = Flask(__name__)
"""
    注册控制器蓝图
"""
app.register_blueprint(env_blue) #注册蓝图
app.register_blueprint(network_blue) 
app.register_blueprint(task_blue) 


        
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
def add_background_coroutine_tasks(loop, coroutine_func, *args):
    """添加协程任务"""
    asyncio.run_coroutine_threadsafe(coroutine_func(*args), loop)

def start_flask_background():
    #启动一个事件循环子线程,并使线程作为daemon(主线程退出则子线程退出)
    print("-------------1.1 启动事件循环线程-------------------")
    threading.Thread(target=start_loop, args=(main_event_loop,), daemon=True).start()
    print("-------------1.2 初始化数据库-------------------")
    add_background_coroutine_tasks(main_event_loop,DBUtil.init_db)
    print("-------------1.3 配置网络环境(ens35)-------------------")
    execute_cmd("ifconfig ens35 10.0.0.252")
    print("-------------1.4 启动client监听服务器(10.0.0.252:8888)-------------------")
    add_background_coroutine_tasks(main_event_loop,
                                   client_connect_server.start,
                                   taskQueue,
                                   taskResultQueue,
                                   DBUtil)
    print("-------------1.5 启动flask服务器-------------------")
    app.run(host="10.0.0.101",port=5000,debug=False, use_reloader=False)  #注意：use_reloader=False 防止重载时创建多个事件循环 