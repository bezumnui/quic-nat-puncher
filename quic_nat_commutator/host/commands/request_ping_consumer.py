import asyncio
import socket

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils


class RequestPingConsumerHost(HostCommandConsumer):
    PREFIX = "reqping"

    def __init__(self, sock: socket.socket, uuid: str):
        self.uuid = uuid
        self.socket = sock


    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print('requesting ping')

        if not (text := Utils.decode_or_none(await reader.read(4096))):
            return await CommandUtils.direct_write_eof(writer, "nack:invalid data")

        arguments = text.split(":")

        if len(arguments) != 4:
            return await CommandUtils.direct_write_eof(writer, "nack:invalid format")

        _, ip, port_raw, uuid = arguments
        if not (port := Utils.int_or_none(port_raw)):
            return await CommandUtils.direct_write_eof(writer, "nack:port is not numeric")

        if self.uuid != uuid:
            return await CommandUtils.direct_write_eof(writer, "nack:uuid is invalid")

        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self.socket, b"punch", (ip, port))
        await asyncio.sleep(1)
        await loop.sock_sendto(self.socket, b"punch", (ip, port))
        writer.write(b"ack")
        await writer.drain()
        writer.write_eof()
        return None

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)