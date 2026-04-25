"""Authentication use cases."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, Token
from app.auth.security import create_access_token, verify_password
from app.users.models import User, UserRole
from app.users.schemas import UserCreate
from app.users.service import (
    count_users,
    create_user,
    get_user_by_email,
)


def _role_value(role: UserRole | str) -> str:
    """Return the serializable role value."""

    return role.value if isinstance(role, UserRole) else role


def register_user(db: Session, payload: UserCreate) -> User:
    """Register a user with first-user admin bootstrap behavior."""

    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    role = UserRole.admin if count_users(db) == 0 else UserRole.operator
    return create_user(db, payload, role)


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Return a user when credentials are valid, otherwise None."""

    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def login_user(db: Session, payload: LoginRequest) -> Token:
    """Authenticate credentials and return a bearer token."""

    user = authenticate_user(db, payload.email, payload.password)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "user_id": user.id,
            "role": _role_value(user.role),
        },
    )
    return Token(access_token=access_token)
