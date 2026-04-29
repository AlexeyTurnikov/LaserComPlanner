"""Transmission request SQLAlchemy model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class TransmissionPriority(str, Enum):
    """Supported transmission priorities."""

    low = "low"
    normal = "normal"
    high = "high"


class TransmissionRequestStatus(str, Enum):
    """Transmission request lifecycle statuses."""

    created = "created"
    planned = "planned"
    failed = "failed"
    completed = "completed"


class TransmissionRequest(Base):
    """Request to transfer data through a source terminal."""

    __tablename__ = "transmission_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_volume_gb: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[TransmissionPriority] = mapped_column(
        SQLEnum(TransmissionPriority, name="transmission_priority"),
        nullable=False,
        default=TransmissionPriority.normal,
        server_default=TransmissionPriority.normal.value,
    )
    min_availability_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[TransmissionRequestStatus] = mapped_column(
        SQLEnum(
            TransmissionRequestStatus,
            name="transmission_request_status",
        ),
        nullable=False,
        default=TransmissionRequestStatus.created,
        server_default=TransmissionRequestStatus.created.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    created_by_user = relationship("User")
    source_terminal = relationship("Terminal")
