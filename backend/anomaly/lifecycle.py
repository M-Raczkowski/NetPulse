from dataclasses import dataclass

@dataclass
class AlertState:
    is_open: bool = False
    anomaly_streak: int = 0
    normal_streak: int = 0

def update_alert(state: AlertState, is_anomaly: bool, open_after: int = 2, close_after: int = 3) -> tuple[AlertState, str | None]:
    anomaly_count = state.anomaly_streak
    normal_count = state.normal_streak
    if is_anomaly:
        anomaly_count += 1
        normal_count = 0
    else:
        anomaly_count = 0
        normal_count += 1
    is_open = state.is_open
    event = None
    if not is_open and anomaly_count >= open_after:
        is_open = True
        event = "opened"
    if is_open and normal_count >= close_after:
        is_open = False
        event = "closed"
    return AlertState(is_open, anomaly_count, normal_count), event