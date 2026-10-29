from fastapi import APIRouter, Depends, HTTPException
from backend.schemas.measurement import MeasurementResponse,MeasurementCreate
from backend.models.measurement import Measurement
from backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

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
        db: AsyncSession = Depends(get_db)):
    stmt = select(Measurement)
    if agent_id:
        stmt = stmt.where(Measurement.agent_id == agent_id)
    if target:
        stmt = stmt.where(Measurement.target == target)
    stmt = stmt.limit(limit).order_by(Measurement.timestamp_utc.desc())
    result = await db.execute(stmt)
    measurements = result.scalars().all()
    return measurements