import asyncio
import logging

from command_consumer import CommandConsumer


class QuicListener:
    BUFFER_SIZE = 4096

    def __init__(self, commands: list[CommandConsumer], loop: asyncio.AbstractEventLoop = None):
        self.loop = loop
        self.commands = commands
        self.buffer_size = self.BUFFER_SIZE

    def stream_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        asyncio.ensure_future(self.on_new_message(reader, writer))

    async def on_new_message(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(4096)
        for command in self.commands:
            try:
                if await command.try_consume(data, reader, writer):
                    return
            except Exception as e:
                logging.exception(e)
