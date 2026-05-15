import asyncio
import socket
import time
from asyncio import BaseProtocol, DatagramTransport, StreamReader, StreamWriter, IncompleteReadError

from aioquic.asyncio import QuicConnectionProtocol

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils, create_socket, pipe_data


class PipeConsumer(HostCommandConsumer):
    PREFIX = "pipe:"

    def __init__(self, ip: str, port: int, is_tcp = True):
        self.is_tcp = is_tcp
        self.port = port
        self.ip = ip
        self.socket = create_socket()
        self.socket.connect((self.ip, self.port))
        self.loop = asyncio.get_running_loop()

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if self.is_tcp:
            await self.send_by_tcp(reader, writer)
        else:
            await asyncio.gather(
                self.send_to_local(reader),
                self.send_to_remote(writer)
            )

    async def send_to_remote(self, writer):
        while True:
            data, address = await self.loop.sock_recvfrom(self.socket, 4096)
            print(data, address)
            if not data:
                break

            writer.write(len(data).to_bytes(2, "big"))
            writer.write(data)
            await writer.drain()

    async def send_to_local(self, reader):
        while True:
            try:
                if not await reader.readexactly(len(self.PREFIX)):
                    print("Peer closed the connection")
                    break
            except IncompleteReadError:
                print("Peer closed the connection due to timeout")
                break

            size_data = await reader.readexactly(2)
            print("size_data: ", size_data)
            size = int.from_bytes(size_data, "big")

            data = await reader.readexactly(size)

            print(data)
            await self.loop.sock_sendall(
                self.socket,
                data,
            )
            print("sent")

    async def send_by_tcp(self, reader, writer):
        local_reader, local_writer = await asyncio.open_connection(
            self.ip,
            self.port,
        )
        await asyncio.gather(
            pipe_data(local_reader, writer, self.PREFIX.encode()),
            pipe_data(reader, local_writer, remove_bytes=len(self.PREFIX) + 2)
        )

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)


