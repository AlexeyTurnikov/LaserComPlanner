"""Terminal persistence use cases."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.terminals.models import Terminal, TerminalStatus
from app.terminals.schemas import TerminalCreate, TerminalUpdate


def get_terminal_by_id(db: Session, terminal_id: int) -> Terminal | None:
    """Return a terminal by ID, or None when not found."""

    return db.scalar(select(Terminal).where(Terminal.id == terminal_id))


def get_terminal_or_404(db: Session, terminal_id: int) -> Terminal:
    """Return a terminal by ID or raise 404."""

    terminal = get_terminal_by_id(db, terminal_id)
    if terminal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal not found",
        )
    return terminal


def create_terminal(db: Session, payload: TerminalCreate) -> Terminal:
    """Create and persist a terminal."""

    terminal = Terminal(**payload.model_dump())
    db.add(terminal)
    db.commit()
    db.refresh(terminal)
    return terminal


def list_terminals(
    db: Session,
    *,
    status: TerminalStatus | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Terminal]:
    """Return terminals filtered by status and name search."""

    query = select(Terminal).order_by(Terminal.id)
    if status is not None:
        query = query.where(Terminal.status == status)
    if search:
        query = query.where(Terminal.name.ilike(f"%{search}%"))
    query = query.limit(limit).offset(offset)
    return list(db.scalars(query).all())


def update_terminal(
    db: Session,
    terminal_id: int,
    payload: TerminalUpdate,
) -> Terminal:
    """Apply a partial update to a terminal."""

    terminal = get_terminal_or_404(db, terminal_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(terminal, field_name, value)
    terminal.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(terminal)
    return terminal


def delete_terminal(db: Session, terminal_id: int) -> None:
    """Delete a terminal by ID."""

    terminal = get_terminal_or_404(db, terminal_id)
    db.delete(terminal)
    db.commit()
