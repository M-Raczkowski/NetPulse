from pydantic import AwareDatetime
from sqlalchemy import select, func
from backend.models.measurement import Measurement
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_aggregates(
        db: AsyncSession,
        agent_id: str | None = None,
        target: str | None = None,
        since: AwareDatetime | None = None,
        until: AwareDatetime | None = None,
):
    start = func.date_trunc("minute", Measurement.timestamp_utc).label("start")
    packets_sent = func.sum(Measurement.packets_sent).label("packets_sent")
    packets_received = func.sum(Measurement.packets_received).label("packets_received")
    packet_loss_percentage = (((packets_sent - packets_received) * 100.0) / packets_sent).label(
        "packet_loss_percentage")
    rtt_avg_ms = (func.sum(Measurement.rtt_avg_ms * Measurement.packets_received) / func.nullif(packets_received,
                                                                                                0)).label("rtt_avg_ms")
    rtt_min_ms = func.min(Measurement.rtt_min_ms).label("rtt_min_ms")
    rtt_max_ms = func.max(Measurement.rtt_max_ms).label("rtt_max_ms")
    stmt = select(start, packets_sent, packets_received, packet_loss_percentage, rtt_avg_ms, rtt_min_ms, rtt_max_ms)
    if agent_id:
        stmt = stmt.where(Measurement.agent_id == agent_id)
    if target:
        stmt = stmt.where(Measurement.target == target)
    if since:
        stmt = stmt.where(Measurement.timestamp_utc >= since)
    if until:
        stmt = stmt.where(Measurement.timestamp_utc <= until)
    stmt = stmt.group_by(start).order_by(start.desc())
    result = await db.execute(stmt)
    return result.all()
