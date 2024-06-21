
from conn.client_connect import ClientConnectServer
from db.tiny_db import  TinyDBUtil
import asyncio
import aiohttp
from asyncio import Queue
""" 
    全局变量注册区
    为避免循环引用，此文件已不需要导入其他依赖
"""
DBUtil = TinyDBUtil()
main_event_loop = asyncio.get_event_loop()
taskQueue = Queue()
taskResultQueue = Queue()
client_connect_server = ClientConnectServer()

""" 
    全局函数注册区
    为避免循环引用，此文件已不需要导入其他依赖
"""
async def async_http_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                return await response.json()
            except Exception as e:
                #非json则返回text
                return await response.text()

async def async_http_post(url,data):
    async with aiohttp.ClientSession() as session:
        try:
            return await session.post(url,data=data,headers={'Content-Type': 'application/json'})
        except Exception as e:
            print(str(e))
            return None

async def async_http_put(url,data):
    async with aiohttp.ClientSession() as session:
        try:
            return await session.put(url,data=data,headers={'Content-Type': 'application/json'})
        except Exception as e:
            print(str(e))
            return None