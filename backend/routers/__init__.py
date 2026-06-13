"""
FastAPI router registry.
"""

from backend.routers.admin import router as admin_router
from backend.routers.auth import router as auth_router
from backend.routers.predict import router as predict_router
from backend.routers.training import router as training_router

__all__ = ["auth_router", "predict_router", "training_router", "admin_router"]
