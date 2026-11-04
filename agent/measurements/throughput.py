import socket
import time


def measure_throughput(host: str, port: int, duration: float, timeout: float) -> float | None:
    try:
        with socket.create_connection((host, port), timeout) as sock:
            packet = bytes(65536)
            start = time.perf_counter()
            sent = 0
            while time.perf_counter() - start < duration:
                sock.sendall(packet)
                sent += len(packet)
            sock.shutdown(socket.SHUT_WR)
            sock.recv(1)
            end = time.perf_counter()
            throughput_mbps = sent * 8 / (end - start) / 1000000
            return throughput_mbps
    except OSError:
        return None
