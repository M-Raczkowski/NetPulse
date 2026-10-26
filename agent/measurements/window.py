from datetime import datetime
from agent.measurements.jitter import calculate_jitter

def build_measurement(agent_id: str, target: str, rtts: list[float | None], window_seconds: int, timestamp_utc: datetime) -> dict:
    v = [value for value in rtts if value is not None]
    packets_sent = len(rtts)
    packets_received = len(v)
    if v:
        rtt_avg_ms = sum(v) / len(v)
        rtt_min_ms = min(v)
        rtt_max_ms = max(v)
    else:
        rtt_avg_ms = None
        rtt_min_ms = None
        rtt_max_ms = None
    jitter_ms = calculate_jitter(rtts)
    throughput_mbps = None
    return {
        "agent_id": agent_id,
        "target": target,
        "window_seconds": window_seconds,
        "timestamp_utc": timestamp_utc.isoformat(),
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "rtt_avg_ms": rtt_avg_ms,
        "rtt_min_ms": rtt_min_ms,
        "rtt_max_ms": rtt_max_ms,
        "jitter_ms": jitter_ms,
        "throughput_mbps": throughput_mbps
    }