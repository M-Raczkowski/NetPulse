import socket
import os
import threading


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


def run_tcp(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen()
    while True:
        conn, addr = sock.accept()
        with conn:
            handle_client(conn)


if __name__ == "__main__":
    RESPONDER_PORT = os.getenv("RESPONDER_PORT", "9999")
    PORT = int(RESPONDER_PORT)
    udp_thread = threading.Thread(target=run_udp, args=(PORT,), daemon=True)
    udp_thread.start()
    run_tcp(PORT)
