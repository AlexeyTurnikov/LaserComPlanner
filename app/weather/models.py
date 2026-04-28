"""Weather snapshot SQLAlchemy model."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class WeatherSnapshot(Base):
    """Weather data captured for a terminal at a point in time."""

    __tablename__ = "weather_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cloud_cover_percent: Mapped[float] = mapped_column(Float, nullable=False)
    visibility_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    wind_gusts_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    terminal = relationship("Terminal")
