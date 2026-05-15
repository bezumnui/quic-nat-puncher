import asyncio
import logging
import socket
import typing
from dataclasses import dataclass

from aioquic.buffer import Buffer
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection, NetworkAddress
from aioquic.quic.events import StreamDataReceived, ProtocolNegotiated
from aioquic.quic.packet import PACKET_TYPE_INITIAL, pull_quic_header


@dataclass
class QuicSession:
    connection: QuicConnection
    remote_address: NetworkAddress


ReceiverHandler = typing.Callable[[QuicSession, StreamDataReceived], typing.Awaitable[None]]


class OnePortQuicPeer:
    def __init__(self, bind_host: str, bind_port: int, server_configuration: QuicConfiguration,
                 client_configuration: QuicConfiguration, receiver: ReceiverHandler) -> None:
        self.receiver = receiver
        self.sessions: dict[bytes, QuicSession] = {}

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setblocking(False)
        self.udp_socket.bind((bind_host, bind_port))

        self.event_loop = asyncio.get_running_loop()

        self.server_configuration = server_configuration
        self.client_configuration = client_configuration

    async def receive_loop(self) -> None:
        while True:
            packet_data, remote_address = await self.event_loop.sock_recvfrom(
                self.udp_socket,
                65535,
            )
            try:
                await self.handle_udp_packet(packet_data, remote_address)
            except Exception as e:
                logging.error(e)

    async def handle_udp_packet(self, packet_data: bytes, remote_address: NetworkAddress) -> None:
        header = pull_quic_header(
            Buffer(data=packet_data),
            host_cid_length=8,
        )

        destination_connection_id = header.destination_cid

        session = self.sessions.get(destination_connection_id)

        if session is None:
            if header.packet_type != PACKET_TYPE_INITIAL:
                return

            session = self.create_server_session(
                original_destination_connection_id=destination_connection_id,
                remote_address=remote_address,
            )

        session.connection.receive_datagram(
            packet_data,
            remote_address,
            now=self.event_loop.time(),
        )
        try:
            await self.process_events(session)
        except Exception as e:
            logging.error(e)

        self.flush_pending_datagrams(session)

    def create_server_session(
            self,
            original_destination_connection_id: bytes,
            remote_address: NetworkAddress,
    ) -> QuicSession:
        connection = QuicConnection(
            configuration=self.server_configuration,
            original_destination_connection_id=original_destination_connection_id,
        )

        session = QuicSession(
            connection=connection,
            remote_address=remote_address,
        )

        self.sessions[connection.host_cid] = session

        return session

    def create_client_session(
            self,
            remote_host: str,
            remote_port: int,
    ) -> QuicSession:
        connection = QuicConnection(
            configuration=self.client_configuration,
            session_ticket_handler=None,
        )

        remote_address = (remote_host, remote_port)

        connection.connect(
            remote_address,
            now=self.event_loop.time(),
        )

        session = QuicSession(
            connection=connection,
            remote_address=remote_address,
        )

        self.sessions[connection.host_cid] = session
        self.flush_pending_datagrams(session)

        return session

    async def process_events(self, session: QuicSession) -> None:
        while event := session.connection.next_event():

            if isinstance(event, StreamDataReceived):
                print(event)
                await self.receiver(session, event)

    def flush_pending_datagrams(self, session: QuicSession) -> None:
        for packet_data, remote_address in session.connection.datagrams_to_send(
                now=self.event_loop.time(),
        ):
            self.udp_socket.sendto(packet_data, remote_address)
