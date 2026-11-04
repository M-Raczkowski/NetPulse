import socket
import time


def measure_rtt(host: str, port: int, count: int, interval: float, timeout: float) -> list[float | None]:
    address = (socket.gethostbyname(host), port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        results = []
        for i in range(count):
            payload = str(i).encode()
            start = time.perf_counter()
            sock.sendto(payload, address)
            try:
                data, addr = sock.recvfrom(1024)
                end = time.perf_counter()
                ms = (end - start) * 1000
                results.append(ms)
            except (socket.timeout, ConnectionResetError):
                results.append(None)
            if i < count - 1:
                time.sleep(interval)
        return results
