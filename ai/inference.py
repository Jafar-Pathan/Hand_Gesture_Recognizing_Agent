#!/usr/bin/env python3
"""
inference.py — Inference engine for hand-gesture recognition.

Provides the ``GesturePredictor`` class with two inference modes:

* **image** — accepts raw image bytes, decodes, resizes, and classifies.
* **landmark** — accepts 21 MediaPipe hand landmarks (each ``[x, y, z]``),
  flattens to a 63-dim vector, and classifies.

The active mode is selected via the ``INFERENCE_MODE`` environment variable
(default: ``image``).

Thread-safe singleton access via ``GesturePredictor.get_instance()``.

Example:
    >>> predictor = GesturePredictor.get_instance()
    >>> result = predictor.predict_from_image(open("palm.png", "rb").read())
    >>> print(result["gesture"], result["confidence"])
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
IMAGE_SIZE = (224, 224)
NUM_LANDMARKS = 21
LANDMARK_DIMS = 3  # x, y, z
LANDMARK_VECTOR_LEN = NUM_LANDMARKS * LANDMARK_DIMS  # 63

DEFAULT_MODEL_PATH = "models/best_model.keras"
DEFAULT_CLASS_NAMES_PATH = "models/class_names.json"


class GesturePredictor:
    """Production inference engine for hand-gesture recognition.

    Parameters
    ----------
    model_path : str | Path
        Path to the saved Keras ``.keras`` model file.
    class_names_path : str | Path
        Path to ``class_names.json``.
    inference_mode : str
        ``"image"`` or ``"landmark"``.

    Notes
    -----
    Use :meth:`get_instance` for thread-safe singleton access.
    """

    _instance: GesturePredictor | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        class_names_path: str | Path = DEFAULT_CLASS_NAMES_PATH,
        inference_mode: str | None = None,
    ) -> None:
        self._model: Any = None
        self._class_names: list[str] = []
        self._inference_mode: str = (
            inference_mode or os.environ.get("INFERENCE_MODE", "image")
        ).lower()
        self._model_path = Path(model_path).resolve()
        self._class_names_path = Path(class_names_path).resolve()
        self._loaded = False

        self._load_model()

    # ──────────────────────────────────────────────────────────────────────
    # Singleton
    # ──────────────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(
        cls,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        class_names_path: str | Path = DEFAULT_CLASS_NAMES_PATH,
        inference_mode: str | None = None,
    ) -> GesturePredictor:
        """Return (or create) the singleton ``GesturePredictor``.

        Thread-safe via double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        model_path=model_path,
                        class_names_path=class_names_path,
                        inference_mode=inference_mode,
                    )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (useful for testing)."""
        with cls._lock:
            cls._instance = None

    # ──────────────────────────────────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """Load the Keras model and class names from disk."""
        if not self._model_path.is_file():
            logger.error("Model file not found: %s", self._model_path)
            logger.warning(
                "GesturePredictor initialised WITHOUT a model — predictions will fail."
            )
            return

        try:
            import tensorflow as tf

            logger.info("Loading model from %s …", self._model_path)
            self._model = tf.keras.models.load_model(str(self._model_path))
            logger.info("Model loaded successfully.")
        except Exception:
            logger.exception("Failed to load model from %s.", self._model_path)
            return

        if self._class_names_path.is_file():
            try:
                self._class_names = json.loads(
                    self._class_names_path.read_text(encoding="utf-8")
                )
                logger.info("Loaded %d class names.", len(self._class_names))
            except (json.JSONDecodeError, OSError):
                logger.exception("Failed to load class names from %s.", self._class_names_path)
        else:
            logger.warning("Class names file not found: %s", self._class_names_path)

        self._loaded = True
        logger.info("Inference mode: %s", self._inference_mode)

    @property
    def is_loaded(self) -> bool:
        """Whether the model was successfully loaded."""
        return self._loaded

    @property
    def inference_mode(self) -> str:
        """Current inference mode (``image`` or ``landmark``)."""
        return self._inference_mode

    @property
    def class_names(self) -> list[str]:
        """Ordered list of gesture class names."""
        return list(self._class_names)

    # ──────────────────────────────────────────────────────────────────────
    # Internal prediction helpers
    # ──────────────────────────────────────────────────────────────────────

    def _ensure_model(self) -> None:
        """Raise if the model has not been loaded."""
        if not self._loaded or self._model is None:
            raise RuntimeError(
                "Model is not loaded. Ensure the model file exists and "
                "GesturePredictor was initialised correctly."
            )

    def _format_result(self, probabilities: np.ndarray) -> dict[str, Any]:
        """Format raw softmax probabilities into the standard response dict.

        Returns
        -------
        dict
            ``{"gesture": str, "confidence": float, "all_scores": dict}``
        """
        pred_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[pred_idx])
        gesture = (
            self._class_names[pred_idx]
            if pred_idx < len(self._class_names)
            else str(pred_idx)
        )

        all_scores: dict[str, float] = {}
        for idx, prob in enumerate(probabilities):
            name = self._class_names[idx] if idx < len(self._class_names) else str(idx)
            all_scores[name] = round(float(prob), 6)

        return {
            "gesture": gesture,
            "confidence": round(confidence, 6),
            "all_scores": all_scores,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Image-mode prediction
    # ──────────────────────────────────────────────────────────────────────

    def predict_from_image(self, image_bytes: bytes) -> dict[str, Any]:
        """Predict the gesture from raw image bytes.

        Parameters
        ----------
        image_bytes : bytes
            Raw bytes of a JPEG / PNG / BMP image.

        Returns
        -------
        dict
            ``{"gesture": str, "confidence": float, "all_scores": dict}``

        Raises
        ------
        RuntimeError
            If the model is not loaded.
        ValueError
            If the image cannot be decoded.
        """
        self._ensure_model()
        t0 = time.perf_counter()

        # Decode image bytes.
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Failed to decode the provided image bytes.")

        # Resize and normalise.
        img_resized = cv2.resize(img, IMAGE_SIZE, interpolation=cv2.INTER_AREA)
        img_norm = img_resized.astype(np.float32) / 255.0

        # Convert grayscale → RGB (3-channel) and add batch dim.
        img_rgb = np.stack([img_norm] * 3, axis=-1)
        batch = np.expand_dims(img_rgb, axis=0)

        # Predict.
        probabilities = self._model.predict(batch, verbose=0)[0]

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Image inference completed in %.1f ms.", elapsed)

        return self._format_result(probabilities)

    # ──────────────────────────────────────────────────────────────────────
    # Landmark-mode prediction
    # ──────────────────────────────────────────────────────────────────────

    def predict_from_landmarks(
        self, landmarks: list[list[float]]
    ) -> dict[str, Any]:
        """Predict the gesture from 21 hand landmarks.

        Parameters
        ----------
        landmarks : list[list[float]]
            A list of 21 landmarks, each ``[x, y, z]``.

        Returns
        -------
        dict
            ``{"gesture": str, "confidence": float, "all_scores": dict}``

        Raises
        ------
        RuntimeError
            If the model is not loaded.
        ValueError
            If landmarks have incorrect dimensions.
        """
        self._ensure_model()
        t0 = time.perf_counter()

        if len(landmarks) != NUM_LANDMARKS:
            raise ValueError(
                f"Expected {NUM_LANDMARKS} landmarks, got {len(landmarks)}."
            )

        flat: list[float] = []
        for lm in landmarks:
            if len(lm) != LANDMARK_DIMS:
                raise ValueError(
                    f"Each landmark must have {LANDMARK_DIMS} values (x, y, z), "
                    f"got {len(lm)}."
                )
            flat.extend(lm)

        vec = np.array(flat, dtype=np.float32).reshape(1, -1)

        # The image-based models expect (batch, 224, 224, 3).  For landmark
        # mode the model is expected to have a compatible input layer, e.g.
        # a Dense-based model trained on 63-dim vectors.
        # If the loaded model expects image input and the user passes landmarks,
        # we attempt to render a simple skeleton image instead so the model can
        # still produce a result.
        model_input_shape = self._model.input_shape
        if isinstance(model_input_shape, list):
            model_input_shape = model_input_shape[0]

        expected_ndim = len(model_input_shape)
        if expected_ndim == 4:
            # Model expects an image — render landmarks onto a blank canvas.
            canvas = self._render_landmarks_to_image(landmarks)
            batch = np.expand_dims(canvas, axis=0)
        else:
            batch = vec

        probabilities = self._model.predict(batch, verbose=0)[0]

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Landmark inference completed in %.1f ms.", elapsed)

        return self._format_result(probabilities)

    @staticmethod
    def _render_landmarks_to_image(
        landmarks: list[list[float]],
    ) -> np.ndarray:
        """Render MediaPipe-style landmarks onto a 224×224×3 image.

        Landmarks ``x`` and ``y`` are assumed normalised to [0, 1].

        Returns
        -------
        np.ndarray
            Float32 image of shape ``(224, 224, 3)`` with values in [0, 1].
        """
        h, w = IMAGE_SIZE
        canvas = np.zeros((h, w, 3), dtype=np.float32)

        # MediaPipe hand connections (thumb, index, middle, ring, pinky).
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (0, 9), (9, 10), (10, 11), (11, 12),
            (0, 13), (13, 14), (14, 15), (15, 16),
            (0, 17), (17, 18), (18, 19), (19, 20),
            (5, 9), (9, 13), (13, 17),
        ]

        pts = []
        for lm in landmarks:
            x_px = int(lm[0] * (w - 1))
            y_px = int(lm[1] * (h - 1))
            pts.append((x_px, y_px))

        # Draw connections as white lines.
        canvas_uint8 = (canvas * 255).astype(np.uint8)
        for i, j in connections:
            if i < len(pts) and j < len(pts):
                cv2.line(canvas_uint8, pts[i], pts[j], (255, 255, 255), 2)

        # Draw landmark dots.
        for px, py in pts:
            cv2.circle(canvas_uint8, (px, py), 4, (255, 255, 255), -1)

        return canvas_uint8.astype(np.float32) / 255.0

    # ──────────────────────────────────────────────────────────────────────
    # Base64 convenience
    # ──────────────────────────────────────────────────────────────────────

    def predict_from_base64(self, base64_string: str) -> dict[str, Any]:
        """Predict the gesture from a base64-encoded image string.

        Parameters
        ----------
        base64_string : str
            Base64-encoded image (may optionally have a
            ``data:image/...;base64,`` prefix).

        Returns
        -------
        dict
            Same format as :meth:`predict_from_image`.
        """
        # Strip optional data-URL prefix.
        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(base64_string)
        except Exception as exc:
            raise ValueError(f"Failed to decode base64 string: {exc}") from exc

        return self.predict_from_image(image_bytes)

    # ──────────────────────────────────────────────────────────────────────
    # MediaPipe landmark extraction helper
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def extract_landmarks_from_image(
        image_bytes: bytes,
    ) -> list[list[float]] | None:
        """Extract hand landmarks from an image using MediaPipe.

        Parameters
        ----------
        image_bytes : bytes
            Raw image bytes (JPEG / PNG).

        Returns
        -------
        list[list[float]] | None
            21 landmarks each ``[x, y, z]``, or ``None`` if no hand detected.
        """
        try:
            import mediapipe as mp  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "MediaPipe is not installed.  Install it with: pip install mediapipe"
            )
            return None

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Failed to decode image for landmark extraction.")
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        mp_hands = mp.solutions.hands
        with mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.5,
        ) as hands:
            results = hands.process(img_rgb)

        if not results.multi_hand_landmarks:
            logger.info("No hand landmarks detected in the image.")
            return None

        hand = results.multi_hand_landmarks[0]
        landmarks: list[list[float]] = [
            [lm.x, lm.y, lm.z] for lm in hand.landmark
        ]
        return landmarks

    # ──────────────────────────────────────────────────────────────────────
    # Convenience: auto-dispatch based on inference mode
    # ──────────────────────────────────────────────────────────────────────

    def predict(
        self,
        *,
        image_bytes: bytes | None = None,
        landmarks: list[list[float]] | None = None,
        base64_string: str | None = None,
    ) -> dict[str, Any]:
        """Auto-dispatch prediction based on the configured inference mode.

        For ``image`` mode:
            * If ``image_bytes`` is provided, use them directly.
            * Else if ``base64_string`` is provided, decode first.

        For ``landmark`` mode:
            * If ``landmarks`` are provided, use them.
            * Else if ``image_bytes`` or ``base64_string`` is given, extract
              landmarks via MediaPipe first.

        Parameters
        ----------
        image_bytes : bytes | None
            Raw image bytes.
        landmarks : list[list[float]] | None
            21 landmarks.
        base64_string : str | None
            Base64-encoded image.

        Returns
        -------
        dict
            Prediction results.
        """
        if self._inference_mode == "landmark":
            if landmarks is not None:
                return self.predict_from_landmarks(landmarks)
            # Fall back: try to extract landmarks from image.
            raw = image_bytes
            if raw is None and base64_string is not None:
                if "," in base64_string:
                    base64_string = base64_string.split(",", 1)[1]
                raw = base64.b64decode(base64_string)
            if raw is not None:
                extracted = self.extract_landmarks_from_image(raw)
                if extracted is not None:
                    return self.predict_from_landmarks(extracted)
                raise ValueError(
                    "Landmark mode selected but no hand was detected in the image."
                )
            raise ValueError(
                "Landmark mode requires 'landmarks' or 'image_bytes'/'base64_string'."
            )

        # Default: image mode.
        if image_bytes is not None:
            return self.predict_from_image(image_bytes)
        if base64_string is not None:
            return self.predict_from_base64(base64_string)
        raise ValueError("Image mode requires 'image_bytes' or 'base64_string'.")


# ──────────────────────────────────────────────────────────────────────────────
# Quick CLI smoke test
# ──────────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    """Minimal CLI for testing inference from a single image file."""
    import argparse

    parser = argparse.ArgumentParser(description="Quick inference smoke test.")
    parser.add_argument("image", type=str, help="Path to an image file.")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help="Path to saved model.",
    )
    parser.add_argument(
        "--class-names",
        type=str,
        default=DEFAULT_CLASS_NAMES_PATH,
        help="Path to class_names.json.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["image", "landmark"],
        default=None,
        help="Inference mode (default: INFERENCE_MODE env or 'image').",
    )
    args = parser.parse_args()

    predictor = GesturePredictor(
        model_path=args.model,
        class_names_path=args.class_names,
        inference_mode=args.mode,
    )

    image_path = Path(args.image)
    if not image_path.is_file():
        logger.error("Image file not found: %s", image_path)
        return

    raw = image_path.read_bytes()

    if predictor.inference_mode == "landmark":
        landmarks = GesturePredictor.extract_landmarks_from_image(raw)
        if landmarks is None:
            logger.error("No hand detected — cannot run landmark inference.")
            return
        result = predictor.predict_from_landmarks(landmarks)
    else:
        result = predictor.predict_from_image(raw)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
