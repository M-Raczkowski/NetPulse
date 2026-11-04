import socket
import threading

import pytest

from agent.measurements import rtt
from agent.measurements.rtt import measure_rtt


@pytest.fixture
def echo_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.2)
    stop = threading.Event()

    def serve():
        while not stop.is_set():
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue
            sock.sendto(data, addr)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield sock.getsockname()[1]
    stop.set()
    thread.join()
    sock.close()


def test_measure_rtt_returns_one_value_per_packet(echo_port):
    result = measure_rtt("127.0.0.1", echo_port, count=5, interval=0.0, timeout=1.0)
    assert len(result) == 5
    assert all(value is not None and value > 0 for value in result)


def test_measure_rtt_resolves_host_once(echo_port, monkeypatch):
    calls = []
    original = socket.gethostbyname

    def counting(host):
        calls.append(host)
        return original(host)

    monkeypatch.setattr(rtt.socket, "gethostbyname", counting)
    measure_rtt("localhost", echo_port, count=5, interval=0.0, timeout=1.0)
    assert calls == ["localhost"]


def test_measure_rtt_no_answer_gives_none():
    silent = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    silent.bind(("127.0.0.1", 0))
    try:
        result = measure_rtt("127.0.0.1", silent.getsockname()[1], count=3, interval=0.0, timeout=0.05)
    finally:
        silent.close()
    assert result == [None, None, None]
