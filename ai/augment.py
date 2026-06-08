#!/usr/bin/env python3
"""
augment.py — Data preprocessing, cleaning, and augmentation for LeapGestRecog.

Loads raw grayscale images from ``dataset/raw/``, cleans, resizes, normalises,
splits into train/val/test sets, and saves processed numpy arrays to
``dataset/processed/``.

Usage:
    python -m ai.augment --input dataset/raw --output dataset/processed

Augmentation is configured but **applied on-the-fly** during training via
``tf.keras.preprocessing.image.ImageDataGenerator``.  This script writes the
augmentation config to the output directory so that ``train.py`` can reload it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
IMAGE_SIZE = (224, 224)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
EXPECTED_GESTURES = [
    "01_palm",
    "02_l",
    "03_fist",
    "04_fist_moved",
    "05_thumb",
    "06_index",
    "07_ok",
    "08_palm_moved",
    "09_c",
    "10_down",
]

AUGMENTATION_CONFIG: dict[str, Any] = {
    "rotation_range": 20,
    "width_shift_range": 0.2,
    "height_shift_range": 0.2,
    "zoom_range": 0.2,
    "horizontal_flip": True,
    "brightness_range": [0.8, 1.2],
    "fill_mode": "nearest",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _find_dataset_root(base: Path) -> Path:
    """Locate the directory that directly contains subject folders.

    The LeapGestRecog dataset may have a wrapper directory after extraction.
    """
    children = sorted([d.name for d in base.iterdir() if d.is_dir()])
    subject_dirs = [d for d in children if d.isdigit() and 0 <= int(d) <= 9]
    if len(subject_dirs) >= 5:
        return base

    for candidate in sorted(base.rglob("*")):
        if not candidate.is_dir():
            continue
        sub_children = sorted([d.name for d in candidate.iterdir() if d.is_dir()])
        sub_digits = [d for d in sub_children if d.isdigit() and 0 <= int(d) <= 9]
        if len(sub_digits) >= 5:
            return candidate
    return base


def _image_hash(data: np.ndarray) -> str:
    """Compute a perceptual hash (MD5 of raw bytes) for duplicate detection."""
    return hashlib.md5(data.tobytes()).hexdigest()


def load_images(input_dir: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load, clean, and resize all images from the raw dataset.

    Parameters
    ----------
    input_dir : Path
        Root of the raw dataset (contains subject sub-folders).

    Returns
    -------
    images : np.ndarray
        Array of shape ``(N, 224, 224)`` with dtype ``float32``, values in
        [0, 1].
    labels : np.ndarray
        Integer labels in ``[0, 9]``.
    class_names : list[str]
        Ordered list of gesture class names.
    """
    root = _find_dataset_root(input_dir)
    logger.info("Loading images from: %s", root)

    subject_dirs = sorted([d for d in root.iterdir() if d.is_dir()])
    if not subject_dirs:
        logger.error("No subject directories found in %s.", root)
        sys.exit(1)

    # Build class-name → label mapping from the first subject that has the
    # gesture folders (they should all have the same set).
    gesture_names: list[str] = []
    for subj in subject_dirs:
        gestures = sorted([g.name for g in subj.iterdir() if g.is_dir()])
        if len(gestures) >= len(EXPECTED_GESTURES):
            gesture_names = gestures
            break
    if not gesture_names:
        # Fallback to expected gestures.
        gesture_names = list(EXPECTED_GESTURES)

    class_to_label = {name: idx for idx, name in enumerate(gesture_names)}
    logger.info("Class mapping: %s", json.dumps(class_to_label, indent=2))

    images: list[np.ndarray] = []
    labels: list[int] = []
    seen_hashes: set[str] = set()

    corrupted_count = 0
    duplicate_count = 0
    loaded_count = 0

    for subj in subject_dirs:
        for gesture_dir in sorted(subj.iterdir()):
            if not gesture_dir.is_dir():
                continue
            gesture_name = gesture_dir.name
            if gesture_name not in class_to_label:
                logger.warning("Unknown gesture folder '%s' — skipping.", gesture_name)
                continue

            label = class_to_label[gesture_name]

            for img_path in sorted(gesture_dir.iterdir()):
                if not img_path.is_file():
                    continue
                if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                # ── Try to load ──────────────────────────────────────────
                try:
                    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        raise ValueError("cv2.imread returned None")
                except Exception:
                    corrupted_count += 1
                    logger.debug("Corrupted image skipped: %s", img_path)
                    continue

                # ── Resize ───────────────────────────────────────────────
                img_resized = cv2.resize(img, IMAGE_SIZE, interpolation=cv2.INTER_AREA)

                # ── Duplicate detection ──────────────────────────────────
                h = _image_hash(img_resized)
                if h in seen_hashes:
                    duplicate_count += 1
                    logger.debug("Duplicate image skipped: %s", img_path)
                    continue
                seen_hashes.add(h)

                images.append(img_resized)
                labels.append(label)
                loaded_count += 1

                if loaded_count % 2000 == 0:
                    logger.info("  … loaded %d images so far.", loaded_count)

    logger.info(
        "Loading complete — %d images loaded, %d corrupted, %d duplicates skipped.",
        loaded_count,
        corrupted_count,
        duplicate_count,
    )

    if loaded_count == 0:
        logger.error("No images were loaded. Check dataset path and structure.")
        sys.exit(1)

    # Normalise to [0, 1] float32.
    X = np.array(images, dtype=np.float32) / 255.0
    y = np.array(labels, dtype=np.int32)

    return X, y, gesture_names


