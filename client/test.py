from flask import Flask, jsonify
import asyncio
import threading
from asyncio import Queue

app = Flask(__name__)

async def producer(queue):
    """模拟生产者，向队列中放入消息"""
    for i in range(5):
        await queue.put(f"Message {i}")
        print(f"Produced: Message {i}")
        await asyncio.sleep(1)

@app.route('/get_message', methods=['GET'])
async def get_message():
    """异步视图，从队列中获取并返回一条消息"""
    try:
        message = await queue.get()  # 直接使用await获取队列中的消息
        queue.task_done()  # 标记消息处理完成
        return jsonify({"message": message})
    except asyncio.QueueEmpty:
        return jsonify({"error": "No message available"}), 404
    except:
        return jsonify({"error": "No message available"}), 404

async def periodic_producer(queue):
    """定期运行生产者任务的协程"""
    while True:
        await producer(queue)
        await asyncio.sleep(10)  # 为了演示，每10秒生产一批消息

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
def add_background_coroutine_tasks(loop, coroutine_func, *args):
    """添加协程任务"""
    asyncio.run_coroutine_threadsafe(coroutine_func(*args), loop)

loop = asyncio.get_event_loop()
queue = Queue()

if __name__ == '__main__':
    #启动一个事件循环子线程,并使线程作为daemon(主线程退出则子线程退出)
    threading.Thread(target=start_loop, args=(loop,), daemon=True).start()
    add_background_coroutine_tasks(loop,periodic_producer,queue)
    app.run(debug=True, use_reloader=False)  # 注意：use_reloader=False 防止重载时创建多个事件循环