from agent.config import AGENT_ID, BACKEND_URL, PACKETS_PER_WINDOW, PACKET_TIMEOUT, CYCLE_SECONDS
from agent.measurements.rtt import measure_rtt
from agent.measurements.window import build_measurement
from agent.transport.client import send_measurement
from datetime import datetime, timezone
def run_cycle(host: str, port: int) -> str:
    timezone_utc = datetime.now(timezone.utc)
    rtts = measure_rtt(host, port, count = PACKETS_PER_WINDOW, interval = 0.1, timeout = PACKET_TIMEOUT)
    payload = build_measurement(agent_id = AGENT_ID, target = f"{host}:{port}", rtts = rtts, window_seconds =CYCLE_SECONDS, timestamp_utc = timezone_utc)
    return send_measurement(BACKEND_URL, payload)