def print_statistics(
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    class_names: list[str],
) -> None:
    """Print per-class distribution for each split."""
    for split_name, split_labels in [
        ("Train", y_train),
        ("Validation", y_val),
        ("Test", y_test),
    ]:
        unique, counts = np.unique(split_labels, return_counts=True)
        logger.info("─── %s set: %d samples ───", split_name, len(split_labels))
        for cls_id, count in zip(unique, counts):
            name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
            logger.info("  %s : %d", name, count)


def preprocess_and_save(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_state: int = 42,
) -> None:
    """Full preprocessing pipeline: load → clean → split → save.

    Parameters
    ----------
    input_dir : str | Path
        Path to the raw dataset root.
    output_dir : str | Path
        Path where processed ``.npz`` files will be saved.
    val_ratio : float
        Fraction of data for validation.
    test_ratio : float
        Fraction of data for testing.
    random_state : int
        Seed for reproducible splits.
    """
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    X, y, class_names = load_images(input_path)

    # ── Stratified split: train / (val + test) ──────────────────────────
    val_test_ratio = val_ratio + test_ratio
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=val_test_ratio, random_state=random_state, stratify=y
    )

    # ── Split the remaining into val / test ──────────────────────────────
    relative_test = test_ratio / val_test_ratio
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=relative_test, random_state=random_state, stratify=y_tmp
    )

    logger.info(
        "Split sizes — Train: %d, Val: %d, Test: %d",
        len(y_train),
        len(y_val),
        len(y_test),
    )

    print_statistics(y_train, y_val, y_test, class_names)

    # ── Save ─────────────────────────────────────────────────────────────
    npz_path = output_path / "data.npz"
    np.savez_compressed(
        str(npz_path),
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        X_test=X_test,
        y_test=y_test,
    )
    logger.info("Saved processed arrays to %s", npz_path)

    # Save class names.
    class_names_path = output_path / "class_names.json"
    class_names_path.write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    logger.info("Saved class names to %s", class_names_path)

    # Save augmentation config (used by train.py).
    aug_cfg_path = output_path / "augmentation_config.json"
    aug_cfg_path.write_text(
        json.dumps(AUGMENTATION_CONFIG, indent=2), encoding="utf-8"
    )
    logger.info("Saved augmentation config to %s", aug_cfg_path)

    logger.info("Preprocessing pipeline complete ✓")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Preprocess and augment the LeapGestRecog dataset."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="dataset/raw",
        help="Path to the raw dataset directory (default: dataset/raw).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/processed",
        help="Path to save processed data (default: dataset/processed).",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="Fraction of data for validation (default: 0.1).",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.1,
        help="Fraction of data for testing (default: 0.1).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible splits (default: 42).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)
    preprocess_and_save(
        args.input,
        args.output,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_state=args.seed,
    )


if __name__ == "__main__":
    main()
