import asyncio
from socket import socket


from host.host_listener import start_host
from peer import start_peer


def input_for_y_or_n(prompt: str):
    while True:
        data = input(f"{prompt} (Y/n): ")
        if data.lower() == "y":
            return True
        elif data.lower() == "n":
            return False

async def main():
    default_server_ip = "130.61.248.57"
    if not (server_ip := input(f"What is the server [Default is {default_server_ip}]?")):
        server_ip = default_server_ip

    is_host = input_for_y_or_n("Are you host?")
    is_tcp = input_for_y_or_n("Are you using TCP?")
    if is_host:
        port_raw = input("Enter the local port:")
        if port_raw.isdigit():
            print("Starting...")
            await start_host(server_ip, int(port_raw), is_tcp)


    else:
        ip = input("Enter host's (remote) ip:")
        port_raw = input("Enter host's (remote) port:")

        if port_raw.isdigit():
            print("Starting...")
            await start_peer(ip, int(port_raw), is_tcp, server_ip)

    print("error. invalid inpput")

if __name__ == '__main__':
    asyncio.run(main())