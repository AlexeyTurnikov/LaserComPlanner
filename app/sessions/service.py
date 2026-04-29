"""Communication session persistence and scheduling rules."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.sessions.models import CommunicationSession, SessionStatus
from app.sessions.schemas import SessionCreate, SessionUpdate
from app.terminals.service import get_terminal_or_404

BLOCKING_SESSION_STATUSES = {
    SessionStatus.scheduled,
    SessionStatus.active,
}


def get_session_by_id(
    db: Session,
    session_id: int,
) -> CommunicationSession | None:
    """Return a communication session by ID, or None."""

    return db.scalar(select(CommunicationSession).where(CommunicationSession.id == session_id))


def get_session_or_404(db: Session, session_id: int) -> CommunicationSession:
    """Return a communication session by ID or raise 404."""

    session = get_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


def _ensure_valid_time_range(start_time: datetime, end_time: datetime) -> None:
    """Raise 400 when end time is not after start time."""

    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time",
        )


def _has_overlapping_session(
    db: Session,
    *,
    terminal_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_session_id: int | None = None,
) -> bool:
    """Return whether a terminal has overlapping scheduled or active sessions."""

    query = select(CommunicationSession.id).where(
        CommunicationSession.terminal_id == terminal_id,
        CommunicationSession.status.in_(BLOCKING_SESSION_STATUSES),
        start_time < CommunicationSession.end_time,
        end_time > CommunicationSession.start_time,
    )
    if exclude_session_id is not None:
        query = query.where(CommunicationSession.id != exclude_session_id)
    return db.scalar(query) is not None


def _ensure_no_overlap(
    db: Session,
    *,
    terminal_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_session_id: int | None = None,
) -> None:
    """Raise 400 when the requested session overlaps a blocking session."""

    if _has_overlapping_session(
        db,
        terminal_id=terminal_id,
        start_time=start_time,
        end_time=end_time,
        exclude_session_id=exclude_session_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session overlaps an existing scheduled or active session",
        )


def create_session(db: Session, payload: SessionCreate) -> CommunicationSession:
    """Create a communication session with overlap validation."""

    get_terminal_or_404(db, payload.terminal_id)
    _ensure_valid_time_range(payload.start_time, payload.end_time)
    if payload.status in BLOCKING_SESSION_STATUSES:
        _ensure_no_overlap(
            db,
            terminal_id=payload.terminal_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )

    session = CommunicationSession(**payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session,
    *,
    terminal_id: int | None = None,
    status: SessionStatus | None = None,
) -> list[CommunicationSession]:
    """Return communication sessions filtered by terminal and status."""

    query = select(CommunicationSession).order_by(CommunicationSession.id)
    if terminal_id is not None:
        query = query.where(CommunicationSession.terminal_id == terminal_id)
    if status is not None:
        query = query.where(CommunicationSession.status == status)
    return list(db.scalars(query).all())


def update_session(
    db: Session,
    session_id: int,
    payload: SessionUpdate,
) -> CommunicationSession:
    """Apply a partial update to a communication session."""

    session = get_session_or_404(db, session_id)
    update_data = payload.model_dump(exclude_unset=True)
    terminal_id = update_data.get("terminal_id", session.terminal_id)
    start_time = update_data.get("start_time", session.start_time)
    end_time = update_data.get("end_time", session.end_time)
    session_status = update_data.get("status", session.status)

    get_terminal_or_404(db, terminal_id)
    _ensure_valid_time_range(start_time, end_time)
    if session_status in BLOCKING_SESSION_STATUSES:
        _ensure_no_overlap(
            db,
            terminal_id=terminal_id,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=session_id,
        )

    for field_name, value in update_data.items():
        setattr(session, field_name, value)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: int) -> None:
    """Delete a communication session by ID."""

    session = get_session_or_404(db, session_id)
    db.delete(session)
    db.commit()
