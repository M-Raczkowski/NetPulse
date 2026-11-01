from sqlalchemy.ext.asyncio import AsyncSession
from backend.anomaly.lifecycle import AlertState, update_alert
from backend.services.alert_store import find_open_alert, open_alert, close_alert
from backend.services.detection import is_anomalous
from backend.services.series import list_active_pairs, fetch_metric_series

STATES: dict[tuple[str, str, str, str], AlertState] = {}
METRICS_THRESHOLD = {"rtt_avg_ms": 100.0,
                     "packet_loss_percentage": 5.0}
DETECTORS = ("threshold", "zscore", "ewma")


async def check_combination(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        detector: str,
        values: list[float | None],
        threshold: float) -> str | None:
    open_row = await find_open_alert(db, agent_id, target, metric, detector)
    previous = STATES.get((agent_id, target, metric, detector), AlertState())
    current = AlertState(is_open=open_row is not None, anomaly_streak=previous.anomaly_streak,
                         normal_streak=previous.normal_streak)
    anomaly = is_anomalous(detector, values, threshold)
    new_state, event = update_alert(current, anomaly)
    STATES[(agent_id, target, metric, detector)] = new_state
    if event == "opened":
        open_alert(db, agent_id, target, metric, detector, values[-1])
    if event == "closed":
        close_alert(open_row)
    return event


async def run_detection(
        db: AsyncSession) -> None:
    pairs = await list_active_pairs(db)
    for agent_id, target in pairs:
        for metric, threshold in METRICS_THRESHOLD.items():
            values = await fetch_metric_series(db, agent_id, target, metric)
            for detector in DETECTORS:
                await check_combination(db, agent_id, target, metric, detector, values, threshold)
    await db.commit()
