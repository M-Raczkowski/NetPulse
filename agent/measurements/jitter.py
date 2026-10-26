def calculate_jitter(rtt: list[float | None]) -> float | None:
    valid = [value for value in rtt if value is not None]
    rtt_diff = [abs(b - a) for a, b in zip(valid, valid[1:])]
    if not rtt_diff:
        return None
    return sum(rtt_diff) / len(rtt_diff)