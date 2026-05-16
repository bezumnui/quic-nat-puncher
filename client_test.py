import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
while True:
    sock.sendto(b"hello", ('127.0.0.1', 12666))
    data, addr = sock.recvfrom(1024)
    print(data)
