from agent.measurements.window import build_measurement
from datetime import datetime, timezone

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def make_window(rtts: list[float | None], throughput_mbps: float | None = None) -> dict:
    return build_measurement(agent_id="agent-test", target="127.0.0.1:9999", rtts=rtts, window_seconds=10,
                             throughput_mbps=throughput_mbps, timestamp_utc=NOW)


def test_build_measurement_all_received():
    result = make_window([10.0, 20.0, 30])
    assert result["packets_sent"] == 3
    assert result["packets_received"] == 3
    assert result["rtt_avg_ms"] == 20.0
    assert result["rtt_min_ms"] == 10.0
    assert result["rtt_max_ms"] == 30.0


def test_build_measurement_lost_packets():
    result = make_window([10.0, None, 30])
    assert result["packets_sent"] == 3
    assert result["packets_received"] == 2
    assert result["rtt_avg_ms"] == 20.0
    assert result["rtt_min_ms"] == 10.0
    assert result["rtt_max_ms"] == 30.0


def test_build_measurement_none_received():
    result = make_window([None, None])
    assert result["packets_sent"] == 2
    assert result["packets_received"] == 0
    assert result["rtt_avg_ms"] is None
    assert result["rtt_min_ms"] is None
    assert result["rtt_max_ms"] is None
    assert result["jitter_ms"] is None


def test_build_measurement_passes_through_fields():
    result = make_window([10.0], throughput_mbps=94.3)
    assert result["throughput_mbps"] == 94.3
    assert result["agent_id"] == "agent-test"
    assert result["target"] == "127.0.0.1:9999"
    assert result["window_seconds"] == 10.0
    assert result["timestamp_utc"] == NOW.isoformat()
