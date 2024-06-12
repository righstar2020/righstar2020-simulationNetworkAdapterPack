
import asyncio
from conn import Client
if __name__ == "__main__":
    client = Client('10.0.0.1', 8888)
    asyncio.run(client.run())