"""
Prediction router.

Endpoints:
    POST /predict          — run gesture inference on a base64 image
    GET  /predictions      — paginated prediction history for the current user
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.security import get_current_user
from backend.db.database import get_db
from backend.models.prediction import Prediction
from backend.models.user import User
from backend.schemas.prediction import (
    HistoryItem,
    HistoryOut,
    PredictRequest,
    PredictResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])


def _get_predictor():
    """Lazy-import the GesturePredictor singleton to avoid loading TF at startup."""
    from ai.inference import GesturePredictor
    from backend.core.config import settings

    return GesturePredictor.get_instance(
        model_path=settings.MODEL_PATH,
        class_names_path=settings.CLASS_NAMES_PATH,
        inference_mode=settings.INFERENCE_MODE,
    )


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Run gesture recognition on a base64 image",
)
def predict(
    body: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictResponse:
    """
    Accept a base64-encoded image (or raw landmarks) and return the predicted
    gesture with confidence scores.

    - **image**: Base64 image string (with or without `data:image/...;base64,` prefix)
    - **mode**: Optional override for inference mode (`image` or `landmark`)
    - **landmarks**: Optional 21-point landmark array for landmark-mode inference
    """
    predictor = _get_predictor()

    if not predictor.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gesture recognition model is not loaded. Please train a model first.",
        )

    t0 = time.perf_counter()
    try:
        if body.landmarks is not None:
            result = predictor.predict_from_landmarks(body.landmarks)
            used_mode = "landmark"
        else:
            result = predictor.predict_from_base64(body.image)
            used_mode = predictor.inference_mode
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    inference_ms = (time.perf_counter() - t0) * 1000

    # Persist prediction to DB
    now = datetime.now(timezone.utc)
    try:
        db_pred = Prediction(
            user_id=current_user.id,
            gesture=result["gesture"],
            confidence=result["confidence"],
            mode=used_mode,
            inference_ms=round(inference_ms, 2),
            timestamp=now,
        )
        db.add(db_pred)
        db.commit()
    except Exception:
        logger.exception("Failed to persist prediction for user_id=%d", current_user.id)
        # Don't raise — inference succeeded, persistence is best-effort

    return PredictResponse(
        gesture=result["gesture"],
        confidence=result["confidence"],
        all_scores=result.get("all_scores", {}),
        mode=used_mode,
        inference_ms=round(inference_ms, 2),
        timestamp=now,
    )


@router.get(
    "/predictions",
    response_model=HistoryOut,
    summary="Get paginated prediction history",
)
def prediction_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryOut:
    """Return the authenticated user's gesture prediction history, newest first."""
    total = (
        db.query(Prediction).filter(Prediction.user_id == current_user.id).count()
    )
    items = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return HistoryOut(
        items=[HistoryItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
