import asyncio
import socket
import time

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils


class PunchConsumerHost(HostCommandConsumer):
    PREFIX = "punch"

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        writer.write(b"ack")
        await writer.drain()
        print("punch")
        pass

    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)
