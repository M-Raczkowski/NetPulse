import socket
import threading

import pytest

from agent.measurements.throughput import measure_throughput


@pytest.fixture
def sink_port():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen()

    def serve():
        conn, addr = server.accept()
        with conn:
            while conn.recv(65536):
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield server.getsockname()[1]
    thread.join(timeout=5)
    server.close()


def test_measure_throughput_returns_positive_value(sink_port):
    result = measure_throughput("127.0.0.1", sink_port, duration=0.2, timeout=5.0)
    assert result is not None
    assert result > 0


def test_measure_throughput_nobody_listening_gives_none():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    assert measure_throughput("127.0.0.1", port, duration=0.2, timeout=1.0) is None
