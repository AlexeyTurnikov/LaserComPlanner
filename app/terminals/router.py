"""Terminal API router."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_engineer_or_admin, require_operator_or_higher
from app.terminals.models import Terminal, TerminalStatus
from app.terminals.schemas import (
    TerminalCreate,
    TerminalListItem,
    TerminalRead,
    TerminalUpdate,
)
from app.terminals.service import (
    create_terminal,
    delete_terminal,
    get_terminal_or_404,
    list_terminals,
    update_terminal,
)
from app.users.models import User

router = APIRouter(prefix="/terminals", tags=["terminals"])


@router.post(
    "",
    response_model=TerminalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_terminal_endpoint(
    payload: TerminalCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> Terminal:
    """Create a terminal. Engineer or admin only."""

    return create_terminal(db, payload)


@router.get("", response_model=list[TerminalListItem])
def list_terminals_endpoint(
    status_filter: TerminalStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> list[Terminal]:
    """List terminals with optional filters."""

    return list_terminals(
        db,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{terminal_id}", response_model=TerminalRead)
def read_terminal_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> Terminal:
    """Return one terminal by ID."""

    return get_terminal_or_404(db, terminal_id)


@router.patch("/{terminal_id}", response_model=TerminalRead)
def update_terminal_endpoint(
    terminal_id: int,
    payload: TerminalUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> Terminal:
    """Update a terminal. Engineer or admin only."""

    return update_terminal(db, terminal_id, payload)


@router.delete("/{terminal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_terminal_endpoint(
    terminal_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> Response:
    """Delete a terminal. Engineer or admin only."""

    delete_terminal(db, terminal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
