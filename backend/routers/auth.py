"""
Authentication router.

Endpoints:
    POST /auth/register  — create a new user account
    POST /auth/login     — authenticate and return JWT tokens
    POST /auth/refresh   — exchange refresh token for new access token
    GET  /auth/me        — return the currently authenticated user
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.db.database import get_db
from backend.models.audit import AuditLog
from backend.models.user import User
from backend.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _log_audit(db: Session, action: str, user_id: Optional[int], detail: str, ip: Optional[str]) -> None:
    try:
        entry = AuditLog(user_id=user_id, action=action, detail=detail, ip_address=ip)
        db.add(entry)
        db.commit()
    except Exception:
        logger.exception("Failed to write audit log for action=%s", action)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create a new user account and return JWT tokens."""
    # Check for duplicates
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: id=%d username=%s", user.id, user.username)
    _log_audit(db, "register", user.id, f"New account: {user.email}", _get_client_ip(request))

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.from_orm_user(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password; returns access + refresh tokens."""
    user: Optional[User] = db.query(User).filter(User.email == body.email).first()
    ip = _get_client_ip(request)

    if not user or not verify_password(body.password, user.hashed_password):
        _log_audit(db, "login_failed", None, f"email={body.email}", ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    _log_audit(db, "login_success", user.id, f"email={user.email}", ip)
    logger.info("User logged in: id=%d username=%s", user.id, user.username)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.from_orm_user(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Refresh token required.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user: Optional[User] = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserOut.from_orm_user(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the authenticated user's profile."""
    return UserOut.from_orm_user(current_user)
