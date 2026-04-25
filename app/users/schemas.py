"""User request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.users.models import UserRole


class UserCreate(BaseModel):
    """User registration payload."""

    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    """Public user representation."""

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRole(BaseModel):
    """Payload for changing a user's role."""

    role: UserRole
