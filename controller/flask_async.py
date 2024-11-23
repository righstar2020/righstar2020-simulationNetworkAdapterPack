from flask import Flask, jsonify, has_request_context, copy_current_request_context
from functools import wraps
from concurrent.futures import Future, ThreadPoolExecutor
import asyncio

#异步flask修饰器
#可指定使用的事件循环(对象在同一事件循环里才可访问)
def run_async(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        call_result = Future()
        def _run():
    
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(func(*args, **kwargs))
            except Exception as error:
                call_result.set_exception(error)
            else:
                call_result.set_result(result)
            finally:
                loop.close()

        loop_executor = ThreadPoolExecutor(max_workers=1)
        if has_request_context():
            _run = copy_current_request_context(_run)
        loop_future = loop_executor.submit(_run)
        loop_future.result()
        return call_result.result()

    return _wrapper