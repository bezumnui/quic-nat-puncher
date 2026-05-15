import asyncio
from asyncio import Queue

from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio import connect


async def main():
    host = "127.0.0.1"
    port = 12715
    async with connect(host=host, port=port, configuration=QuicConfiguration(
        is_client=True,
        verify_mode=False,
        alpn_protocols=["quic_punching"],
    )) as client:
        quic_reader, quic_writer = await client.create_stream()
        quic_writer.write(b"Hello, world!")
        await quic_writer.drain()
        while True:
            data = await quic_reader.read()
            if data:
                print(data)

    # await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())

