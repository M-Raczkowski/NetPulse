import statistics
from backend.anomaly.direction import direction_sign


def z_score(history: list[float | None], latest: float | None, k: float = 3.0, min_history: int = 10,
            min_deviation: float = 0.0, direction: str = "high") -> bool:
    sign = direction_sign(direction)
    if latest is None:
        return False
    history = [x for x in history if x is not None]
    if len(history) < min_history:
        return False
    avg_history = statistics.mean(history)
    deviation = max(statistics.stdev(history), min_deviation)
    if deviation == 0:
        return False
    z_calc = sign * (latest - avg_history) / deviation
    return z_calc > k
