#!/usr/bin/env python3
"""
train.py — Train a hand-gesture classification model.

Supports three backbones (``cnn``, ``mobilenetv2``, ``efficientnetb0``),
selectable via the ``MODEL_BACKBONE`` environment variable or the ``--backbone``
CLI flag.

Usage:
    python -m ai.train --epochs 50 --batch-size 32 --backbone cnn

Reads processed data from ``dataset/processed/data.npz`` and writes
model artefacts to ``models/``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Lazy TF import (keeps startup fast and lets us set env vars first)
# ──────────────────────────────────────────────────────────────────────────────

def _import_tf():
    """Import TensorFlow / Keras with deterministic-seed setup."""
    import tensorflow as tf
    tf.random.set_seed(42)
    return tf


# ──────────────────────────────────────────────────────────────────────────────
# Model builders
# ──────────────────────────────────────────────────────────────────────────────

def build_custom_cnn(input_shape: tuple[int, int, int], num_classes: int):
    """Build the custom CNN backbone.

    Architecture
    ------------
    Conv2D(32,3) → BN → ReLU → MaxPool(2)
    Conv2D(64,3) → BN → ReLU → MaxPool(2)
    Conv2D(128,3) → BN → ReLU → MaxPool(2)
    Conv2D(256,3) → BN → ReLU → MaxPool(2)
    GlobalAveragePooling2D
    Dense(512) → BN → ReLU → Dropout(0.5)
    Dense(256) → ReLU → Dropout(0.3)
    Dense(num_classes, softmax)
    """
    tf = _import_tf()
    layers = tf.keras.layers

    model = tf.keras.Sequential(
        [
            layers.Input(shape=input_shape),
            # Block 1
            layers.Conv2D(32, (3, 3), padding="same"),
            layers.BatchNormalization(),
            layers.Activation("relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            # Block 2
            layers.Conv2D(64, (3, 3), padding="same"),
            layers.BatchNormalization(),
            layers.Activation("relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            # Block 3
            layers.Conv2D(128, (3, 3), padding="same"),
            layers.BatchNormalization(),
            layers.Activation("relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            # Block 4
            layers.Conv2D(256, (3, 3), padding="same"),
            layers.BatchNormalization(),
            layers.Activation("relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            # Head
            layers.GlobalAveragePooling2D(),
            layers.Dense(512),
            layers.BatchNormalization(),
            layers.Activation("relu"),
            layers.Dropout(0.5),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="custom_cnn",
    )
    return model


def build_mobilenetv2(input_shape: tuple[int, int, int], num_classes: int):
    """Build a MobileNetV2-based transfer-learning model.

    The base is frozen; only the classification head is trainable.
    """
    tf = _import_tf()
    layers = tf.keras.layers

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=input_shape,
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    model = tf.keras.Sequential(
        [
            layers.Input(shape=input_shape),
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="mobilenetv2_transfer",
    )
    return model


def build_efficientnetb0(input_shape: tuple[int, int, int], num_classes: int):
    """Build an EfficientNetB0-based transfer-learning model.

    The base is frozen; only the classification head is trainable.
    """
    tf = _import_tf()
    layers = tf.keras.layers

    base_model = tf.keras.applications.EfficientNetB0(
        input_shape=input_shape,
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    model = tf.keras.Sequential(
        [
            layers.Input(shape=input_shape),
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="efficientnetb0_transfer",
    )
    return model


BACKBONE_BUILDERS = {
    "cnn": build_custom_cnn,
    "mobilenetv2": build_mobilenetv2,
    "efficientnetb0": build_efficientnetb0,
}


# ──────────────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────────────

def _grayscale_to_rgb(arr: np.ndarray) -> np.ndarray:
    """Convert (N, H, W) grayscale to (N, H, W, 3) by stacking channels."""
    if arr.ndim == 3:
        return np.stack([arr] * 3, axis=-1)
    if arr.ndim == 4 and arr.shape[-1] == 1:
        return np.concatenate([arr] * 3, axis=-1)
    return arr  # already multi-channel


def load_processed_data(data_dir: str | Path) -> dict[str, Any]:
    """Load processed ``.npz`` data and class names.

    Returns a dict with keys:
    ``X_train``, ``y_train``, ``X_val``, ``y_val``, ``X_test``, ``y_test``,
    ``class_names``, ``augmentation_config``.
    """
    data_path = Path(data_dir).resolve()
    npz_path = data_path / "data.npz"
    class_names_path = data_path / "class_names.json"
    aug_cfg_path = data_path / "augmentation_config.json"

    if not npz_path.is_file():
        logger.error("Processed data not found at %s.  Run augment.py first.", npz_path)
        sys.exit(1)

    logger.info("Loading processed data from %s …", npz_path)
    data = np.load(str(npz_path))

    class_names: list[str] = []
    if class_names_path.is_file():
        class_names = json.loads(class_names_path.read_text(encoding="utf-8"))
    else:
        logger.warning("class_names.json not found; using numeric labels.")

    aug_cfg: dict[str, Any] = {}
    if aug_cfg_path.is_file():
        aug_cfg = json.loads(aug_cfg_path.read_text(encoding="utf-8"))

    return {
        "X_train": data["X_train"],
        "y_train": data["y_train"],
        "X_val": data["X_val"],
        "y_val": data["y_val"],
        "X_test": data["X_test"],
        "y_test": data["y_test"],
        "class_names": class_names,
        "augmentation_config": aug_cfg,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Plotting helpers
# ──────────────────────────────────────────────────────────────────────────────

def save_training_curves(history, output_path: Path) -> None:
    """Save accuracy and loss curves to a PNG file."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Accuracy
    ax1.plot(history.history["accuracy"], label="Train Accuracy")
    ax1.plot(history.history["val_accuracy"], label="Val Accuracy")
    ax1.set_title("Model Accuracy")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Accuracy")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Loss
    ax2.plot(history.history["loss"], label="Train Loss")
    ax2.plot(history.history["val_loss"], label="Val Loss")
    ax2.set_title("Model Loss")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Loss")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    logger.info("Training curves saved to %s", output_path)


