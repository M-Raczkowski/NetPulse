from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.alert import Alert
from datetime import datetime, timezone


async def find_open_alert(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        detector: str) -> Alert | None:
    stmt = select(Alert).where(Alert.agent_id == agent_id, Alert.target == target, Alert.metric == metric,
                               Alert.detector == detector, Alert.closed_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().first()


def open_alert(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        detector: str,
        value_at_open: float | None) -> Alert:
    alert = Alert(agent_id=agent_id, target=target, metric=metric,
                  detector=detector, value_at_open=value_at_open, opened_at=datetime.now(timezone.utc))
    db.add(alert)
    return alert
