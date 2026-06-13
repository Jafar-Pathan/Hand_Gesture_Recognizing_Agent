"""
Unit tests for the AI inference engine.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ai.inference import GesturePredictor


@pytest.fixture
def mock_tf():
    """Mock TensorFlow and Keras to avoid loading real models during unit tests."""
    with patch("ai.inference.tf") as mock_tf, \
         patch("ai.inference.keras.models.load_model") as mock_load_model:
        
        # Mock a Keras model that returns a dummy prediction array
        mock_model = MagicMock()
        # Shape: (1, 10) representing probabilities for 10 classes
        mock_model.predict.return_value = np.array([[0.1, 0.8, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def mock_mediapipe():
    """Mock MediaPipe Hands."""
    with patch("ai.inference.mp.solutions.hands.Hands") as mock_hands:
        yield mock_hands


@pytest.fixture
def temp_class_names(tmp_path):
    """Create a temporary class_names.json file."""
    import json
    
    file_path = tmp_path / "class_names.json"
    classes = ["Palm", "L", "Fist", "Fist Moved", "Thumb", "Index", "OK", "Palm Moved", "C", "Down"]
    with open(file_path, "w") as f:
        json.dump(classes, f)
    
    return str(file_path)


class TestGesturePredictor:
    
    def test_singleton_instance(self, mock_tf, temp_class_names):
        """Test that get_instance returns a singleton."""
        # Reset the singleton for the test
        GesturePredictor._instance = None
        
        predictor1 = GesturePredictor.get_instance(
            model_path="dummy.keras", 
            class_names_path=temp_class_names
        )
        
        predictor2 = GesturePredictor.get_instance()
        
        assert predictor1 is predictor2
        assert predictor1.is_loaded is True
        assert len(predictor1.class_names) == 10
        assert predictor1.inference_mode == "image"

    def test_predict_from_base64_image_mode(self, mock_tf, temp_class_names):
        """Test base64 prediction in image mode."""
        GesturePredictor._instance = None
        predictor = GesturePredictor.get_instance(
            model_path="dummy.keras", 
            class_names_path=temp_class_names,
            inference_mode="image"
        )
        
        # Create a valid minimal base64 JPEG
        import base64
        import cv2
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", img)
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        
        result = predictor.predict_from_base64(b64)
        
        # mock_model.predict returns [[0.1, 0.8, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
        # argmax is index 1, which corresponds to "L"
        assert result["gesture"] == "L"
        assert result["confidence"] == 0.8
        assert "all_scores" in result
        assert result["all_scores"]["L"] == 0.8
        
    def test_invalid_base64(self, mock_tf, temp_class_names):
        GesturePredictor._instance = None
        predictor = GesturePredictor.get_instance(
            model_path="dummy.keras", 
            class_names_path=temp_class_names
        )
        
        with pytest.raises(ValueError, match="Invalid image data"):
            predictor.predict_from_base64("not-base64")

    def test_predict_from_landmarks(self, mock_tf, temp_class_names):
        GesturePredictor._instance = None
        predictor = GesturePredictor.get_instance(
            model_path="dummy.keras", 
            class_names_path=temp_class_names,
            inference_mode="landmark"
        )
        
        # Create 21 dummy landmarks
        landmarks = [[float(i), float(i), float(i)] for i in range(21)]
        
        result = predictor.predict_from_landmarks(landmarks)
        assert result["gesture"] == "L"
        assert result["confidence"] == 0.8
