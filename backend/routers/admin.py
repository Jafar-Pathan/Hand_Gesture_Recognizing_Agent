"""
Admin router.

Endpoints:
    GET    /admin/stats           — platform-wide statistics
    GET    /admin/users           — paginated user list
    DELETE /admin/users/{id}      — deactivate (soft-delete) a user
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.security import get_admin_user
from backend.db.database import get_db
from backend.models.prediction import Prediction
from backend.models.training import TrainingJob
from backend.models.user import User
from backend.schemas.admin import StatsOut, UserAdminOut, UserListOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/stats",
    response_model=StatsOut,
    summary="Get platform-wide statistics",
)
def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> StatsOut:
    """Return aggregate platform statistics (admin only)."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0
    total_training_jobs = db.query(func.count(TrainingJob.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    predictions_today = (
        db.query(func.count(Prediction.id))
        .filter(Prediction.timestamp >= today_start)
        .scalar()
        or 0
    )

    return StatsOut(
        total_users=total_users,
        total_predictions=total_predictions,
        total_training_jobs=total_training_jobs,
        predictions_today=predictions_today,
        active_users=active_users,
    )


@router.get(
    "/users",
    response_model=UserListOut,
    summary="List all users",
)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> UserListOut:
    """Return a paginated list of all registered users (admin only)."""
    total = db.query(func.count(User.id)).scalar() or 0
    users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    user_out_list: list[UserAdminOut] = []
    for user in users:
        pred_count = (
            db.query(func.count(Prediction.id))
            .filter(Prediction.user_id == user.id)
            .scalar()
            or 0
        )
        user_out_list.append(
            UserAdminOut(
                id=user.id,
                email=user.email,
                username=user.username,
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=user.created_at,
                prediction_count=pred_count,
            )
        )

    return UserListOut(users=user_out_list, total=total, page=page, page_size=page_size)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user account",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> None:
    """Soft-delete (deactivate) a user account. Admins cannot deactivate themselves."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account.",
        )

    user: Optional[User] = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = False
    db.commit()
    logger.info("User id=%d deactivated by admin id=%d", user_id, admin.id)
