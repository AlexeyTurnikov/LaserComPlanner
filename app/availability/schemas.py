"""Availability schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.availability.models import AvailabilityStatus
from app.terminals.models import TerminalStatus


class AvailabilityCheckRead(BaseModel):
    """Availability check representation."""

    id: int
    terminal_id: int
    weather_snapshot_id: int
    checked_at: datetime
    availability_score: float
    status: AvailabilityStatus
    reason: list[str]
    created_by_user_id: int | None

    model_config = ConfigDict(from_attributes=True)


class AvailabilityMapItem(BaseModel):
    """Map-ready terminal availability representation."""

    terminal_id: int
    name: str
    latitude: float
    longitude: float
    terminal_status: TerminalStatus
    availability_status: AvailabilityStatus | None
    availability_score: float | None
    checked_at: datetime | None
    weather_snapshot_id: int | None
    cloud_cover_percent: float | None
    visibility_m: float | None
    precipitation_mm: float | None
    wind_speed_kmh: float | None
