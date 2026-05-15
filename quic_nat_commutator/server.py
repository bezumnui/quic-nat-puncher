import abc
import asyncio
import dataclasses
import logging
from asyncio import Queue

from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

from quic_nat_commutator.one_port_quic_peer import OnePortQuicPeer, QuicSession
from quic_nat_commutator.utils import CommandUtils, Utils


class CommandConsumer(abc.ABC):
    async def try_consume(self, session: QuicSession, data: StreamDataReceived):
        if await self.can_consume(data):
            await self.consume(session, data)
            return True

        return False

    @abc.abstractmethod
    async def consume(self, session: QuicSession, data: StreamDataReceived):
        pass

    @abc.abstractmethod
    async def can_consume(self, data: StreamDataReceived):
        pass


@dataclasses.dataclass
class Client:
    ip: str
    port: int


class Clients:
    def __init__(self):
        self.clients = {}
        self.mutex = asyncio.Lock
        self.free_queue = Queue()

    def get_client(self, id_: int):
        return self.clients.get(id_, None)

    def get_clients(self):
        return self.clients.values()

    def update_client(self, id_: int, client: Client):
        with self.mutex:
            self.clients.update({id_: client})

    def wait_for_removal(self):
        pass

    def remove_client_by_id(self, id_: int):
        with self.mutex:
            self.remove_client_by_id(id_)


# class AskForPing(CommandConsumer):
#     COMMAND = "ping"
#     BUFFER_SIZE = 4096
#
#     async def consume(self, session: QuicSession, data: StreamDataReceived):
#         text = Utils.decode_or_none(data.data)
#
#         if not text:
#             return None
#
#         arguments = text.split()
#         if len(arguments) < 3:
#             return await CommandUtils.direct_write(writer, b"error. not enough arguments.")
#
#         ip = arguments[1]
#         port = Utils.int_or_none(arguments[2])
#
#         if not ip or not port:
#             return await CommandUtils.direct_write(writer, b"error. invalid ip or port.")
#
#         CommandUtils.direct_write(writer, b"pinging")
#
#     async def can_consume(self, data: bytes):
#         return CommandUtils.has_prefix(data, self.COMMAND)


# class AddClientPing(CommandConsumer):
#     COMMAND = "add"
#     BUFFER_SIZE = 4096
#
#     def __init__(self, clients: Clients):
#         self.clients = clients
#
#     async def consume(self, session: QuicSession, data: StreamDataReceived):
#
#
#     async def can_consume(self, data: StreamDataReceived):
#         return CommandUtils.has_prefix(data, self.COMMAND)


class QuicListener:
    BUFFER_SIZE = 4096

    def __init__(self, commands: list[CommandConsumer], loop: asyncio.EventLoop = None):
        self.loop = loop
        self.commands = commands
        self.buffer_size = self.BUFFER_SIZE

    async def on_new_message(self, session: QuicSession, data: StreamDataReceived):
        session.connection.send_datagram_frame(b"hello")

        for command in self.commands:
            try:
                if await command.try_consume(session, data):
                    return
            except Exception as e:
                logging.exception(e)



async def main():
    host = "localhost"
    port = 12715

    server_config = QuicConfiguration(
        is_client=False,
        alpn_protocols=["my-proto"],
    )

    client_config = QuicConfiguration(
        is_client=True,
        alpn_protocols=["my-proto"],
    )

    server_config.load_cert_chain("cert.pem", "key.pem")

    listener = QuicListener([])
    server = OnePortQuicPeer(host, port, server_config, client_config, listener.on_new_message)
    asyncio.create_task(server.receive_loop())

    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
