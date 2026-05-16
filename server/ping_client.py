import asyncio
import os
import platform
import socket
from contextlib import asynccontextmanager

from peer_connect import peer_connect
from utils import create_ipv6_socket


class PingClient:
    def __init__(self, port: int):
        self.port = port
        self.socket = create_ipv6_socket("::", port)
        self.mutex = asyncio.Lock()

    def get_socket_dup(self):
        if platform.system().lower() == "windows":
            return socket.fromshare(self.socket.share(os.getpid()))
        return self.socket.dup()

    @asynccontextmanager
    async def connect(self, host, port, alpn_protocols=None):
        try:
            await self.mutex.acquire()

            async with peer_connect(self.get_socket_dup(), host, port, alpn_protocols) as connection:
                yield connection
        finally:
            self.mutex.release()
