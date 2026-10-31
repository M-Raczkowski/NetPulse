from sqlalchemy.ext.asyncio import AsyncSession
from backend.anomaly.lifecycle import AlertState, update_alert
from backend.services.alert_store import find_open_alert, open_alert, close_alert
from backend.services.detection import is_anomalous

STATES: dict[tuple[str, str, str, str], AlertState] = {}


async def check_combination(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        detector: str,
        values: list[float | None],
        threshold: float) -> str | None:
    open_row = await find_open_alert(db, agent_id, target, metric, detector)
    key = (agent_id, target, metric, detector)
    previous = STATES.get((agent_id, target, metric, detector), AlertState())
    current = AlertState(is_open=open_row is not None, anomaly_streak=previous.anomaly_streak,
                         normal_streak=previous.normal_streak)
    anomaly = is_anomalous(detector, values, threshold)
    new_state, event = update_alert(current, anomaly)
    STATES[key] = new_state
    if event == "opened":
        open_alert(db, agent_id, target, metric, detector, values[-1])
    if event == "closed":
        close_alert(open_row)
    return event
