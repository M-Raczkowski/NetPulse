import socket
import time

def measure_rtt(host: str, port: int, count: int, interval: float, timeout: float) -> list[float | None]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    results=[]
    for i in range(count):
        payload = str(i).encode()
        start = time.perf_counter()
        sock.sendto(payload,(host, port))
        try:
            data, addr = sock.recvfrom(1024)
            end = time.perf_counter()
            ms = (end-start)*1000
            results.append(ms)
        except (socket.timeout, ConnectionResetError):
            results.append(None)
    return results