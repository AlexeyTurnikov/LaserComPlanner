"""Users API router."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.users.models import User
from app.users.schemas import UserRead, UserUpdateRole
from app.users.service import (
    delete_user,
    get_user_or_404,
    list_users,
    update_user_role,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the current authenticated user."""

    return current_user


@router.get("", response_model=list[UserRead])
def read_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    """Return all users. Admin only."""

    return list_users(db)


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    """Return one user by ID. Admin only."""

    return get_user_or_404(db, user_id)


@router.patch("/{user_id}/role", response_model=UserRead)
def change_user_role(
    user_id: int,
    payload: UserUpdateRole,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    """Change a user's role. Admin only."""

    return update_user_role(db, user_id, payload.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """Delete a user. Admin only."""

    delete_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
