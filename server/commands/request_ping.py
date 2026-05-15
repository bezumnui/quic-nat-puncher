import asyncio
import logging

from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

from clients import Clients
from command_consumer import CommandConsumer
from commands.register import UUID_LEN
from utils import Utils, CommandUtils


class RequestPingConsumer(CommandConsumer):
    PREFIX = "reqping:"

    # reqping:0.0.0.0:54345 peer-to-server
    # reqping:0.0.0.0:12345:uuid server-to-host

    def __init__(self, clients: Clients):
        self.clients = clients

    async def consume(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print('requesting ping')
        data = await reader.read(4096)

        if not (text := Utils.decode_or_none(data)):
            return await CommandUtils.direct_write_eof(writer, "invalid data")

        arguments = text.split(":")

        if len(arguments) != 3:
            return await CommandUtils.direct_write_eof(writer, "error:invalid amount of arguments")

        command, destination_ip, destination_port_raw = arguments

        if not (destination_port := Utils.int_or_none(destination_port_raw)):
            return await CommandUtils.direct_write_eof(writer, "error:port not a number")

        if not (client := self.clients.get_client_with_address(destination_ip, destination_port)):
            return await CommandUtils.direct_write_eof(writer, "error:client was not found")

        try:
            await self.send_to_host(client, destination_ip, destination_port, writer)

        except Exception as e:
            await CommandUtils.direct_write_eof(writer, f"nack:internal error")
            logging.error(e)

    async def send_to_host(self, client, destination_ip, destination_port, writer):
        async with connect(destination_ip, destination_port,
                           configuration=QuicConfiguration(is_client=True, verify_mode=False,
                                                           alpn_protocols=["quic_punching"], )) as connection:
            ip, port = writer.__getattribute__("peer_address")
            client_reader, client_writer = await connection.create_stream()
            client_writer.write(f"reqping:{ip}:{port}:{client.connection_id}".encode())
            await client_writer.drain()

            if await client_reader.read(1024):
                await CommandUtils.direct_write_eof(writer, f"ack")
            else:
                await CommandUtils.direct_write_eof(writer, f"nack:host failed")


    async def can_consume(self, data: bytes):
        return CommandUtils.has_prefix(data, self.PREFIX)
