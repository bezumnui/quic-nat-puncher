import asyncio
import socket
from asyncio import BaseProtocol, DatagramTransport, StreamWriter, StreamReader

from aioquic.asyncio import QuicConnectionProtocol, connect
from aioquic.asyncio.server import QuicServer, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from cryptography.hazmat.primitives.keywrap import aes_key_wrap

from peer_connect import peer_connect, get_address, create_peer_protocol, create_peer_with_protocol, AtomicProtocol
from utils import create_ipv6_socket, create_socket, pipe_data

CONFIG = QuicConfiguration(is_client=True, verify_mode=False, alpn_protocols=["quic_punching"])

SOCKET_PORT = 0


async def send_command_to_host(command, server_ip, server_port):
    global SOCKET_PORT
    async with connect(server_ip, server_port, configuration=CONFIG, local_port=SOCKET_PORT) as connection:
        if not SOCKET_PORT:
            SOCKET_PORT = connection._transport.get_extra_info("sockname")[1]
            print(SOCKET_PORT)
        reader, writer = await connection.create_stream()
        writer.write(command)
        await writer.drain()

        if (data := await reader.read(1024)) == b"ack":
            return True

        print(f"Error: {data}")
        return False


async def request_ping(server_ip, server_port, host_ip, host_port):
    return await send_command_to_host(f"reqping:{host_ip}:{host_port}".encode(), server_ip, server_port)


async def punch(host_ip, host_port):
    return await send_command_to_host("punch".encode(), host_ip, host_port)


async def handle_local_connection_tcp(
        connection: QuicConnectionProtocol,
        tcp_reader: asyncio.StreamReader,
        tcp_writer: asyncio.StreamWriter,
) -> None:
    quic_reader, quic_writer = await connection.create_stream()

    await asyncio.gather(
        pipe_data(tcp_reader, quic_writer),
        pipe_data(quic_reader, tcp_writer),
    )


class UDPPipe(BaseProtocol):
    def __init__(self, protocol: QuicConnectionProtocol, pipe_socked: socket.socket):
        self.protocol: QuicConnectionProtocol = protocol
        self.pipe_socked = pipe_socked
        self.loop = asyncio.get_running_loop()
        self.quic_reader: StreamReader | None = None
        self.quic_writer: StreamWriter | None = None
        self.address = None

        asyncio.ensure_future(self.connect())

    async def connect(self):
        self.quic_reader, self.quic_writer = await self.protocol.create_stream()
        asyncio.ensure_future(self.read_server())

    async def disconnect(self):
        self.protocol.close()
        await self.protocol.wait_closed()

    def datagram_received(self, data: bytes, address: tuple[str, int]):
        if self.address is None:
            self.address = address

        if self.address != address:
            return

        async def handler():
            if not self.quic_writer or not self.quic_reader:
                return

            self.quic_writer.write(b"pipe:")
            self.quic_writer.write(len(data).to_bytes(2, "big"))
            self.quic_writer.write(data)
            await self.quic_writer.drain()

        asyncio.ensure_future(handler())

    async def read_server(self):
        try:
            while True:
                size_data = await self.quic_reader.readexactly(2)
                size = int.from_bytes(size_data, "big")

                data = await self.quic_reader.readexactly(size)
                await self.loop.sock_sendto(
                    self.pipe_socked,
                    data,
                    self.address,
                )

        except asyncio.IncompleteReadError:
            print("connection closed")
            pass


class PipeServer:
    def __init__(self, sock: socket.socket, host_ip: str, host_port: int):
        self.socket = sock
        self.host_port = host_port
        self.host_ip = host_ip

    def stream_handler(self, server_reader: asyncio.StreamReader, server_writer: asyncio.StreamWriter):
        asyncio.ensure_future(self.on_new_stream(server_reader, server_writer))

    async def on_new_stream(self, server_reader: asyncio.StreamReader, server_writer: asyncio.StreamWriter):
        async with peer_connect(self.socket, self.host_port, self.host_ip, ["quic-pipe"]) as connection:
            host_reader, host_writer = await connection.create_stream()

            await asyncio.gather(
                pipe_data(host_reader, server_writer),
                pipe_data(server_reader, host_writer, remove_bytes=len(b"pipe:")),
            )


async def start_peer(host_ip, host_port, is_tcp, server_ip):
    print(host_ip, host_port)
    local_ip = "127.0.0.1"
    local_port = 12666
    server_port = 12777

    print("First ping request..")

    if not await request_ping(server_ip, server_port, host_ip, host_port):
        return False

    print("Second ping request..")

    if not await request_ping(server_ip, server_port, host_ip, host_port):
        return False

    print("Ping requested. Timeout for NAT...")
    await asyncio.sleep(2)
    print("Timeout passed.")

    punch_success = False
    try:
        print("Punching the nat...")

        await punch(host_ip, host_port)
        punch_success = True
        print("Nat was punched successfully.")
    finally:
        if not punch_success:
            print("Failed to ping the host. Exit.")
            exit(1)

    async with connect(host_ip, host_port, configuration=CONFIG, local_port=SOCKET_PORT) as connection:

        if is_tcp:
            await asyncio.start_server(
                lambda reader, writer: handle_local_connection_tcp(connection, reader, writer),
                local_ip,
                local_port,
            )
            print("Mode: TCP")

        else:
            sock = create_socket(local_ip, local_port)
            loop = asyncio.get_running_loop()
            await loop.create_datagram_endpoint(
                lambda: UDPPipe(connection, sock),
                sock=sock
            )
            print("Mode: UDP")

        print(f"Successfully! Your address to connect is: {local_ip}:{local_port}")

        await asyncio.Future()
    return None
