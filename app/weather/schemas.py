"""Weather snapshot schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WeatherSnapshotRead(BaseModel):
    """Weather snapshot representation."""

    id: int
    terminal_id: int
    timestamp: datetime
    cloud_cover_percent: float
    visibility_m: float | None
    precipitation_mm: float
    wind_speed_kmh: float
    wind_gusts_kmh: float
    temperature_c: float
    raw_payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
