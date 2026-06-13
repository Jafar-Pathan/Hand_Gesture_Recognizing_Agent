"""
Training router.

Endpoints:
    POST /training/start          — start a background training job (admin only)
    GET  /training/status/{id}    — poll a specific training job
    GET  /training/history        — list all training jobs
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.security import get_admin_user, get_current_user
from backend.db.database import SessionLocal, get_db
from backend.models.training import TrainingJob
from backend.models.user import User
from backend.schemas.training import TrainHistoryOut, TrainRequest, TrainStatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["Training"])


def _run_training_job(job_id: str, backbone: str, epochs: int, batch_size: int) -> None:
    """Execute training in a background thread; updates TrainingJob record."""
    db: Session = SessionLocal()
    try:
        job: Optional[TrainingJob] = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            logger.error("Training job %s not found in DB", job_id)
            return

        job.status = "running"
        db.commit()

        logger.info("Starting training job %s: backbone=%s epochs=%d", job_id, backbone, epochs)

        # Import here to avoid loading TF at module import time
        from ai.train import train as run_train

        run_train(
            data_dir="dataset/processed",
            model_dir="models",
            log_dir="logs/tensorboard",
            backbone=backbone,
            epochs=epochs,
            batch_size=batch_size,
        )

        # Re-fetch in case of long-running job
        db.refresh(job)
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Training job %s completed successfully.", job_id)

    except Exception as exc:
        logger.exception("Training job %s failed: %s", job_id, exc)
        try:
            db.refresh(job)
            job.status = "failed"
            job.error_message = str(exc)[:1000]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            logger.exception("Failed to update job status to failed for %s", job_id)
    finally:
        db.close()


@router.post(
    "/start",
    response_model=TrainStatusOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a model training job (admin only)",
)
def start_training(
    body: TrainRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> TrainStatusOut:
    """
    Trigger a new model training run in the background.
    Only accessible to admin users.

    Returns the newly created job record immediately (status: `queued`).
    Poll `/training/status/{job_id}` to track progress.
    """
    if body.backbone not in ("cnn", "mobilenetv2", "efficientnetb0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid backbone '{body.backbone}'. Choose from: cnn, mobilenetv2, efficientnetb0.",
        )

    # Check for an already-running job
    running = (
        db.query(TrainingJob)
        .filter(TrainingJob.status.in_(["queued", "running"]))
        .first()
    )
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A training job is already in progress (id={running.id}, status={running.status}).",
        )

    job = TrainingJob(
        user_id=admin_user.id,
        status="queued",
        backbone=body.backbone,
        epochs=body.epochs,
        batch_size=body.batch_size,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Fire background thread
    thread = threading.Thread(
        target=_run_training_job,
        args=(job.id, body.backbone, body.epochs, body.batch_size),
        daemon=True,
        name=f"train-{job.id[:8]}",
    )
    thread.start()

    logger.info("Training job %s queued by admin user_id=%d", job.id, admin_user.id)
    return TrainStatusOut.from_orm_job(job)


@router.get(
    "/status/{job_id}",
    response_model=TrainStatusOut,
    summary="Get training job status",
)
def get_training_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainStatusOut:
    """Poll the status of a specific training job by its ID."""
    job: Optional[TrainingJob] = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training job not found.")
    return TrainStatusOut.from_orm_job(job)


@router.get(
    "/history",
    response_model=TrainHistoryOut,
    summary="List all training jobs",
)
def training_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainHistoryOut:
    """Return a paginated list of all training jobs, newest first."""
    total = db.query(TrainingJob).count()
    jobs = (
        db.query(TrainingJob)
        .order_by(TrainingJob.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return TrainHistoryOut(
        jobs=[TrainStatusOut.from_orm_job(j) for j in jobs],
        total=total,
    )
