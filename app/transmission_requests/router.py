"""Transmission requests API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_operator_or_higher
from app.transmission_requests.models import TransmissionRequest
from app.transmission_requests.schemas import (
    TransmissionRequestCreate,
    TransmissionRequestRead,
    TransmissionRequestUpdateStatus,
)
from app.transmission_requests.service import (
    create_transmission_request,
    get_transmission_request_for_user,
    list_transmission_requests_for_user,
    update_transmission_request_status,
)
from app.users.models import User

router = APIRouter(prefix="/transmission-requests", tags=["transmission requests"])


@router.post("", response_model=TransmissionRequestRead)
def create_transmission_request_endpoint(
    payload: TransmissionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> TransmissionRequest:
    """Create a transmission request for the current user."""

    return create_transmission_request(db, payload, current_user.id)


@router.get("", response_model=list[TransmissionRequestRead])
def list_transmission_requests_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> list[TransmissionRequest]:
    """List visible transmission requests for the current user."""

    return list_transmission_requests_for_user(db, current_user)


@router.get("/{request_id}", response_model=TransmissionRequestRead)
def read_transmission_request_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> TransmissionRequest:
    """Return one visible transmission request."""

    return get_transmission_request_for_user(db, request_id, current_user)


@router.patch("/{request_id}/status", response_model=TransmissionRequestRead)
def update_transmission_request_status_endpoint(
    request_id: int,
    payload: TransmissionRequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator_or_higher),
) -> TransmissionRequest:
    """Update status for a visible transmission request."""

    return update_transmission_request_status(
        db,
        request_id,
        payload.status,
        current_user,
    )
