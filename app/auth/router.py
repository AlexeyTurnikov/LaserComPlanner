"""Authentication API router."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, Token
from app.auth.service import login_user, register_user
from app.database import get_db
from app.users.models import User
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a user and make the first registered user an admin."""

    return register_user(db, payload)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate user credentials and return a JWT access token."""

    return login_user(db, payload)
