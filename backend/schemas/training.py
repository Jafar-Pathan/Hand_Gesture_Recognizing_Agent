"""
Training job request/response Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    """Schema for POST /training/start."""

    backbone: str = Field(
        default="cnn",
        description="Model backbone: cnn | mobilenetv2 | efficientnetb0",
    )
    epochs: int = Field(default=50, ge=1, le=500, description="Maximum training epochs")
    batch_size: int = Field(default=32, ge=1, le=512, description="Training batch size")

    @property
    def is_valid_backbone(self) -> bool:
        return self.backbone in ("cnn", "mobilenetv2", "efficientnetb0")


class TrainStatusOut(BaseModel):
    """Status of a single training job."""

    job_id: str
    status: str  # queued | running | done | failed
    backbone: str
    epochs: int
    batch_size: int
    train_accuracy: Optional[float]
    val_accuracy: Optional[float]
    loss: Optional[float]
    error_message: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_job(cls, job) -> "TrainStatusOut":  # type: ignore[override]
        return cls(
            job_id=job.id,
            status=job.status,
            backbone=job.backbone,
            epochs=job.epochs,
            batch_size=job.batch_size,
            train_accuracy=job.train_accuracy,
            val_accuracy=job.val_accuracy,
            loss=job.loss,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


class TrainHistoryOut(BaseModel):
    """Paginated list of training jobs."""

    jobs: list[TrainStatusOut]
    total: int
