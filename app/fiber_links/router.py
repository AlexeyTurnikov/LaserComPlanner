"""Fiber link API router."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_engineer_or_admin, require_operator_or_higher
from app.fiber_links.models import FiberLink, FiberLinkQuality
from app.fiber_links.schemas import (
    FiberLinkCreate,
    FiberLinkMapItem,
    FiberLinkRead,
    FiberLinkUpdate,
)
from app.fiber_links.service import (
    create_fiber_link,
    delete_fiber_link,
    get_fiber_link_or_404,
    list_fiber_link_map,
    list_fiber_links,
    update_fiber_link,
)
from app.users.models import User

router = APIRouter(prefix="/fiber-links", tags=["fiber links"])


@router.post(
    "",
    response_model=FiberLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_fiber_link_endpoint(
    payload: FiberLinkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> FiberLink:
    """Create a fiber link and calculate distance, latency, and quality."""

    return create_fiber_link(db, payload)


@router.get("", response_model=list[FiberLinkRead])
def list_fiber_links_endpoint(
    is_active: bool | None = None,
    quality: FiberLinkQuality | None = None,
    terminal_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> list[FiberLink]:
    """List fiber links with optional filters."""

    return list_fiber_links(
        db,
        is_active=is_active,
        quality=quality,
        terminal_id=terminal_id,
    )


@router.get("/map", response_model=list[FiberLinkMapItem])
def list_fiber_links_map_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> list[FiberLinkMapItem]:
    """Return link geometry for map rendering."""

    return list_fiber_link_map(db)


@router.get("/{link_id}", response_model=FiberLinkRead)
def read_fiber_link_endpoint(
    link_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator_or_higher),
) -> FiberLink:
    """Return one fiber link by ID."""

    return get_fiber_link_or_404(db, link_id)


@router.patch("/{link_id}", response_model=FiberLinkRead)
def update_fiber_link_endpoint(
    link_id: int,
    payload: FiberLinkUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> FiberLink:
    """Update a fiber link and recalculate derived fields when needed."""

    return update_fiber_link(db, link_id, payload)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fiber_link_endpoint(
    link_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_engineer_or_admin),
) -> Response:
    """Delete a fiber link."""

    delete_fiber_link(db, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
