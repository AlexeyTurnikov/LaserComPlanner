"""Availability API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.availability.models import AvailabilityCheck
from app.availability.schemas import AvailabilityCheckRead, AvailabilityMapItem
from app.availability.service import (
    check_all_terminals,
    check_terminal_availability,
    get_availability_map,
    get_latest_availability,
)
from app.database import get_db
from app.dependencies import require_operator_or_higher
from app.users.models import User
from app.weather.client import OpenMeteoClient
from app.weather.router import get_weather_client

router = APIRouter(prefix="/availability", tags=["availability"])
map_router = APIRouter(tags=["availability"])


@router.post("/check/{terminal_id}", response_model=AvailabilityCheckRead)
def check_terminal_availability_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    weather_client: OpenMeteoClient = Depends(get_weather_client),
    current_user: User = Depends(require_operator_or_higher),
) -> AvailabilityCheck:
    """Calculate availability for one terminal."""

    return check_terminal_availability(
        db,
        terminal_id,
        current_user.id,
        weather_client,
    )


@router.post("/check-all", response_model=list[AvailabilityCheckRead])
def check_all_terminals_endpoint(
    db: Session = Depends(get_db),
    weather_client: OpenMeteoClient = Depends(get_weather_client),
    current_user: User = Depends(require_operator_or_higher),
) -> list[AvailabilityCheck]:
    """Calculate availability for all terminals."""

    return check_all_terminals(db, current_user.id, weather_client)


@router.get("/{terminal_id}/latest", response_model=AvailabilityCheckRead)
def read_latest_availability_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> AvailabilityCheck:
    """Return latest availability check for a terminal."""

    return get_latest_availability(db, terminal_id)


@map_router.get("/availability-map", response_model=list[AvailabilityMapItem])
def read_availability_map_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> list[AvailabilityMapItem]:
    """Return terminal coordinates with latest availability and weather data."""

    return get_availability_map(db)
