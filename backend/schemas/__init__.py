"""
Pydantic schemas package.

Exports all request/response models used by the FastAPI routers.
"""

from backend.schemas.auth import (  # noqa: F401
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from backend.schemas.prediction import (  # noqa: F401
    HistoryItem,
    HistoryOut,
    PredictRequest,
    PredictResponse,
)
from backend.schemas.training import (  # noqa: F401
    TrainHistoryOut,
    TrainRequest,
    TrainStatusOut,
)
from backend.schemas.admin import StatsOut, UserAdminOut, UserListOut  # noqa: F401

__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserOut",
    "PredictRequest",
    "PredictResponse",
    "HistoryItem",
    "HistoryOut",
    "TrainRequest",
    "TrainStatusOut",
    "TrainHistoryOut",
    "StatsOut",
    "UserAdminOut",
    "UserListOut",
]
