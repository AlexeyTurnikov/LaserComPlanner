"""Communication session SQLAlchemy model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class SessionStatus(str, Enum):
    """Scheduled communication session statuses."""

    scheduled = "scheduled"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class CommunicationSession(Base):
    """Planned or historical satellite communication session."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.scheduled,
        server_default=SessionStatus.scheduled.value,
    )
    data_volume_gb: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    terminal = relationship("Terminal")
