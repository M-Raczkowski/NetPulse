from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, Integer, Float, Index
from datetime import datetime
from backend.db.session import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    detector: Mapped[str] = mapped_column(String(50), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    value_at_open: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_opened_alerts", "agent_id", "target", "metric", "detector", "closed_at"),
    )
