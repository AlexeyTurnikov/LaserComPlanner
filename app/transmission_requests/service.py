"""Transmission request persistence and permission logic."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.terminals.service import get_terminal_or_404
from app.transmission_requests.models import (
    TransmissionRequest,
    TransmissionRequestStatus,
)
from app.transmission_requests.schemas import TransmissionRequestCreate
from app.users.models import User, UserRole


def _can_view_all_requests(user: User) -> bool:
    """Return whether the user can see all transmission requests."""

    return user.role in {UserRole.engineer, UserRole.admin}


def get_transmission_request_by_id(
    db: Session,
    request_id: int,
) -> TransmissionRequest | None:
    """Return a transmission request by ID, or None."""

    return db.scalar(
        select(TransmissionRequest).where(TransmissionRequest.id == request_id),
    )


def get_transmission_request_or_404(
    db: Session,
    request_id: int,
) -> TransmissionRequest:
    """Return a transmission request by ID or raise 404."""

    request = get_transmission_request_by_id(db, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transmission request not found",
        )
    return request


def _ensure_request_visible(request: TransmissionRequest, user: User) -> None:
    """Raise 403 when a user cannot access a transmission request."""

    if _can_view_all_requests(user):
        return
    if request.created_by_user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Transmission request is not available for this user",
    )


def create_transmission_request(
    db: Session,
    payload: TransmissionRequestCreate,
    created_by_user_id: int,
) -> TransmissionRequest:
    """Create and persist a transmission request."""

    get_terminal_or_404(db, payload.source_terminal_id)
    request = TransmissionRequest(
        created_by_user_id=created_by_user_id,
        source_terminal_id=payload.source_terminal_id,
        data_volume_gb=payload.data_volume_gb,
        priority=payload.priority,
        min_availability_score=payload.min_availability_score,
        status=TransmissionRequestStatus.created,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_transmission_requests_for_user(
    db: Session,
    user: User,
) -> list[TransmissionRequest]:
    """Return requests visible to a user."""

    query = select(TransmissionRequest).order_by(TransmissionRequest.id)
    if not _can_view_all_requests(user):
        query = query.where(TransmissionRequest.created_by_user_id == user.id)
    return list(db.scalars(query).all())


def get_transmission_request_for_user(
    db: Session,
    request_id: int,
    user: User,
) -> TransmissionRequest:
    """Return one request if visible to a user."""

    request = get_transmission_request_or_404(db, request_id)
    _ensure_request_visible(request, user)
    return request


def update_transmission_request_status(
    db: Session,
    request_id: int,
    request_status: TransmissionRequestStatus,
    user: User,
) -> TransmissionRequest:
    """Update request status when the request is visible to the user."""

    request = get_transmission_request_for_user(db, request_id, user)
    request.status = request_status
    db.commit()
    db.refresh(request)
    return request
