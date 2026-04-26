"""Terminal request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.terminals.models import TerminalStatus


class TerminalBase(BaseModel):
    """Shared terminal fields."""

    name: str = Field(min_length=3, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float = Field(ge=-500, le=9000)
    status: TerminalStatus = TerminalStatus.online
    max_data_rate_gbps: float = Field(gt=0)
    min_elevation_deg: float = Field(ge=0, le=90)


class TerminalCreate(TerminalBase):
    """Payload for terminal creation."""


class TerminalUpdate(BaseModel):
    """Payload for partial terminal updates."""

    name: str | None = Field(default=None, min_length=3, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    altitude_m: float | None = Field(default=None, ge=-500, le=9000)
    status: TerminalStatus | None = None
    max_data_rate_gbps: float | None = Field(default=None, gt=0)
    min_elevation_deg: float | None = Field(default=None, ge=0, le=90)


class TerminalListItem(BaseModel):
    """Compact terminal representation for lists."""

    id: int
    name: str
    latitude: float
    longitude: float
    status: TerminalStatus
    max_data_rate_gbps: float

    model_config = ConfigDict(from_attributes=True)


class TerminalRead(TerminalListItem):
    """Full terminal representation."""

    altitude_m: float
    min_elevation_deg: float
    created_at: datetime
    updated_at: datetime
