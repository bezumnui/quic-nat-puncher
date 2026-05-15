import asyncio
from asyncio import BaseProtocol

from clients import Clients, Client
from utils import Utils



class UdpListener(BaseProtocol):
    UUID_LEN = 36
    TIMEOUT_SECONDS = 10

    def __init__(self, clients: Clients):
        self.clients = clients

    def datagram_received(self, data: bytes, address: tuple[str, int]):
        asyncio.ensure_future(self.on_datagram_received(data, address))

    async def on_datagram_received(self, data: bytes, address: tuple[str, int]):
        if not (text := Utils.decode_or_none(data)):
            return

        if not len(arguments := text.split(":")) == 2:
            return

        if not arguments[0] == "open_connection":
            return

        if not (id_ := arguments[1]).isdigit() != self.UUID_LEN:
            return

        print("New client:", id_)
        await self.clients.add_client(id_, Client(address[0], address[1], None))
        await self.dispose_unassigned_client(id_, self.TIMEOUT_SECONDS)

    async def dispose_unassigned_client(self, id_: str, timeout_seconds: float):
        await asyncio.sleep(timeout_seconds)
        if not (client := self.clients.get_client_or_None(id_)):
            return

        client: Client
        if not client.connection_id:
            await self.clients.remove_client_by_id(id_)

