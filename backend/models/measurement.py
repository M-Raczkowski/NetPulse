from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, Integer, Float, UniqueConstraint, Index
from datetime import datetime
from backend.db.session import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key = True, autoincrement = True)

    agent_id: Mapped[str] = mapped_column(String(100), nullable = False)
    target: Mapped[str] = mapped_column(String(500), nullable = False)

    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone = True), nullable = False)

    window_seconds: Mapped[int] = mapped_column(Integer, nullable = False)

    packets_sent: Mapped[int] = mapped_column(Integer, nullable = False)
    packets_received: Mapped[int] = mapped_column(Integer, nullable=False)

    rtt_avg_ms: Mapped[float | None] = mapped_column(Float, nullable = True)
    rtt_min_ms: Mapped[float | None] = mapped_column(Float, nullable = True)
    rtt_max_ms: Mapped[float | None] = mapped_column(Float, nullable = True)

    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable = True)
    throughput_mbps: Mapped[float | None] = mapped_column(Float, nullable = True)

    __table_args__ = (
        UniqueConstraint("agent_id", "target", "timestamp_utc",
                         name ="uq_measurements_agent_target_ts"),
    )