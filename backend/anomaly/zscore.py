import statistics

def z_score(history: list[float | None], latest: float | None, k: float = 3.0, min_history: int = 10,
            min_deviation: float = 0.0) -> bool:
    if latest is None:
        return False
    history = [x for x in history if x is not None]
    if len(history) < min_history:
        return False
    avg_history = statistics.mean(history)
    deviation = max(statistics.stdev(history), min_deviation)
    if deviation == 0:
        return False
    z_calc = (latest - avg_history) / deviation
    return z_calc > k
