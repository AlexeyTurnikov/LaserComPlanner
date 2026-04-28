"""Availability scoring and persistence use cases."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.availability.models import AvailabilityCheck, AvailabilityStatus
from app.availability.schemas import AvailabilityMapItem
from app.terminals.models import Terminal, TerminalStatus
from app.terminals.service import get_terminal_or_404
from app.weather.client import OpenMeteoClient
from app.weather.models import WeatherSnapshot
from app.weather.service import update_terminal_weather


def _score_visibility(visibility_m: float | None) -> tuple[float, str]:
    """Return normalized visibility score and explanation."""

    if visibility_m is None:
        return 0.5, "Visibility data is missing, neutral score applied"
    if visibility_m >= 20000:
        return 1.0, "Visibility is sufficient"
    if visibility_m >= 10000:
        return 0.7, "Visibility is acceptable"
    if visibility_m >= 5000:
        return 0.4, "Visibility is limited"
    return 0.0, "Visibility is too low"


def _score_cloud_cover(cloud_cover_percent: float) -> tuple[float, str]:
    """Return normalized cloud cover score and explanation."""

    if cloud_cover_percent <= 20:
        return 1.0, "Cloud cover is low"
    if cloud_cover_percent <= 40:
        return 0.75, "Cloud cover is acceptable"
    if cloud_cover_percent <= 70:
        return 0.35, "Cloud cover is high"
    return 0.0, "Cloud cover is too high"


def _score_precipitation(precipitation_mm: float) -> tuple[float, str]:
    """Return normalized precipitation score and explanation."""

    if precipitation_mm == 0:
        return 1.0, "No precipitation detected"
    if precipitation_mm <= 0.5:
        return 0.6, "Light precipitation detected"
    return 0.0, "Precipitation is too high"


def _score_wind(wind_speed_kmh: float) -> tuple[float, str]:
    """Return normalized wind score and explanation."""

    if wind_speed_kmh <= 25:
        return 1.0, "Wind speed is acceptable"
    if wind_speed_kmh <= 45:
        return 0.5, "Wind speed is high"
    return 0.0, "Wind speed is too high"


def _score_hardware(terminal_status: TerminalStatus) -> tuple[float, str]:
    """Return normalized hardware status score and explanation."""

    if terminal_status == TerminalStatus.online:
        return 1.0, "Terminal hardware status is online"
    if terminal_status == TerminalStatus.maintenance:
        return 0.3, "Terminal hardware status is maintenance"
    return 0.0, "Terminal hardware status is offline"


def _status_from_score(score: float) -> AvailabilityStatus:
    """Return availability status for a score."""

    if score >= 0.75:
        return AvailabilityStatus.available
    if score >= 0.50:
        return AvailabilityStatus.limited
    return AvailabilityStatus.unavailable


def calculate_availability(
    terminal: Terminal,
    weather_snapshot: WeatherSnapshot,
) -> tuple[float, AvailabilityStatus, list[str]]:
    """Calculate weighted availability score, status, and explanations."""

    visibility_score, visibility_reason = _score_visibility(
        weather_snapshot.visibility_m,
    )
    cloud_score, cloud_reason = _score_cloud_cover(
        weather_snapshot.cloud_cover_percent,
    )
    precipitation_score, precipitation_reason = _score_precipitation(
        weather_snapshot.precipitation_mm,
    )
    wind_score, wind_reason = _score_wind(weather_snapshot.wind_speed_kmh)
    hardware_score, hardware_reason = _score_hardware(terminal.status)
    reasons = [
        visibility_reason,
        cloud_reason,
        precipitation_reason,
        wind_reason,
        hardware_reason,
    ]

    score = (
        0.35 * visibility_score
        + 0.30 * cloud_score
        + 0.15 * precipitation_score
        + 0.10 * wind_score
        + 0.10 * hardware_score
    )

    if terminal.status == TerminalStatus.offline:
        score = min(score, 0.49)
        reasons.append("Offline terminals cannot be used for satellite transmission")
    elif terminal.status == TerminalStatus.maintenance:
        score = min(score, 0.74)
        reasons.append("Maintenance mode limits satellite transmission")

    rounded_score = round(score, 4)
    return rounded_score, _status_from_score(rounded_score), reasons


def get_latest_weather_snapshot(
    db: Session,
    terminal_id: int,
) -> WeatherSnapshot | None:
    """Return latest weather snapshot for a terminal, or None."""

    return db.scalar(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.terminal_id == terminal_id)
        .order_by(WeatherSnapshot.timestamp.desc(), WeatherSnapshot.id.desc()),
    )


def _get_or_create_latest_weather(
    db: Session,
    terminal_id: int,
    weather_client: OpenMeteoClient,
) -> WeatherSnapshot:
    """Return latest weather snapshot or fetch one when no data exists."""

    snapshot = get_latest_weather_snapshot(db, terminal_id)
    if snapshot is not None:
        return snapshot
    return update_terminal_weather(db, terminal_id, weather_client)


def check_terminal_availability(
    db: Session,
    terminal_id: int,
    created_by_user_id: int,
    weather_client: OpenMeteoClient,
) -> AvailabilityCheck:
    """Calculate and persist availability for one terminal."""

    terminal = get_terminal_or_404(db, terminal_id)
    weather_snapshot = _get_or_create_latest_weather(db, terminal_id, weather_client)
    score, availability_status, reasons = calculate_availability(
        terminal,
        weather_snapshot,
    )
    check = AvailabilityCheck(
        terminal_id=terminal_id,
        weather_snapshot_id=weather_snapshot.id,
        availability_score=score,
        status=availability_status,
        reason=reasons,
        created_by_user_id=created_by_user_id,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def check_all_terminals(
    db: Session,
    created_by_user_id: int,
    weather_client: OpenMeteoClient,
) -> list[AvailabilityCheck]:
    """Calculate and persist availability for every terminal."""

    terminals = db.scalars(select(Terminal).order_by(Terminal.id)).all()
    return [
        check_terminal_availability(db, terminal.id, created_by_user_id, weather_client)
        for terminal in terminals
    ]


def get_latest_availability(db: Session, terminal_id: int) -> AvailabilityCheck:
    """Return latest availability check for a terminal or raise 404."""

    get_terminal_or_404(db, terminal_id)
    check = db.scalar(
        select(AvailabilityCheck)
        .where(AvailabilityCheck.terminal_id == terminal_id)
        .order_by(AvailabilityCheck.checked_at.desc(), AvailabilityCheck.id.desc()),
    )
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability check not found",
        )
    return check


def get_latest_availability_or_none(
    db: Session,
    terminal_id: int,
) -> AvailabilityCheck | None:
    """Return latest availability check for a terminal, or None."""

    return db.scalar(
        select(AvailabilityCheck)
        .where(AvailabilityCheck.terminal_id == terminal_id)
        .order_by(AvailabilityCheck.checked_at.desc(), AvailabilityCheck.id.desc()),
    )


def get_availability_map(db: Session) -> list[AvailabilityMapItem]:
    """Return all terminals with their latest weather and availability data."""

    terminals = db.scalars(select(Terminal).order_by(Terminal.id)).all()
    items: list[AvailabilityMapItem] = []
    for terminal in terminals:
        latest_check = get_latest_availability_or_none(db, terminal.id)
        latest_weather = get_latest_weather_snapshot(db, terminal.id)
        items.append(
            AvailabilityMapItem(
                terminal_id=terminal.id,
                name=terminal.name,
                latitude=terminal.latitude,
                longitude=terminal.longitude,
                terminal_status=terminal.status,
                availability_status=latest_check.status if latest_check else None,
                availability_score=(
                    latest_check.availability_score if latest_check else None
                ),
                checked_at=latest_check.checked_at if latest_check else None,
                weather_snapshot_id=latest_weather.id if latest_weather else None,
                cloud_cover_percent=(
                    latest_weather.cloud_cover_percent if latest_weather else None
                ),
                visibility_m=latest_weather.visibility_m if latest_weather else None,
                precipitation_mm=(
                    latest_weather.precipitation_mm if latest_weather else None
                ),
                wind_speed_kmh=latest_weather.wind_speed_kmh if latest_weather else None,
            ),
        )
    return items
