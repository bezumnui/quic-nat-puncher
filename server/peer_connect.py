import asyncio
import socket
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection


async def get_address(host, port):
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
    addr = infos[0][4]
    if len(addr) == 2:
        addr = ("::ffff:" + addr[0], addr[1], 0, 0)
    return addr


@asynccontextmanager
async def peer_connect(sock, host, port, alpn_protocols=None, close_transport=False) -> AsyncGenerator[QuicConnectionProtocol, None]:
    if alpn_protocols is None:
        alpn_protocols = ["quic_punching"]

    loop = asyncio.get_running_loop()
    config = QuicConfiguration(
        verify_mode=False,
        is_client=True,
        alpn_protocols=alpn_protocols
    )

    connection = QuicConnection(
        configuration=config,
    )

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: QuicConnectionProtocol(connection),
        sock=sock,
    )

    try:
        protocol.connect(await get_address(host, port), transmit=True)
        await protocol.wait_connected()
        yield protocol

    finally:
        protocol.close()
        await protocol.wait_closed()
        if close_transport:
            transport.close()

def create_peer_protocol():
    loop = asyncio.get_running_loop()
    config = QuicConfiguration(
        verify_mode=False,
        is_client=True,
        alpn_protocols=["quic_punching"]
    )

    connection = QuicConnection(
        configuration=config,
    )

    return QuicConnectionProtocol(connection)


class AtomicProtocol:
    def __init__(self):
        self.protocol = None

@asynccontextmanager
async def create_peer_with_protocol(host, port, protocol) -> AsyncGenerator[QuicConnectionProtocol, None]:
    try:
        protocol.connect(await get_address(host, port), transmit=True)
        await protocol.wait_connected()
        yield protocol

    finally:
        protocol._quic.close(error_code=0, reason_phrase="done")
        protocol.transmit()
        # protocol.close()
        # await protocol.wait_closed()

