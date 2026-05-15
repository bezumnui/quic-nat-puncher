import asyncio
import socket

from aioquic.quic.events import StreamDataReceived


class CommandUtils:
    @staticmethod
    def has_prefix(data: bytes, prefix: str):
        size = len(prefix)
        if len(data) < size:
            return None

        try:
            return data[:size].decode() == prefix
        except UnicodeDecodeError:
            return None

    @staticmethod
    async def direct_write_eof(writer: asyncio.StreamWriter, data: str):
        writer.write(data.encode())
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


def create_socket(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.setblocking(False)
    return sock
