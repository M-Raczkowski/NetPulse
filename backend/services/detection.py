from backend.anomaly.ewma import ewma
from backend.anomaly.threshold import threshold_check
from backend.anomaly.zscore import z_score


def is_anomalous(detector: str, values: list[float | None], threshold: float) -> bool:
    if not values:
        return False
    latest = values[-1]
    if detector == "ewma":
        recent = values[-3:]
        history = values[:-3]
        return ewma(history, recent)
    if detector == "zscore":
        history = values[:-1]
        return z_score(history, latest)
    if detector == "threshold":
        return threshold_check(latest, threshold)
    raise ValueError("detector not found")
