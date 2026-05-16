import asyncio
import socket
import time

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils


class PingConsumerHost(HostCommandConsumer):
    PREFIX = "ping"

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await reader.readexactly(len(self.PREFIX))
        writer.write(b"pong")
        await writer.drain()

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)
