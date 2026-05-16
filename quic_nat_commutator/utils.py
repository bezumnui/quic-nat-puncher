import asyncio
import socket

from aioquic.quic.events import StreamDataReceived


class CommandUtils:
    @staticmethod
    def has_prefix(data: bytes, prefix: str):
        size = len(prefix)
        if len(data) < size:
            return False

        try:
            return data[:size].decode() == prefix
        except UnicodeDecodeError:
            return False

    @staticmethod
    async def direct_write_eof(writer: asyncio.StreamWriter, text: str):
        writer.write(text.encode())
        await writer.drain()
        writer.write_eof()



class Utils:
    @staticmethod
    def int_or_none(text: str) -> int | None:
        if text.isdigit():
            return int(text)
        return None

    @staticmethod
    def decode_or_none(data: bytes) -> str | None:
        try:
            return data.decode()
        except UnicodeDecodeError:
            return None

async def pipe_data(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, prefix: bytes = b'', remove_bytes = 0):
    if remove_bytes:
        await reader.read(remove_bytes)
    while len(data := await reader.read(4096)) > 0:
        if data == b'ack':
            continue
        if prefix:
            writer.write(prefix)
        writer.write(data)
        await writer.drain()


def create_socket(host=None, port=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if host and port:
        sock.bind((host, port))
    sock.setblocking(False)
    return sock

def create_ipv6_socket(local_host="::", local_port=0):
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    completed = False
    try:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind((local_host, local_port, 0, 0))
        completed = True
    finally:
        if not completed:
            sock.close()

    return sock
