import socket
import os

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RESPONDER_PORT = os.getenv("RESPONDER_PORT", "9999")
PORT = int(RESPONDER_PORT)
sock.bind(("0.0.0.0", PORT))

while True:
    data, addr = sock.recvfrom(1024)
    sock.sendto(data, addr)