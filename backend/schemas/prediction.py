"""
Prediction request/response Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """Schema for POST /predict."""

    image: str = Field(..., description="Base64-encoded image (JPEG/PNG), optionally with data-URL prefix")
    mode: Optional[str] = Field(None, description="Override inference mode: 'image' or 'landmark'")
    landmarks: Optional[list[list[float]]] = Field(
        None,
        description="21 MediaPipe landmarks [[x,y,z], ...] for landmark-mode inference",
    )


class PredictResponse(BaseModel):
    """Schema for the response from POST /predict."""

    gesture: str = Field(..., description="Predicted gesture class name")
    confidence: float = Field(..., description="Prediction confidence in [0, 1]")
    all_scores: dict[str, float] = Field(..., description="Per-class confidence scores")
    mode: str = Field(..., description="Inference mode used: image or landmark")
    inference_ms: Optional[float] = Field(None, description="Model inference time in milliseconds")
    timestamp: datetime = Field(..., description="UTC timestamp of the prediction")


class HistoryItem(BaseModel):
    """Single row in the user's prediction history."""

    id: int
    gesture: str
    confidence: float
    mode: str
    inference_ms: Optional[float]
    timestamp: datetime

    model_config = {"from_attributes": True}


class HistoryOut(BaseModel):
    """Paginated prediction history response."""

    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
