
#启动Flask服务器
# app.py
from flask import Flask,jsonify,request
from conn.client_connect import ClientConnectServer
from db.tiny_db import  TinyDBUtil
import asyncio
import threading
import aiohttp
from asyncio import Queue
import logging
import time
from system.simulator import start_simulator
from db.init_db import init_db
from controller.app import start_flask_background
import threading

def background_service():
    print("-------------1.初始化数据库-------------------")
    asyncio.run(init_db())
    print("-------------2.启动后端服务-------------------")
    start_flask_background()
def network_simulator():
    print("-------------3.启动网络仿真环境-------------------")
    start_simulator()

    

if __name__ == '__main__':
    threading.Thread(target=network_simulator, daemon=True).start()
    background_service()
    
    