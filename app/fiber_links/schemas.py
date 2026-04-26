"""Fiber link request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.fiber_links.models import FiberLinkQuality


class FiberLinkCreate(BaseModel):
    """Payload for creating a fiber link."""

    source_terminal_id: int
    target_terminal_id: int
    capacity_gbps: float = Field(gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_distinct_terminals(self) -> "FiberLinkCreate":
        """Ensure a link connects two different terminals."""

        if self.source_terminal_id == self.target_terminal_id:
            raise ValueError("source_terminal_id and target_terminal_id must differ")
        return self


class FiberLinkUpdate(BaseModel):
    """Payload for partially updating a fiber link."""

    source_terminal_id: int | None = None
    target_terminal_id: int | None = None
    capacity_gbps: float | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_distinct_terminals(self) -> "FiberLinkUpdate":
        """Reject updates that explicitly set identical endpoints."""

        if (
            self.source_terminal_id is not None
            and self.target_terminal_id is not None
            and self.source_terminal_id == self.target_terminal_id
        ):
            raise ValueError("source_terminal_id and target_terminal_id must differ")
        return self


class FiberLinkRead(BaseModel):
    """Fiber link representation."""

    id: int
    source_terminal_id: int
    target_terminal_id: int
    distance_km: float
    latency_ms: float
    capacity_gbps: float
    is_active: bool
    quality: FiberLinkQuality
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FiberLinkMapItem(BaseModel):
    """Map-ready fiber link representation with endpoint coordinates."""

    id: int
    source_terminal_id: int
    target_terminal_id: int
    source_name: str
    target_name: str
    source_latitude: float
    source_longitude: float
    target_latitude: float
    target_longitude: float
    distance_km: float
    latency_ms: float
    capacity_gbps: float
    is_active: bool
    quality: FiberLinkQuality
