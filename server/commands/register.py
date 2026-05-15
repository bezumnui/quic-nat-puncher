import asyncio

from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

from clients import Clients
from command_consumer import CommandConsumer

from ping_client import PingClient
from utils import CommandUtils, Utils

UUID_LEN = 36


class RegisterConsumer(CommandConsumer):
    PREFIX = "register:"

    def __init__(self, clients: Clients, ping_client: PingClient):
        self.ping_client: PingClient = ping_client
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
        asyncio.ensure_future(self.nat_puncher(client.ip, client.port))
        # await asyncio.sleep(2)
        return await CommandUtils.direct_write_eof(writer, f"ack:{client.ip}:{client.port}")


    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)

    async def nat_puncher(self, address, port):
        while True:
            loop = asyncio.get_running_loop()
            # socket = self.ping_client.get_socket_dup()
            try:
                async with self.ping_client.mutex:
                    await loop.sock_sendto(self.ping_client.socket, b"punch",  ("::ffff:" + address, port, 0, 0))
                await asyncio.sleep(4)
            except OSError as error:
                print(f"nat_puncher send failed: {error}")

            await asyncio.sleep(1)

