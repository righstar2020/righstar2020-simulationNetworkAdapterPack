import socket
import time
import asyncio

class ScanHost():
    def __init__(self):
        pass
    async def scan_and_test_connection(self, ip, port):
        start_time = time.time()
        try:
            # 直接尝试异步连接，利用超时来判断端口是否响应
            reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=20)
            
            print(f"Port {port}: OPEN, Starting connection test...")
            # 发送测试数据
            writer.write(b"TEST")
            await writer.drain()
            
            # 接收服务器响应
            response = await reader.read(1024)
            response_time = time.time() - start_time
            writer.close()
            return port, response_time
    
        except asyncio.TimeoutError:
            # 超时则认为端口未响应或服务无反应
            return 0, 0   
        except Exception as e:
            return 0, 0

    async def start_scan(self, target_ip):
        port_range = range(1, 1000)  # 1-1000的端口
        tasks = [self.scan_and_test_connection(target_ip, port) for port in port_range]
        done, _ = await asyncio.wait(tasks)  # 等待所有任务完成或任何一个抛出异常

        port_scan_results = []
        for future in done:
            port, response_time = future.result()
            if response_time is not None and response_time > 0:  # 确保response_time有效且非零
                print(f"Port {port}: OPEN, connection test success!")
                port_scan_results.append({
                    'port': port,
                    'response_time': response_time
                })
        
        return port_scan_results