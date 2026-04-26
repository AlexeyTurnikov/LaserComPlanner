"""Terminal SQLAlchemy model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base


class TerminalStatus(str, Enum):
    """Operational statuses for a ground terminal."""

    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class Terminal(Base):
    """Ground laser communication terminal."""

    __tablename__ = "terminals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[TerminalStatus] = mapped_column(
        SQLEnum(TerminalStatus, name="terminal_status"),
        nullable=False,
        default=TerminalStatus.online,
        server_default=TerminalStatus.online.value,
    )
    max_data_rate_gbps: Mapped[float] = mapped_column(Float, nullable=False)
    min_elevation_deg: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
