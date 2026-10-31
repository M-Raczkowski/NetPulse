from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from backend.services.aggregates import fetch_aggregates


async def fetch_metric_series(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        minutes: int = 60) -> list[float | None]:
    rows = await fetch_aggregates(db, agent_id, target, since=datetime.now(timezone.utc) - timedelta(minutes=minutes))
    return [getattr(row, metric) for row in reversed(rows)]
