"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.users.models import UserRole


class LoginRequest(BaseModel):
    """Credentials for JSON-based login."""

    email: EmailStr
    password: str = Field(min_length=8)


class Token(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT identity payload."""

    user_id: int | None = None
    role: UserRole | None = None
