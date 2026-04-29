"""Routing request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.transmission_requests.models import TransmissionPriority


class FindNearestAvailableRequest(BaseModel):
    """Payload for nearest-available-terminal lookup."""

    source_terminal_id: int
    min_availability_score: float = Field(default=0.75, ge=0, le=1)


class FindNearestAvailableResponse(BaseModel):
    """Nearest available terminal response."""

    source_terminal_id: int
    recommended_terminal_id: int
    direct_satellite_access: bool
    route: list[int]
    route_distance_km: float
    estimated_latency_ms: float
    availability_score: float
    decision_reason: list[str]


class FindRouteRequest(BaseModel):
    """Payload for route lookup between two terminals."""

    source_terminal_id: int
    target_terminal_id: int


class FindRouteResponse(BaseModel):
    """Fiber route response."""

    source_terminal_id: int
    target_terminal_id: int
    route: list[int]
    total_cost: float
    route_distance_km: float
    estimated_latency_ms: float
    min_capacity_gbps: float


class TransmissionPlanRequest(BaseModel):
    """Payload for full transmission planning."""

    source_terminal_id: int
    data_volume_gb: float = Field(gt=0, le=10000)
    priority: TransmissionPriority = TransmissionPriority.normal
    min_availability_score: float = Field(default=0.75, ge=0, le=1)


class TransmissionPlanResponse(BaseModel):
    """Transmission planning result response."""

    request_id: int
    routing_result_id: int
    source_terminal_id: int
    direct_satellite_access: bool
    recommended_terminal_id: int
    route: list[int]
    route_distance_km: float
    estimated_latency_ms: float
    estimated_transfer_time_sec: float
    availability_score: float
    final_score: float
    decision_reason: list[str]


class RoutingResultRead(BaseModel):
    """Saved routing result representation."""

    id: int
    request_id: int
    selected_terminal_id: int
    route_terminal_ids: list[int]
    route_distance_km: float
    estimated_latency_ms: float
    estimated_transfer_time_sec: float
    final_score: float
    decision_reason: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
