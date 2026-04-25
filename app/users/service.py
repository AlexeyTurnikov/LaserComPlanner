"""User persistence and role-management use cases."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import get_password_hash
from app.users.models import User, UserRole
from app.users.schemas import UserCreate


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by ID, or None when not found."""

    return db.scalar(select(User).where(User.id == user_id))


def get_user_or_404(db: Session, user_id: int) -> User:
    """Return a user by ID or raise 404."""

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email, or None when not found."""

    return db.scalar(select(User).where(User.email == email))


def count_users(db: Session) -> int:
    """Return total number of users."""

    return db.scalar(select(func.count(User.id))) or 0


def create_user(
    db: Session,
    payload: UserCreate,
    role: UserRole = UserRole.operator,
) -> User:
    """Create and persist a user."""

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    """Return users ordered by ID."""

    return list(db.scalars(select(User).order_by(User.id)).all())


def update_user_role(
    db: Session,
    user_id: int,
    role: UserRole,
) -> User:
    """Update a user's role."""

    user = get_user_or_404(db, user_id)
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """Delete a user by ID."""

    user = get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
