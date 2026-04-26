"""Fiber link business logic and persistence."""

from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.fiber_links.models import FiberLink, FiberLinkQuality
from app.fiber_links.schemas import (
    FiberLinkCreate,
    FiberLinkMapItem,
    FiberLinkUpdate,
)
from app.terminals.models import Terminal
from app.terminals.service import get_terminal_or_404

EARTH_RADIUS_KM = 6371.0
FIBER_SIGNAL_SPEED_KM_PER_SEC = 200000.0


def calculate_distance_km(
    source_latitude: float,
    source_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    """Calculate distance between two coordinates using the Haversine formula."""

    source_lat = radians(source_latitude)
    source_lon = radians(source_longitude)
    target_lat = radians(target_latitude)
    target_lon = radians(target_longitude)
    delta_lat = target_lat - source_lat
    delta_lon = target_lon - source_lon

    haversine_value = (
        sin(delta_lat / 2) ** 2
        + cos(source_lat) * cos(target_lat) * sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * asin(sqrt(haversine_value))
    return round(EARTH_RADIUS_KM * central_angle, 3)


def calculate_latency_ms(distance_km: float) -> float:
    """Calculate approximate fiber latency in milliseconds."""

    latency_ms = distance_km / FIBER_SIGNAL_SPEED_KM_PER_SEC * 1000
    return round(latency_ms, 6)


def determine_quality(distance_km: float) -> FiberLinkQuality:
    """Classify link quality according to the 100 km spacing rule."""

    if 80 <= distance_km <= 120:
        return FiberLinkQuality.optimal
    if 50 <= distance_km < 80 or 120 < distance_km <= 150:
        return FiberLinkQuality.acceptable
    if distance_km < 50:
        return FiberLinkQuality.redundant
    return FiberLinkQuality.suboptimal


def get_fiber_link_by_id(db: Session, link_id: int) -> FiberLink | None:
    """Return a fiber link by ID, or None when not found."""

    return db.scalar(select(FiberLink).where(FiberLink.id == link_id))


def get_fiber_link_or_404(db: Session, link_id: int) -> FiberLink:
    """Return a fiber link by ID or raise 404."""

    link = get_fiber_link_by_id(db, link_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiber link not found",
        )
    return link


def _validate_distinct_terminals(source_terminal_id: int, target_terminal_id: int) -> None:
    """Raise 400 when a link connects a terminal to itself."""

    if source_terminal_id == target_terminal_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_terminal_id and target_terminal_id must differ",
        )


def _calculate_link_metrics(
    source_terminal: Terminal,
    target_terminal: Terminal,
) -> tuple[float, float, FiberLinkQuality]:
    """Return calculated distance, latency, and quality for two terminals."""

    distance_km = calculate_distance_km(
        source_terminal.latitude,
        source_terminal.longitude,
        target_terminal.latitude,
        target_terminal.longitude,
    )
    latency_ms = calculate_latency_ms(distance_km)
    quality = determine_quality(distance_km)
    return distance_km, latency_ms, quality


def create_fiber_link(db: Session, payload: FiberLinkCreate) -> FiberLink:
    """Create a fiber link with calculated distance, latency, and quality."""

    source_terminal = get_terminal_or_404(db, payload.source_terminal_id)
    target_terminal = get_terminal_or_404(db, payload.target_terminal_id)
    distance_km, latency_ms, quality = _calculate_link_metrics(
        source_terminal,
        target_terminal,
    )
    link = FiberLink(
        source_terminal_id=payload.source_terminal_id,
        target_terminal_id=payload.target_terminal_id,
        distance_km=distance_km,
        latency_ms=latency_ms,
        capacity_gbps=payload.capacity_gbps,
        is_active=payload.is_active,
        quality=quality,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def list_fiber_links(
    db: Session,
    *,
    is_active: bool | None = None,
    quality: FiberLinkQuality | None = None,
    terminal_id: int | None = None,
) -> list[FiberLink]:
    """Return fiber links filtered by activity, quality, and terminal."""

    query = select(FiberLink).order_by(FiberLink.id)
    if is_active is not None:
        query = query.where(FiberLink.is_active == is_active)
    if quality is not None:
        query = query.where(FiberLink.quality == quality)
    if terminal_id is not None:
        query = query.where(
            or_(
                FiberLink.source_terminal_id == terminal_id,
                FiberLink.target_terminal_id == terminal_id,
            ),
        )
    return list(db.scalars(query).all())


def list_fiber_link_map(db: Session) -> list[FiberLinkMapItem]:
    """Return map-ready fiber links with coordinates for both endpoints."""

    query = (
        select(FiberLink)
        .options(
            joinedload(FiberLink.source_terminal),
            joinedload(FiberLink.target_terminal),
        )
        .order_by(FiberLink.id)
    )
    links = db.scalars(query).all()
    return [
        FiberLinkMapItem(
            id=link.id,
            source_terminal_id=link.source_terminal_id,
            target_terminal_id=link.target_terminal_id,
            source_name=link.source_terminal.name,
            target_name=link.target_terminal.name,
            source_latitude=link.source_terminal.latitude,
            source_longitude=link.source_terminal.longitude,
            target_latitude=link.target_terminal.latitude,
            target_longitude=link.target_terminal.longitude,
            distance_km=link.distance_km,
            latency_ms=link.latency_ms,
            capacity_gbps=link.capacity_gbps,
            is_active=link.is_active,
            quality=link.quality,
        )
        for link in links
    ]


def update_fiber_link(
    db: Session,
    link_id: int,
    payload: FiberLinkUpdate,
) -> FiberLink:
    """Apply a partial update to a fiber link."""

    link = get_fiber_link_or_404(db, link_id)
    update_data = payload.model_dump(exclude_unset=True)

    source_terminal_id = update_data.get(
        "source_terminal_id",
        link.source_terminal_id,
    )
    target_terminal_id = update_data.get(
        "target_terminal_id",
        link.target_terminal_id,
    )
    _validate_distinct_terminals(source_terminal_id, target_terminal_id)

    should_recalculate = (
        "source_terminal_id" in update_data or "target_terminal_id" in update_data
    )
    if should_recalculate:
        source_terminal = get_terminal_or_404(db, source_terminal_id)
        target_terminal = get_terminal_or_404(db, target_terminal_id)
        distance_km, latency_ms, quality = _calculate_link_metrics(
            source_terminal,
            target_terminal,
        )
        link.source_terminal_id = source_terminal_id
        link.target_terminal_id = target_terminal_id
        link.distance_km = distance_km
        link.latency_ms = latency_ms
        link.quality = quality

    if "capacity_gbps" in update_data:
        link.capacity_gbps = update_data["capacity_gbps"]
    if "is_active" in update_data:
        link.is_active = update_data["is_active"]

    db.commit()
    db.refresh(link)
    return link


def delete_fiber_link(db: Session, link_id: int) -> None:
    """Delete a fiber link by ID."""

    link = get_fiber_link_or_404(db, link_id)
    db.delete(link)
    db.commit()
