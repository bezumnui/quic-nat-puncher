import asyncio
import os
import platform
import socket
import uuid

from aioquic.asyncio import connect
from aioquic.asyncio.server import QuicServer
from aioquic.quic.configuration import QuicConfiguration

from host.command_consumer import HostCommandConsumer
from host.commands.invalid_consumer import InvalidConsumer
from host.commands.pipe_consumer import PipeConsumer
from host.commands.punch_consumer import PunchConsumerHost
from host.commands.request_ping_consumer import RequestPingConsumerHost
from utils import create_socket, Utils



class QuicListener:
    BUFFER_SIZE = 4096

    def __init__(self, commands: list[HostCommandConsumer]):
        self.commands = commands

    def stream_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print('streaming request')
        asyncio.ensure_future(self.on_new_message(reader, writer))

    async def on_new_message(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(4096)
        print("data recieved", data)
        for command in self.commands:
            if await command.try_consume(data, reader, writer):
                return


async def nat_puncher(sock: socket.socket, server_address, server_udp_port, server_ping_port):
    # while True:
    loop = asyncio.get_running_loop()
    try:
        await loop.sock_sendto(sock, b"punch", (server_address, server_udp_port))
        await loop.sock_sendto(sock, b"punch", (server_address, server_ping_port))
        await asyncio.sleep(4)
    except OSError as error:
        print(f"nat_puncher send failed: {error}")

    await asyncio.sleep(1)

def get_socket_dup(sock):
    if platform.system().lower() == "windows":
        return socket.fromshare(sock.share(os.getpid()))
    return sock.dup()


async def print_server(sock):
    loop = asyncio.get_event_loop()
    d, a =await loop.sock_recvfrom(sock, 4096)
    print(d, a, "received")

async def start_host(server_address, local_port, is_tcp):
    print(local_port)
    server_quic_port = 12777
    server_udp_port = 12767
    server_ping_port = 12677

    sock = create_socket()
    id_ = str(uuid.uuid4())




    # asyncio.ensure_future(print_server(sock))
    config = QuicConfiguration(
        is_client=True,
        alpn_protocols=["quic_punching"],
        verify_mode=False
    )


    sock.sendto(f"open_connection:{id_}".encode(), (server_address, server_udp_port))

    await nat_puncher(sock, server_address, server_udp_port, server_ping_port)
    print("open_connection sent")

    await asyncio.sleep(1)
    print("Connection to the server..")
    transport = await start_server(sock, id_, local_port, is_tcp)


    async with connect(server_address, server_quic_port, configuration=config) as connection:
        print("Connected.")
        reader, writer = await connection.create_stream()
        writer.write(f"register:{id_}".encode())
        await writer.drain()
        response = await reader.read(1024)

        if not (text := Utils.decode_or_none(response)):
            print(f"Failed to register: {response}")
            return

        if not len(args := text.split(":")) == 3:
            print(f"Invalid arguments:", args)
            return

        _, ip, port = args
        print(f"Successfully! Your global ip: {ip}:{port}. Provide this address to a peer.")

    try:
        await asyncio.Future()
    finally:
        transport.close()


async def start_server(sock: socket, id_: str, local_port, is_tcp):
    local_host = "127.0.0.1"

    server_config = QuicConfiguration(
        is_client=False,
        alpn_protocols=["quic_punching"],
    )
    server_config.load_cert_chain("cert.pem", "key.pem")

    listener = QuicListener([PipeConsumer(local_host, local_port, is_tcp), RequestPingConsumerHost(sock, id_), PunchConsumerHost(), InvalidConsumer()])

    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: QuicServer(
            configuration=server_config,
            stream_handler=listener.stream_handler,
        ),
        sock=sock
    )
    return transport


if __name__ == '__main__':
    asyncio.run(start_host())
