import asyncio

from aioquic.asyncio.server import serve
from aioquic.quic.configuration import QuicConfiguration

from clients import Clients
from commands.register import RegisterConsumer
from commands.request_ping import RequestPingConsumer
from ping_client import PingClient
from quic_listener import QuicListener
from server_protocol import PeerAwareQuicProtocol
from udp_listener import UdpListener
from utils import create_socket


async def main():
    host = "0.0.0.0"
    quick_port = 12777
    udp_port = 12767
    ping_port = 12677

    clients = Clients()

    await start_quic(host, quick_port, clients, ping_port)
    await start_udp(host, udp_port, clients)

    await asyncio.Future()


async def start_udp(host, udp_port, clients):
    sock = create_socket(host, udp_port)
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(lambda: UdpListener(clients), sock=sock)


async def start_quic(host, quick_port, clients, ping_port):
    server_config = QuicConfiguration(
        is_client=False,
        alpn_protocols=["quic_punching"],
    )
    server_config.load_cert_chain("cert.pem", "key.pem")
    ping_client = PingClient(ping_port)
    listener = QuicListener([
        RequestPingConsumer(clients, ping_client),
        RegisterConsumer(clients, ping_client)
    ])
    await serve(host, quick_port, configuration=server_config, stream_handler=listener.stream_handler, create_protocol=PeerAwareQuicProtocol)


if __name__ == '__main__':
    asyncio.run(main())
