
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
from controller.app import start_flask_background
import threading

def background_service():
    print("-------------1.启动后端服务-------------------")
    start_flask_background()
def network_simulator():
    print("-------------2.启动网络仿真环境-------------------")
    start_simulator()

    

if __name__ == '__main__':
    threading.Thread(target=network_simulator, daemon=True).start()
    background_service()
    
    