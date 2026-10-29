from agent.config import AGENT_ID, BACKEND_URL, PACKETS_PER_WINDOW, PACKET_TIMEOUT, CYCLE_SECONDS, TARGETS
from agent.measurements.rtt import measure_rtt
from agent.measurements.window import build_measurement
from agent.transport.client import send_measurement
from datetime import datetime, timezone
import time

def run_cycle(host: str, port: int) -> str:
    timezone_utc = datetime.now(timezone.utc)
    rtts = measure_rtt(host, port, count = PACKETS_PER_WINDOW, interval = 0.1, timeout = PACKET_TIMEOUT)
    payload = build_measurement(agent_id = AGENT_ID, target = f"{host}:{port}", rtts = rtts, window_seconds =CYCLE_SECONDS, timestamp_utc = timezone_utc)
    return send_measurement(BACKEND_URL, payload)

def run_round() -> dict[str, str]:
    results = {}
    for host, port in TARGETS:
        try:
            status = run_cycle(host,port)
        except Exception as exc:
            status = f"error: {exc}"
        results[f"{host}:{port}"] = status
    return results

def main() -> None:
    try:
        while True:
            start = time.monotonic()
            measurements = run_round()
            end = time.monotonic()
            measurement_time = end - start
            wait_time = max(0,CYCLE_SECONDS - measurement_time)
            print(measurements)
            time.sleep(wait_time)
    except KeyboardInterrupt:
        print(f"{AGENT_ID} has stopped")


if __name__ == "__main__":
    main()