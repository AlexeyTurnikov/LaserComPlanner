"""Availability check SQLAlchemy model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, JSON, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class AvailabilityStatus(str, Enum):
    """Calculated terminal availability status."""

    available = "available"
    limited = "limited"
    unavailable = "unavailable"


class AvailabilityCheck(Base):
    """Calculated terminal availability for one weather snapshot."""

    __tablename__ = "availability_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weather_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("weather_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    availability_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(AvailabilityStatus, name="availability_status"),
        nullable=False,
    )
    reason: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    terminal = relationship("Terminal")
    weather_snapshot = relationship("WeatherSnapshot")
    created_by_user = relationship("User")
