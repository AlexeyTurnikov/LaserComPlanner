"""Weather snapshot persistence use cases."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.terminals.models import Terminal
from app.terminals.service import get_terminal_or_404
from app.weather.client import OpenMeteoClient, OpenMeteoClientError
from app.weather.models import WeatherSnapshot


def _save_weather_snapshot(
    db: Session,
    terminal_id: int,
    weather_data: dict[str, Any],
) -> WeatherSnapshot:
    """Persist normalized weather data."""

    snapshot = WeatherSnapshot(
        terminal_id=terminal_id,
        timestamp=weather_data["timestamp"],
        cloud_cover_percent=weather_data["cloud_cover_percent"],
        visibility_m=weather_data["visibility_m"],
        precipitation_mm=weather_data["precipitation_mm"],
        wind_speed_kmh=weather_data["wind_speed_kmh"],
        wind_gusts_kmh=weather_data["wind_gusts_kmh"],
        temperature_c=weather_data["temperature_c"],
        raw_payload=weather_data["raw_payload"],
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def update_terminal_weather(
    db: Session,
    terminal_id: int,
    weather_client: OpenMeteoClient,
) -> WeatherSnapshot:
    """Fetch and save a weather snapshot for one terminal."""

    terminal = get_terminal_or_404(db, terminal_id)
    try:
        weather_data = weather_client.get_current_weather(
            terminal.latitude,
            terminal.longitude,
        )
    except OpenMeteoClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return _save_weather_snapshot(db, terminal_id, weather_data)


def update_all_weather(
    db: Session,
    weather_client: OpenMeteoClient,
) -> list[WeatherSnapshot]:
    """Fetch and save weather snapshots for all terminals."""

    terminals = db.scalars(select(Terminal).order_by(Terminal.id)).all()
    snapshots = []
    for terminal in terminals:
        snapshots.append(update_terminal_weather(db, terminal.id, weather_client))
    return snapshots


def get_latest_weather(db: Session, terminal_id: int) -> WeatherSnapshot:
    """Return latest weather snapshot for a terminal or raise 404."""

    get_terminal_or_404(db, terminal_id)
    snapshot = db.scalar(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.terminal_id == terminal_id)
        .order_by(WeatherSnapshot.timestamp.desc(), WeatherSnapshot.id.desc()),
    )
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weather snapshot not found",
        )
    return snapshot


def list_weather_history(
    db: Session,
    terminal_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[WeatherSnapshot]:
    """Return weather snapshots for a terminal ordered newest first."""

    get_terminal_or_404(db, terminal_id)
    query = (
        select(WeatherSnapshot)
        .where(WeatherSnapshot.terminal_id == terminal_id)
        .order_by(WeatherSnapshot.timestamp.desc(), WeatherSnapshot.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())
