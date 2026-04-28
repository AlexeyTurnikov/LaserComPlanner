"""Weather API router."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_engineer_or_admin, require_operator_or_higher
from app.users.models import User
from app.weather.client import OpenMeteoClient
from app.weather.models import WeatherSnapshot
from app.weather.schemas import WeatherSnapshotRead
from app.weather.service import (
    get_latest_weather,
    list_weather_history,
    update_all_weather,
    update_terminal_weather,
)

router = APIRouter(prefix="/weather", tags=["weather"])


def get_weather_client() -> OpenMeteoClient:
    """Provide Open-Meteo client through dependency injection."""

    return OpenMeteoClient()


@router.post("/update/{terminal_id}", response_model=WeatherSnapshotRead)
def update_terminal_weather_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    weather_client: OpenMeteoClient = Depends(get_weather_client),
    _: User = Depends(require_engineer_or_admin),
) -> WeatherSnapshot:
    """Fetch and save latest weather for one terminal."""

    return update_terminal_weather(db, terminal_id, weather_client)


@router.post("/update-all", response_model=list[WeatherSnapshotRead])
def update_all_weather_endpoint(
    db: Session = Depends(get_db),
    weather_client: OpenMeteoClient = Depends(get_weather_client),
    _: User = Depends(require_engineer_or_admin),
) -> list[WeatherSnapshot]:
    """Fetch and save latest weather for all terminals."""

    return update_all_weather(db, weather_client)


@router.get("/{terminal_id}/latest", response_model=WeatherSnapshotRead)
def read_latest_weather_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> WeatherSnapshot:
    """Return latest weather snapshot for a terminal."""

    return get_latest_weather(db, terminal_id)


@router.get("/{terminal_id}/history", response_model=list[WeatherSnapshotRead])
def read_weather_history_endpoint(
    terminal_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> list[WeatherSnapshot]:
    """Return weather snapshot history for a terminal."""

    return list_weather_history(db, terminal_id, limit=limit, offset=offset)
