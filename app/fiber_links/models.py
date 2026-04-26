"""Fiber link SQLAlchemy model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class FiberLinkQuality(str, Enum):
    """Quality buckets based on distance from the 100 km target spacing."""

    optimal = "optimal"
    acceptable = "acceptable"
    redundant = "redundant"
    suboptimal = "suboptimal"


class FiberLink(Base):
    """Terrestrial fiber connection between two terminals."""

    __tablename__ = "fiber_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    capacity_gbps: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    quality: Mapped[FiberLinkQuality] = mapped_column(
        SQLEnum(FiberLinkQuality, name="fiber_link_quality"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    source_terminal = relationship(
        "Terminal",
        foreign_keys=[source_terminal_id],
    )
    target_terminal = relationship(
        "Terminal",
        foreign_keys=[target_terminal_id],
    )
