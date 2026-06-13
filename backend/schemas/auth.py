"""
Authentication request/response Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Schema for POST /auth/register."""

    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not all(c.isalnum() or c in ("_", "-") for c in v):
            raise ValueError("Username may only contain letters, digits, underscores, and hyphens.")
        return v.strip()


class LoginRequest(BaseModel):
    """Schema for POST /auth/login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class RefreshRequest(BaseModel):
    """Schema for POST /auth/refresh."""

    refresh_token: str = Field(..., description="Valid JWT refresh token")


class UserOut(BaseModel):
    """Public user representation returned by auth endpoints."""

    id: int
    email: str
    username: str
    role: str  # "admin" | "user"  — derived from is_admin
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_user(cls, user) -> "UserOut":  # type: ignore[override]
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            role="admin" if user.is_admin else "user",
            is_active=user.is_active,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    """Token pair returned on successful login or registration."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
