"""Communication session schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.sessions.models import SessionStatus


class SessionCreate(BaseModel):
    """Payload for creating a communication session."""

    terminal_id: int
    start_time: datetime
    end_time: datetime
    status: SessionStatus = SessionStatus.scheduled
    data_volume_gb: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SessionCreate":
        """Ensure end_time is after start_time."""

        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class SessionUpdate(BaseModel):
    """Payload for partially updating a communication session."""

    terminal_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: SessionStatus | None = None
    data_volume_gb: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SessionUpdate":
        """Reject updates that explicitly set an invalid time range."""

        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time")
        return self


class SessionRead(BaseModel):
    """Communication session representation."""

    id: int
    terminal_id: int
    start_time: datetime
    end_time: datetime
    status: SessionStatus
    data_volume_gb: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
