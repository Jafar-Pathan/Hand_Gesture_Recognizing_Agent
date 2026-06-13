"""
SQLAlchemy ORM models package.

Import all models here so that ``Base.metadata`` is fully populated
before ``create_all`` or Alembic's autogenerate is called.
"""

from backend.models.audit import AuditLog  # noqa: F401
from backend.models.prediction import Prediction  # noqa: F401
from backend.models.training import TrainingJob  # noqa: F401
from backend.models.user import User  # noqa: F401

__all__ = ["User", "Prediction", "TrainingJob", "AuditLog"]
