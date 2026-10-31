from fastapi import APIRouter, Depends, HTTPException
from backend.schemas.measurement import MeasurementResponse, MeasurementCreate, MeasurementAggregate
from backend.models.measurement import Measurement
from backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from pydantic import AwareDatetime
from backend.services.aggregates import fetch_aggregates

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.post("", response_model=MeasurementResponse, status_code=201)
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
        raise HTTPException(status_code=409, detail="measurement already exists")
    await db.refresh(measurement)
    return measurement


@router.get("", response_model=list[MeasurementResponse])
async def get_measurements(
        agent_id: str | None = None,
        target: str | None = None,
        limit: int = 100,
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


@router.get("/aggregates", response_model=list[MeasurementAggregate])
async def get_aggregates(
        db: AsyncSession = Depends(get_db),
        agent_id: str | None = None,
        target: str | None = None,
        since: AwareDatetime | None = None,
        until: AwareDatetime | None = None, ):
    return await fetch_aggregates(db, agent_id, target, since, until)
