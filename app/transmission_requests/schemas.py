"""Transmission request schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.transmission_requests.models import (
    TransmissionPriority,
    TransmissionRequestStatus,
)


class TransmissionRequestCreate(BaseModel):
    """Payload for creating a transmission request."""

    source_terminal_id: int
    data_volume_gb: float = Field(gt=0, le=10000)
    priority: TransmissionPriority = TransmissionPriority.normal
    min_availability_score: float = Field(ge=0, le=1)


class TransmissionRequestRead(BaseModel):
    """Transmission request representation."""

    id: int
    created_by_user_id: int | None
    source_terminal_id: int
    data_volume_gb: float
    priority: TransmissionPriority
    min_availability_score: float
    status: TransmissionRequestStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransmissionRequestUpdateStatus(BaseModel):
    """Payload for changing transmission request status."""

    status: TransmissionRequestStatus
