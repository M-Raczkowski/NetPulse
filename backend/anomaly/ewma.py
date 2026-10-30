import math
import statistics

def ewma(history: list[float | None], recent: list[float | None], alpha: float = 0.3, L: float = 3.0, min_history: int = 10) -> bool:
    history = [x for x in history if x is not None]
    recent = [x for x in recent if x is not None]
    if len(history) < min_history or len(recent) == 0:
        return False
    avg_history = statistics.mean(history)
    deviation = statistics.stdev(history)
    if deviation == 0:
        return False
    ewma_value = avg_history
    for x in recent:
        ewma_value = alpha * x + (1.0 - alpha) * ewma_value
    upper_limit = avg_history + L * deviation * math.sqrt(alpha / (2 - alpha))
    return ewma_value > upper_limit
