import socket
import time
import random  # 引入random模块来生成随机延迟时间，仅作示例

hostServer = None
def get_server_instance():
    global hostServer
    if hostServer is None:
        hostServer = HostServer()
    return hostServer

class HostServer:
    def __init__(self):
        self.socketServerMap = {}
    def handle_request(self,client_socket,port):
        if self.socketServerMap.get(port) is None:
            return
        delay_min_time,delay_max_time = self.socketServerMap[port].delay_min_time, self.socketServerMap[port].delay_max_time
        delay = random.randint(delay_min_time,delay_max_time)  # 生成1到5秒之间的随机延迟
        print(f"Simulating delay of {delay} seconds before responding...")
        time.sleep(delay)  # 引入延迟
        response = "Hello, this response was delayed by the server.\n".encode('utf-8')
        client_socket.sendall(response)
        client_socket.close()

    def start_server_on_port_delay_response(self,port,delay_min_time,delay_max_time):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.socketServerMap.get(port) is not None:
            #只更新延迟时间
            server_socket = self.socketServerMap.get(port).server_socket
            self.socketServerMap[port].delay_min_time=delay_min_time
            self.socketServerMap[port].delay_max_time=delay_max_time
        else:
            server_address = ('', port)  # 使用空字符串''表示绑定到所有可用的网络接口，80是端口号
            server_socket.bind(server_address)
            server_socket.listen(5)
            self.socketServerMap[port]={
                "server_socket":server_socket,
                "delay_min_time":delay_min_time,  
                "delay_max_time":delay_max_time
            }
            print("Server is listening on port 80...")
            print(f"delay_min_time:{delay_min_time},delay_max_time:{delay_max_time}")
            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")
                self.handle_request(client_socket,80)  # 调用处理请求的函数，包含延迟逻辑

if __name__ == "__main__":
    get_server_instance().start_server_on_port_delay_response(80,1,10)
