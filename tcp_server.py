import asyncio

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"Connection from {addr}")

    try:
        while data := await reader.read(1024):
            print(f"Received: {data.decode()} from {addr}")
            writer.write(data)  # Echo the received data back to the client
            await writer.drain()
    except asyncio.IncompleteReadError:
        print(f"Connection closed by {addr}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Connection with {addr} closed")

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())