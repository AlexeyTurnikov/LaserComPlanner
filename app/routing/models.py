"""Routing result SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class RoutingResult(Base):
    """Saved transmission routing decision."""

    __tablename__ = "routing_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("transmission_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_terminal_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    route_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_transfer_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision_reason: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    request = relationship("TransmissionRequest")
    selected_terminal = relationship("Terminal")
