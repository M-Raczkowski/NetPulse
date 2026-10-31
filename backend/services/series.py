from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from backend.services.aggregates import fetch_aggregates
from sqlalchemy import select
from backend.models.measurement import Measurement

async def fetch_metric_series(
        db: AsyncSession,
        agent_id: str,
        target: str,
        metric: str,
        minutes: int = 60) -> list[float | None]:
    rows = await fetch_aggregates(db, agent_id, target, since=datetime.now(timezone.utc) - timedelta(minutes=minutes))
    return [getattr(row, metric) for row in reversed(rows)]

async def list_active_pairs(
        db:AsyncSession,
        minutes: int = 60) -> list[tuple[str, str]]:
    stmt = select(Measurement.agent_id, Measurement.target).where(Measurement.timestamp_utc>=datetime.now(timezone.utc) - timedelta(minutes=minutes)).distinct()
    result = await db.execute(stmt)
    return [tuple(row) for row in result]
