"""
Admin request/response Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class StatsOut(BaseModel):
    """Platform-wide statistics for the admin dashboard."""

    total_users: int
    total_predictions: int
    total_training_jobs: int
    predictions_today: int
    active_users: int


class UserAdminOut(BaseModel):
    """Extended user view for admin endpoints."""

    id: int
    email: str
    username: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    prediction_count: int = 0

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    """Paginated user list for admin panel."""

    users: list[UserAdminOut]
    total: int
    page: int
    page_size: int
