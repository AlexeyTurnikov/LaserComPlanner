"""Routing API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_operator_or_higher
from app.routing.models import RoutingResult
from app.routing.schemas import (
    FindNearestAvailableRequest,
    FindNearestAvailableResponse,
    FindRouteRequest,
    FindRouteResponse,
    RoutingResultRead,
    TransmissionPlanRequest,
    TransmissionPlanResponse,
)
from app.routing.service import (
    find_nearest_available_terminal,
    find_route_between_terminals,
    get_routing_result_for_request,
    create_transmission_plan,
)
from app.users.models import User

router = APIRouter(prefix="/routing", tags=["routing"])


@router.post("/find-nearest-available", response_model=FindNearestAvailableResponse)
def find_nearest_available_endpoint(
    payload: FindNearestAvailableRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> FindNearestAvailableResponse:
    """Find the nearest available terminal reachable from the source."""

    return find_nearest_available_terminal(db, payload)


@router.post("/find-route", response_model=FindRouteResponse)
def find_route_endpoint(
    payload: FindRouteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> FindRouteResponse:
    """Find a fiber route between two terminals."""

    return find_route_between_terminals(db, payload)


@router.post("/transmission-plan", response_model=TransmissionPlanResponse)
def transmission_plan_endpoint(
    payload: TransmissionPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> TransmissionPlanResponse:
    """Create a transmission request and select the best terminal route."""

    return create_transmission_plan(db, payload, current_user.id)


@router.get("/results/{request_id}", response_model=RoutingResultRead)
def read_routing_result_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> RoutingResult:
    """Return latest routing result for a visible transmission request."""

    return get_routing_result_for_request(db, request_id, current_user)
