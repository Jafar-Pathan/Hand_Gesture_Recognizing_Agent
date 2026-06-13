"""
Tests for the prediction endpoints.

NOTE: These tests mock the GesturePredictor so TensorFlow is not required.
"""

import base64
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Helper: tiny valid JPEG base64 ───────────────────────────────────────────

def _tiny_jpeg_b64() -> str:
    """Generate a minimal 10x10 grayscale JPEG as base64."""
    import cv2
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


MOCK_RESULT = {
    "gesture": "Palm",
    "confidence": 0.97,
    "all_scores": {
        "Palm": 0.97, "L": 0.01, "Fist": 0.01, "Fist Moved": 0.0,
        "Thumb": 0.0, "Index": 0.0, "OK": 0.0, "Palm Moved": 0.01,
        "C": 0.0, "Down": 0.0,
    },
}


@pytest.fixture(autouse=True)
def mock_predictor():
    """Patch GesturePredictor so no TF model is needed."""
    predictor = MagicMock()
    predictor.is_loaded = True
    predictor.inference_mode = "image"
    predictor.predict_from_base64.return_value = MOCK_RESULT
    predictor.predict_from_landmarks.return_value = MOCK_RESULT

    with patch("backend.routers.predict._get_predictor", return_value=predictor):
        yield predictor


class TestPredict:
    def test_predict_success(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"image": _tiny_jpeg_b64()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gesture"] == "Palm"
        assert data["confidence"] == pytest.approx(0.97, abs=0.001)
        assert "all_scores" in data
        assert "timestamp" in data

    def test_predict_unauthenticated(self, client):
        resp = client.post("/api/v1/predict", json={"image": "base64=="})
        assert resp.status_code == 403

    def test_predict_model_not_loaded(self, client, auth_headers, mock_predictor):
        mock_predictor.is_loaded = False
        resp = client.post(
            "/api/v1/predict",
            json={"image": _tiny_jpeg_b64()},
            headers=auth_headers,
        )
        assert resp.status_code == 503

    def test_predict_invalid_base64(self, client, auth_headers, mock_predictor):
        mock_predictor.predict_from_base64.side_effect = ValueError("Failed to decode")
        resp = client.post(
            "/api/v1/predict",
            json={"image": "not-valid-base64!!!"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestPredictionHistory:
    def test_empty_history(self, client, auth_headers):
        resp = client.get("/api/v1/predictions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_history_after_prediction(self, client, auth_headers):
        # Make a prediction first
        client.post(
            "/api/v1/predict",
            json={"image": _tiny_jpeg_b64()},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/predictions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_history_unauthenticated(self, client):
        resp = client.get("/api/v1/predictions")
        assert resp.status_code == 403
