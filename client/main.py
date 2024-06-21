
import asyncio
from conn import Client
if __name__ == "__main__":
    #这个IP暂时不能改,后端Server端通信接口在第一台交换机eth1口上
    client = Client('10.0.0.252', 8888)
    asyncio.run(client.run())