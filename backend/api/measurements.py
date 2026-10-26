from fastapi import APIRouter, Depends, HTTPException
from backend.schemas.measurement import MeasurementResponse,MeasurementCreate
from backend.models.measurement import Measurement
from backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

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