import asyncio
import random
import time
class HostServer:
    def __init__(self) -> None: 
        self.socketServerMap = None

        
    async def handle_client(self,reader, writer, port):
        try:
            data = await reader.read(1024)
            addr = writer.get_extra_info('peername')
            if self.socketServerMap.get(port) is None:
                return
            delay_min_time,delay_max_time = self.socketServerMap[port]['delay_min_time'], self.socketServerMap[port]['delay_max_time']
            delay = random.uniform(delay_min_time, delay_max_time)  # 生成1到5秒之间的随机延迟
            print(f"Simulating delay of {delay} seconds before responding...")
            await asyncio.sleep(delay)
            print(f"Sending confirmation to {addr} after delay")
            writer.write(b"TEST")
            await writer.drain()
            writer.close()
        except Exception as e:
            print(f"err:{e}")
        return 

    async def start_server(self,port,delay_min_time,delay_max_time):
        if self.socketServerMap.get(port) is not None:
            #只更新延迟时间
            server = self.socketServerMap.get(port)['server']
            self.socketServerMap[port]['delay_min_time']=delay_min_time
            self.socketServerMap[port]['delay_max_time']=delay_max_time
            return 'success'
        else:
            #启动新的服务器
            server = await asyncio.start_server(
                lambda r, w: self.handle_client(r, w, port), 
                '0.0.0.0', port)
            addr = server.sockets[0].getsockname()
            print(f'Server started on {addr}')
            self.socketServerMap[port]={
                "server":server,
                "delay_min_time":delay_min_time,  
                "delay_max_time":delay_max_time
            }
            print(f"Server is listening on port {port}...")
            print(f"delay_min_time:{delay_min_time},delay_max_time:{delay_max_time}")
            #启动新的协程任务
            asyncio.create_task(self.run_server_forever(server))
            return 'success'
    async def run_server_forever(self, server):
        async with server:
            await server.serve_forever()
    async def start_server_on_port_delay_response(self,port,delay_min_time,delay_max_time):
        if self.socketServerMap == None:
            self.socketServerMap = {}
        return await self.start_server(port,delay_min_time,delay_max_time)

# if __name__ == "__main__":
#     asyncio.run(HostServer().start_server_on_port_delay_response(80,1,10))