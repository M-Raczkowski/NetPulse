from fastapi import APIRouter, Depends, HTTPException
from backend.schemas.measurement import MeasurementResponse,MeasurementCreate, MeasurementAggregate
from backend.models.measurement import Measurement
from backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from pydantic import AwareDatetime
router = APIRouter(prefix ="/measurements", tags = ["measurements"])

@router.post("", response_model = MeasurementResponse, status_code = 201)
async def create_measurement(
        data: MeasurementCreate,
        db: AsyncSession = Depends(get_db)
):
    values = data.model_dump()
    measurement = Measurement(**values)
    db.add(measurement)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code = 409, detail="measurement already exists")
    await db.refresh(measurement)
    return measurement

@router.get("", response_model = list[MeasurementResponse])
async def get_measurements(
        agent_id: str | None = None,
        target: str | None = None,
        limit : int = 100,
        since: AwareDatetime | None = None,
        until: AwareDatetime | None = None,
        db: AsyncSession = Depends(get_db)):
    stmt = select(Measurement)
    if agent_id:
        stmt = stmt.where(Measurement.agent_id == agent_id)
    if target:
        stmt = stmt.where(Measurement.target == target)
    if since:
        stmt = stmt.where(Measurement.timestamp_utc >= since)
    if until:
        stmt = stmt.where(Measurement.timestamp_utc <= until)
    stmt = stmt.limit(limit).order_by(Measurement.timestamp_utc.desc())
    result = await db.execute(stmt)
    measurements = result.scalars().all()
    return measurements
@router.get("/aggregates", response_model = list[MeasurementAggregate])
async def get_aggregates(
        agent_id: str | None = None,
        target: str | None = None,
        since: AwareDatetime | None = None,
        until: AwareDatetime | None = None,
        db: AsyncSession = Depends(get_db)):
    start = func.date_trunc("minute", Measurement.timestamp_utc).label("start")
    packets_sent = func.sum(Measurement.packets_sent).label("packets_sent")
    packets_received = func.sum(Measurement.packets_received).label("packets_received")
    packet_loss_percentage = (((packets_sent - packets_received)*100.0)/packets_sent).label("packet_loss_percentage")
    rtt_avg_ms = (func.sum(Measurement.rtt_avg_ms * Measurement.packets_received)/func.nullif(packets_received, 0)).label("rtt_avg_ms")
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
    aggregates = result.all()
    return aggregates
