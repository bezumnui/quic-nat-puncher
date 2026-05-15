import asyncio
from typing import Optional, Tuple

from aioquic.asyncio.protocol import QuicConnectionProtocol


class PeerAwareQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, stream_handler=None, **kwargs):
        self.peer_address: Optional[Tuple[str, int]] = None
        self.user_stream_handler = stream_handler

        super().__init__(
            *args,
            stream_handler=self.stream_handler_with_peer,
            **kwargs,
        )

    def datagram_received(self, data: bytes, address) -> None:
        self.peer_address = address
        super().datagram_received(data, address)

    def stream_handler_with_peer(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        writer.peer_address = self.peer_address

        if self.user_stream_handler is not None:
            self.user_stream_handler(reader, writer)