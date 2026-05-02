"""Seed realistic demo data for LaserGround Planner."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.availability.models import AvailabilityCheck
from app.availability.service import calculate_availability
from app.database import SESSION_LOCAL
from app.fiber_links.models import FiberLink
from app.fiber_links.schemas import FiberLinkCreate
from app.fiber_links.service import create_fiber_link
from app.terminals.models import Terminal, TerminalStatus
from app.terminals.schemas import TerminalCreate
from app.terminals.service import create_terminal
from app.users.models import User, UserRole
from app.users.schemas import UserCreate
from app.users.service import create_user, get_user_by_email
from app.weather.models import WeatherSnapshot

DEMO_USERS = [
    ("admin@laserground.dev", "admin123", UserRole.admin),
    ("engineer@laserground.dev", "engineer123", UserRole.engineer),
    ("operator@laserground.dev", "operator123", UserRole.operator),
]

DEMO_TERMINALS: list[dict[str, Any]] = [
    {
        "name": "Moscow Terminal",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "altitude_m": 180,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 40,
        "min_elevation_deg": 15,
    },
    {
        "name": "Serpukhov Terminal",
        "latitude": 54.9158,
        "longitude": 37.4111,
        "altitude_m": 165,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 25,
        "min_elevation_deg": 12,
    },
    {
        "name": "Tula Terminal",
        "latitude": 54.1961,
        "longitude": 37.6182,
        "altitude_m": 170,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 22,
        "min_elevation_deg": 12,
    },
    {
        "name": "Kolomna Terminal",
        "latitude": 55.0938,
        "longitude": 38.7684,
        "altitude_m": 145,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 30,
        "min_elevation_deg": 10,
    },
    {
        "name": "Ryazan Terminal",
        "latitude": 54.6292,
        "longitude": 39.7364,
        "altitude_m": 130,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 28,
        "min_elevation_deg": 10,
    },
    {
        "name": "Vladimir Terminal",
        "latitude": 56.1291,
        "longitude": 40.4070,
        "altitude_m": 155,
        "status": TerminalStatus.maintenance,
        "max_data_rate_gbps": 18,
        "min_elevation_deg": 15,
    },
    {
        "name": "Murom Terminal",
        "latitude": 55.5792,
        "longitude": 42.0524,
        "altitude_m": 120,
        "status": TerminalStatus.online,
        "max_data_rate_gbps": 20,
        "min_elevation_deg": 12,
    },
    {
        "name": "Nizhny Novgorod Terminal",
        "latitude": 56.3269,
        "longitude": 44.0059,
        "altitude_m": 140,
        "status": TerminalStatus.offline,
        "max_data_rate_gbps": 35,
        "min_elevation_deg": 15,
    },
]

DEMO_LINKS = [
    ("Moscow Terminal", "Serpukhov Terminal", 20.0, True),
    ("Serpukhov Terminal", "Tula Terminal", 15.0, True),
    ("Moscow Terminal", "Kolomna Terminal", 25.0, True),
    ("Kolomna Terminal", "Ryazan Terminal", 18.0, True),
    ("Moscow Terminal", "Vladimir Terminal", 10.0, True),
    ("Vladimir Terminal", "Murom Terminal", 12.0, True),
    ("Murom Terminal", "Nizhny Novgorod Terminal", 12.0, True),
    ("Ryazan Terminal", "Murom Terminal", 8.0, True),
    ("Tula Terminal", "Ryazan Terminal", 10.0, False),
]

DEMO_WEATHER = {
    "Moscow Terminal": {
        "cloud_cover_percent": 88.0,
        "visibility_m": 4200.0,
        "precipitation_mm": 0.8,
        "wind_speed_kmh": 28.0,
        "wind_gusts_kmh": 42.0,
        "temperature_c": 9.0,
    },
    "Serpukhov Terminal": {
        "cloud_cover_percent": 18.0,
        "visibility_m": 24000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 12.0,
        "wind_gusts_kmh": 18.0,
        "temperature_c": 12.5,
    },
    "Tula Terminal": {
        "cloud_cover_percent": 55.0,
        "visibility_m": 15000.0,
        "precipitation_mm": 0.2,
        "wind_speed_kmh": 18.0,
        "wind_gusts_kmh": 25.0,
        "temperature_c": 11.0,
    },
    "Kolomna Terminal": {
        "cloud_cover_percent": 12.0,
        "visibility_m": 26000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 10.0,
        "wind_gusts_kmh": 16.0,
        "temperature_c": 13.0,
    },
    "Ryazan Terminal": {
        "cloud_cover_percent": 24.0,
        "visibility_m": 21000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 16.0,
        "wind_gusts_kmh": 22.0,
        "temperature_c": 12.0,
    },
    "Vladimir Terminal": {
        "cloud_cover_percent": 18.0,
        "visibility_m": 23000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 14.0,
        "wind_gusts_kmh": 20.0,
        "temperature_c": 10.0,
    },
    "Murom Terminal": {
        "cloud_cover_percent": 20.0,
        "visibility_m": 22000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 17.0,
        "wind_gusts_kmh": 23.0,
        "temperature_c": 10.5,
    },
    "Nizhny Novgorod Terminal": {
        "cloud_cover_percent": 10.0,
        "visibility_m": 25000.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 11.0,
        "wind_gusts_kmh": 17.0,
        "temperature_c": 11.5,
    },
}


def ensure_user(db: Session, email: str, password: str, role: UserRole) -> User:
    """Create a demo user if it does not exist."""

    user = get_user_by_email(db, email)
    if user is not None:
        return user
    return create_user(db, UserCreate(email=email, password=password), role=role)


def ensure_terminal(db: Session, payload: dict[str, Any]) -> Terminal:
    """Create a demo terminal if it does not exist."""

    terminal = db.scalar(select(Terminal).where(Terminal.name == payload["name"]))
    if terminal is not None:
        return terminal
    return create_terminal(db, TerminalCreate(**payload))


def ensure_fiber_link(
    db: Session,
    terminals_by_name: dict[str, Terminal],
    source_name: str,
    target_name: str,
    capacity_gbps: float,
    is_active: bool,
) -> FiberLink:
    """Create a demo fiber link if an equivalent link does not exist."""

    source_terminal = terminals_by_name[source_name]
    target_terminal = terminals_by_name[target_name]
    existing = db.scalar(
        select(FiberLink).where(
            or_(
                and_(
                    FiberLink.source_terminal_id == source_terminal.id,
                    FiberLink.target_terminal_id == target_terminal.id,
                ),
                and_(
                    FiberLink.source_terminal_id == target_terminal.id,
                    FiberLink.target_terminal_id == source_terminal.id,
                ),
            ),
        ),
    )
    if existing is not None:
        return existing

    return create_fiber_link(
        db,
        FiberLinkCreate(
            source_terminal_id=source_terminal.id,
            target_terminal_id=target_terminal.id,
            capacity_gbps=capacity_gbps,
            is_active=is_active,
        ),
    )


def ensure_weather_snapshot(
    db: Session,
    terminal: Terminal,
    weather_data: dict[str, float],
    timestamp: datetime,
) -> WeatherSnapshot:
    """Create a demo weather snapshot if the terminal has none."""

    snapshot = db.scalar(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.terminal_id == terminal.id)
        .order_by(WeatherSnapshot.timestamp.desc(), WeatherSnapshot.id.desc()),
    )
    if snapshot is not None:
        return snapshot

    snapshot = WeatherSnapshot(
        terminal_id=terminal.id,
        timestamp=timestamp,
        cloud_cover_percent=weather_data["cloud_cover_percent"],
        visibility_m=weather_data["visibility_m"],
        precipitation_mm=weather_data["precipitation_mm"],
        wind_speed_kmh=weather_data["wind_speed_kmh"],
        wind_gusts_kmh=weather_data["wind_gusts_kmh"],
        temperature_c=weather_data["temperature_c"],
        raw_payload={"source": "demo-seed", "terminal": terminal.name},
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def ensure_availability_check(
    db: Session,
    terminal: Terminal,
    snapshot: WeatherSnapshot,
    admin_user: User,
) -> AvailabilityCheck:
    """Create a demo availability check if the terminal has none."""

    check = db.scalar(
        select(AvailabilityCheck)
        .where(AvailabilityCheck.terminal_id == terminal.id)
        .order_by(AvailabilityCheck.checked_at.desc(), AvailabilityCheck.id.desc()),
    )
    if check is not None:
        return check

    score, status, reasons = calculate_availability(terminal, snapshot)
    check = AvailabilityCheck(
        terminal_id=terminal.id,
        weather_snapshot_id=snapshot.id,
        availability_score=score,
        status=status,
        reason=reasons,
        created_by_user_id=admin_user.id,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def seed_demo_data(db: Session) -> None:
    """Create all demo users, terminals, links, weather, and availability checks."""

    users = {
        role: ensure_user(db, email, password, role)
        for email, password, role in DEMO_USERS
    }
    terminals_by_name = {
        payload["name"]: ensure_terminal(db, payload)
        for payload in DEMO_TERMINALS
    }

    for source_name, target_name, capacity_gbps, is_active in DEMO_LINKS:
        ensure_fiber_link(
            db,
            terminals_by_name,
            source_name,
            target_name,
            capacity_gbps,
            is_active,
        )

    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    for index, (terminal_name, weather_data) in enumerate(DEMO_WEATHER.items()):
        terminal = terminals_by_name[terminal_name]
        snapshot = ensure_weather_snapshot(
            db,
            terminal,
            weather_data,
            timestamp - timedelta(minutes=index),
        )
        ensure_availability_check(db, terminal, snapshot, users[UserRole.admin])


def main() -> None:
    """Run the demo data seed."""

    db = SESSION_LOCAL()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    print("Demo data is ready.")
    print("Users:")
    for email, password, role in DEMO_USERS:
        print(f"- {role.value}: {email} / {password}")


if __name__ == "__main__":
    main()
