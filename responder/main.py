import socket
import os


def run_udp(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))

    while True:
        data, addr = sock.recvfrom(1024)
        sock.sendto(data, addr)


def handle_client(conn: socket.socket) -> None:
    while True:
        data = conn.recv(65536)
        if not data:
            break


if __name__ == "__main__":
    RESPONDER_PORT = os.getenv("RESPONDER_PORT", "9999")
    PORT = int(RESPONDER_PORT)
    run_udp(PORT)
