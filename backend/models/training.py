"""
TrainingJob ORM model.

Tracks background model re-training runs triggered via the admin API.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class TrainingJob(Base):
    """Background model training job record."""

    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued"
    )  # queued | running | done | failed
    backbone: Mapped[str] = mapped_column(String(32), nullable=False, default="cnn")
    epochs: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=32)
    train_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    val_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="training_jobs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<TrainingJob id={self.id!r} status={self.status!r} backbone={self.backbone!r}>"
        )
