
#执行linux系统命令
import os
import subprocess
import sys
import asyncio,threading
from typing import Callable
#同步执行指令
def execute_cmd(cmd):
    try:
        print("execute cmd:"+cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        return p.stdout.read().decode('utf-8')
    except Exception as e:
        print(e)
        return None
    
def execute_cmd_thread(cmd):
    try:
        print("execute cmd:"+cmd)
        thread = threading.Thread(target=execute_cmd, args=(cmd,), daemon=True).start()
        return thread
    except Exception as e:
        print(e)
        return None
#异步执行指令
async def execute_cmd_async(cmd: str, callback: Callable[[str], None]):
    """
    异步执行系统命令，并通过回调处理输出。   
    :param cmd: 要执行的命令字符串。
    :param callback: 命令执行完毕后的回调函数，接受一个字符串参数（命令的输出）。
    """
    print("execute cmd:"+cmd)
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if stdout:
        callback(stdout.decode('utf-8'))
    if stderr:
        print(f"Error: {stderr.decode('utf-8')}")  # 处理错误输出

async def handle_output(output: str):
    """示例回调函数，处理命令输出"""
    print(f"Command output: {output}")