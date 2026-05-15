import abc
import asyncio


class CommandConsumer(abc.ABC):
    async def try_consume(self, data: bytes, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if await self.can_consume(data):
            reader.feed_data(data)
            await self.consume(reader, writer)
            return True

        return False

    @abc.abstractmethod
    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        pass

    @abc.abstractmethod
    async def can_consume(self, data: bytes):
        pass
