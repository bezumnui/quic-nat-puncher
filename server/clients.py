import asyncio
import dataclasses
from asyncio import Queue
from typing import Optional


@dataclasses.dataclass
class Client:
    ip: str
    port: int
    connection_id: Optional[str]

class Clients:
    def __init__(self):
        self.clients: dict[str, Client] = {}
        self.mutex = asyncio.Lock()
        self.free_queue = Queue()

    def get_client_or_None(self, id_: str) -> Client | None:
        return self.clients.get(id_, None)

    def get_client_with_address(self, ip: str, port: int):
        for client in self.clients.values():
            if client.ip == ip and client.port == port:
                return client

        return None

    def get_clients(self):
        return self.clients.values()

    async def add_client(self, id_: str, client: Client):
        async with self.mutex:
            if self.clients.get(id_, None):
                return False

            self.clients.update({id_: client})
            return True

    def wait_for_removal(self):
        pass

    async def remove_client_by_id(self, id_: str):
        async with self.mutex:
            self.clients.pop(id_)