def save_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
    output_path: Path,
) -> None:
    """Save a confusion-matrix heatmap to a PNG file."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    tick_labels = class_names if class_names else [str(i) for i in range(cm.shape[0])]
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=tick_labels,
        yticklabels=tick_labels,
        ylabel="True label",
        xlabel="Predicted label",
        title="Confusion Matrix",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Annotate cells.
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                format(cm[i, j], "d"),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
            )

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close(fig)
    logger.info("Confusion matrix saved to %s", output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Training
# ──────────────────────────────────────────────────────────────────────────────

def train(
    data_dir: str = "dataset/processed",
    model_dir: str = "models",
    log_dir: str = "logs/tensorboard",
    backbone: str = "cnn",
    epochs: int = 50,
    batch_size: int = 32,
) -> None:
    """Run the full training pipeline.

    Parameters
    ----------
    data_dir : str
        Path to the directory containing ``data.npz``.
    model_dir : str
        Directory to save model artefacts.
    log_dir : str
        TensorBoard log directory.
    backbone : str
        One of ``cnn``, ``mobilenetv2``, ``efficientnetb0``.
    epochs : int
        Maximum number of training epochs.
    batch_size : int
        Training batch size.
    """
    tf = _import_tf()
    from sklearn.metrics import classification_report

    # ── Resolve backbone ─────────────────────────────────────────────────
    backbone = backbone.lower()
    if backbone not in BACKBONE_BUILDERS:
        logger.error(
            "Unknown backbone '%s'. Choose from: %s",
            backbone,
            ", ".join(BACKBONE_BUILDERS),
        )
        sys.exit(1)

    logger.info("Selected backbone: %s", backbone)

    # ── Load data ────────────────────────────────────────────────────────
    dataset = load_processed_data(data_dir)
    X_train = _grayscale_to_rgb(dataset["X_train"])
    X_val = _grayscale_to_rgb(dataset["X_val"])
    X_test = _grayscale_to_rgb(dataset["X_test"])
    y_train = dataset["y_train"]
    y_val = dataset["y_val"]
    y_test = dataset["y_test"]
    class_names: list[str] = dataset["class_names"]
    aug_cfg: dict[str, Any] = dataset["augmentation_config"]

    num_classes = len(class_names) if class_names else int(y_train.max() + 1)
    input_shape = X_train.shape[1:]  # (224, 224, 3)

    logger.info("Input shape: %s  |  Classes: %d", input_shape, num_classes)
    logger.info(
        "Samples — Train: %d, Val: %d, Test: %d",
        len(y_train),
        len(y_val),
        len(y_test),
    )

    # ── Build model ──────────────────────────────────────────────────────
    model = BACKBONE_BUILDERS[backbone](input_shape, num_classes)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.summary(print_fn=logger.info)

    # ── Prepare directories ──────────────────────────────────────────────
    model_path = Path(model_dir).resolve()
    model_path.mkdir(parents=True, exist_ok=True)
    tb_path = Path(log_dir).resolve()
    tb_path.mkdir(parents=True, exist_ok=True)

    # ── Callbacks ────────────────────────────────────────────────────────
    best_model_file = model_path / "best_model.keras"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(best_model_file),
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            patience=5,
            factor=0.5,
            min_lr=1e-7,
            verbose=1,
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir=str(tb_path),
            histogram_freq=1,
        ),
    ]

    # ── On-the-fly augmentation ──────────────────────────────────────────
    datagen = tf.keras.preprocessing.image.ImageDataGenerator(**aug_cfg)
    datagen.fit(X_train)

    train_gen = datagen.flow(X_train, y_train, batch_size=batch_size)

    # ── Train ────────────────────────────────────────────────────────────
    logger.info("Starting training for up to %d epochs …", epochs)
    history = model.fit(
        train_gen,
        steps_per_epoch=len(X_train) // batch_size,
        epochs=epochs,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1,
    )

    # ── Evaluate on test set ─────────────────────────────────────────────
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    logger.info("Test loss: %.4f  |  Test accuracy: %.4f", test_loss, test_acc)

    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)

    target_names = class_names if class_names else [str(i) for i in range(num_classes)]
    report = classification_report(y_test, y_pred, target_names=target_names)
    logger.info("Classification Report:\n%s", report)

    # ── Save artefacts ───────────────────────────────────────────────────
    save_training_curves(history, model_path / "training_curves.png")
    save_confusion_matrix(y_test, y_pred, class_names, model_path / "confusion_matrix.png")

    # Save class names alongside the model.
    cn_path = model_path / "class_names.json"
    cn_path.write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    logger.info("Class names saved to %s", cn_path)

    logger.info("Training pipeline complete ✓")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Train a hand-gesture classifier.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="dataset/processed",
        help="Directory containing data.npz (default: dataset/processed).",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="models",
        help="Directory to save model artefacts (default: models).",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/tensorboard",
        help="TensorBoard log directory (default: logs/tensorboard).",
    )
    parser.add_argument(
        "--backbone",
        type=str,
        default=None,
        help="Model backbone: cnn | mobilenetv2 | efficientnetb0 (default: cnn or MODEL_BACKBONE env).",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Maximum training epochs (default: 50).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size (default: 32).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)
    backbone = args.backbone or os.environ.get("MODEL_BACKBONE", "cnn")
    train(
        data_dir=args.data_dir,
        model_dir=args.model_dir,
        log_dir=args.log_dir,
        backbone=backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
