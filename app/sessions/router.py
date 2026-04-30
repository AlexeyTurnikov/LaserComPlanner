"""Communication sessions API router."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_engineer_or_admin
from app.sessions.models import CommunicationSession, SessionStatus
from app.sessions.schemas import SessionCreate, SessionRead, SessionUpdate
from app.sessions.service import (
    create_session,
    delete_session,
    get_session_or_404,
    list_sessions,
    update_session,
)
from app.users.models import User

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session_endpoint(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> CommunicationSession:
    """Create a communication session. Engineer or admin only."""

    return create_session(db, payload)


@router.get("", response_model=list[SessionRead])
def list_sessions_endpoint(
    terminal_id: int | None = Query(default=None, ge=1),
    session_status: SessionStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> list[CommunicationSession]:
    """List communication sessions."""

    return list_sessions(db, terminal_id=terminal_id, session_status=session_status)


@router.get("/{session_id}", response_model=SessionRead)
def read_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> CommunicationSession:
    """Return one communication session."""

    return get_session_or_404(db, session_id)


@router.patch("/{session_id}", response_model=SessionRead)
def update_session_endpoint(
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> CommunicationSession:
    """Update a communication session."""

    return update_session(db, session_id, payload)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> Response:
    """Delete a communication session."""

    delete_session(db, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
