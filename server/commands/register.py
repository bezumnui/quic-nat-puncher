import asyncio

from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

from clients import Clients
from command_consumer import CommandConsumer
from utils import CommandUtils, Utils

UUID_LEN = 36


class RegisterConsumer(CommandConsumer):
    PREFIX = "register:"

    def __init__(self, clients: Clients):
        self.clients = clients

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(4096)

        if not (text := Utils.decode_or_none(data)):
            return await CommandUtils.direct_write_eof(writer, "invalid data")

        arguments = text.split(":")

        if not len(arguments) == 2:
            return await CommandUtils.direct_write_eof(writer, "error:invalid amount of arguments")

        if len(id_ := arguments[1]) != UUID_LEN:
            return await CommandUtils.direct_write_eof(writer, "error:invalid id")

        if not (client := self.clients.get_client_or_None(id_)):
            print(client, self.clients.get_clients())
            return await CommandUtils.direct_write_eof(writer, "error:client was not found. try again")


        client.connection_id = id_
        print(f"{client} added")
        await asyncio.sleep(2)
        return await CommandUtils.direct_write_eof(writer, f"ack:{client.ip}:{client.port}")


    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)

