import asyncio
import socket
import time

from host.command_consumer import HostCommandConsumer
from utils import CommandUtils, Utils


class InvalidConsumer(HostCommandConsumer):

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print(await reader.read(4096))

    async def can_consume(self, data: bytes):
        return True
