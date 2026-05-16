import asyncio
from asyncio import IncompleteReadError

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, create_socket


class PipeConsumer(HostCommandConsumer):
    PREFIX = b"pipe:"
    CLOSE_PREFIX = b"close"
    PUNCH_PREFIX = b"punch"

    def __init__(self, ip: str, port: int, is_tcp=True):
        self.is_tcp = is_tcp
        self.port = port
        self.ip = ip
        self.socket = create_socket()
        self.socket.connect((self.ip, self.port))
        self.loop = asyncio.get_running_loop()

        self.tcp_readers: dict[int, asyncio.StreamReader] = {}
        self.tcp_writers: dict[int, asyncio.StreamWriter] = {}
        self.write_mutex = asyncio.Lock()

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if self.is_tcp:
            await self.consume_tcp(reader, writer)
            return

        await asyncio.gather(
            self.send_to_local(reader),
            self.send_to_remote(writer),
        )

    async def consume_tcp(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await self.read_from_peer(reader, writer)

    async def read_from_peer(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        while True:
            try:
                message_type = await reader.readexactly(5)

                if message_type == self.PUNCH_PREFIX:
                    continue

                if message_type == self.CLOSE_PREFIX:
                    connection_id = int.from_bytes(await reader.readexactly(4), "big")
                    await self.close_local_connection(connection_id)
                    continue

                if message_type != self.PREFIX:
                    print("unknown tcp message:", message_type)
                    continue

                connection_id = int.from_bytes(await reader.readexactly(4), "big")
                size = int.from_bytes(await reader.readexactly(2), "big")
                data = await reader.readexactly(size)

                local_writer = await self.get_or_create_local_connection(
                    connection_id,
                    writer,
                )

                local_writer.write(data)
                await local_writer.drain()

            except IncompleteReadError:
                print("peer closed tcp pipe")
                break

    async def get_or_create_local_connection(
        self,
        connection_id: int,
        peer_writer: asyncio.StreamWriter,
    ) -> asyncio.StreamWriter:
        existing_writer = self.tcp_writers.get(connection_id)

        if existing_writer is not None:
            return existing_writer

        local_reader, local_writer = await asyncio.open_connection(
            self.ip,
            self.port,
        )

        self.tcp_readers[connection_id] = local_reader
        self.tcp_writers[connection_id] = local_writer

        asyncio.create_task(
            self.forward_local_to_peer(
                connection_id,
                local_reader,
                peer_writer,
            )
        )

        return local_writer

    async def forward_local_to_peer(
        self,
        connection_id: int,
        local_reader: asyncio.StreamReader,
        peer_writer: asyncio.StreamWriter,
    ):
        try:
            while True:
                data = await local_reader.read(4096)

                if not data:
                    break

                async with self.write_mutex:
                    peer_writer.write(self.PREFIX)
                    peer_writer.write(connection_id.to_bytes(4, "big"))
                    peer_writer.write(len(data).to_bytes(2, "big"))
                    peer_writer.write(data)
                    await peer_writer.drain()

        finally:
            await self.close_local_connection(connection_id)

            async with self.write_mutex:
                peer_writer.write(self.CLOSE_PREFIX)
                peer_writer.write(connection_id.to_bytes(4, "big"))
                await peer_writer.drain()

    async def close_local_connection(self, connection_id: int):
        self.tcp_readers.pop(connection_id, None)

        local_writer = self.tcp_writers.pop(connection_id, None)

        if local_writer is None:
            return

        local_writer.close()
        await local_writer.wait_closed()

    async def send_to_remote(self, writer):
        while True:
            data, address = await self.loop.sock_recvfrom(self.socket, 4096)

            if not data:
                break

            async with self.write_mutex:
                writer.write(self.PREFIX)
                writer.write(len(data).to_bytes(2, "big"))
                writer.write(data)
                await writer.drain()

        print("eof send_to_remote")

    async def send_to_local(self, reader):
        while True:
            try:
                message_type = await reader.readexactly(5)

                if message_type == self.PUNCH_PREFIX:
                    continue

                if message_type != self.PREFIX:
                    print("unknown udp message:", message_type)
                    continue

                size = int.from_bytes(await reader.readexactly(2), "big")
                data = await reader.readexactly(size)

                await self.loop.sock_sendall(self.socket, data)

            except IncompleteReadError:
                print("peer closed udp pipe")
                break

        print("eof send_to_local")

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX.decode())