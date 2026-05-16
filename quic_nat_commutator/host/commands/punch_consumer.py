import asyncio
import socket
import time

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils


class PunchConsumerHost(HostCommandConsumer):
    PREFIX = "punch"

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await reader.readexactly(len(self.PREFIX))
        writer.write(b"ack")
        await writer.drain()
        pass

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)
