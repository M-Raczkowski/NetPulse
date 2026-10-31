from fastapi import APIRouter, Depends
from backend.schemas.alert import AlertResponse
from backend.models.alert import Alert
from backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def get_alerts(
        agent_id: str | None = None,
        target: str | None = None,
        is_open: bool | None = None,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)):
    stmt = select(Alert)
    if agent_id:
        stmt = stmt.where(Alert.agent_id == agent_id)
    if target:
        stmt = stmt.where(Alert.target == target)
    if is_open is not None:
        if is_open:
            stmt = stmt.where(Alert.closed_at.is_(None))
        if not is_open:
            stmt = stmt.where(Alert.closed_at.is_not(None))
    stmt = stmt.limit(limit).order_by(Alert.opened_at.desc())
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return alerts
