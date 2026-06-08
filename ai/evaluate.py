#!/usr/bin/env python3
"""
evaluate.py — Evaluate a trained hand-gesture classification model.

Loads the best saved model and the processed test set, produces a full
classification report, confusion-matrix heatmap, per-class accuracy
breakdown, and writes a JSON evaluation report.

Usage:
    python -m ai.evaluate --model models/best_model.keras --data-dir dataset/processed
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _grayscale_to_rgb(arr: np.ndarray) -> np.ndarray:
    """Convert (N, H, W) grayscale to (N, H, W, 3)."""
    if arr.ndim == 3:
        return np.stack([arr] * 3, axis=-1)
    if arr.ndim == 4 and arr.shape[-1] == 1:
        return np.concatenate([arr] * 3, axis=-1)
    return arr


def save_confusion_matrix_heatmap(
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
        title="Evaluation — Confusion Matrix",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

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
    logger.info("Confusion matrix heatmap saved to %s", output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────────────────────────────────────

def evaluate(
    model_path: str = "models/best_model.keras",
    data_dir: str = "dataset/processed",
    output_dir: str = "models",
) -> dict:
    """Run the full evaluation pipeline.

    Parameters
    ----------
    model_path : str
        Path to the saved Keras model.
    data_dir : str
        Directory containing ``data.npz`` and ``class_names.json``.
    output_dir : str
        Directory to write evaluation artefacts.

    Returns
    -------
    dict
        Evaluation results dictionary.
    """
    import tensorflow as tf
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        accuracy_score,
        precision_recall_fscore_support,
    )

    model_file = Path(model_path).resolve()
    data_path = Path(data_dir).resolve()
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # ── Load model ───────────────────────────────────────────────────────
    if not model_file.is_file():
        logger.error("Model file not found: %s", model_file)
        sys.exit(1)
    logger.info("Loading model from %s …", model_file)
    model = tf.keras.models.load_model(str(model_file))

    # ── Load test data ───────────────────────────────────────────────────
    npz_file = data_path / "data.npz"
    if not npz_file.is_file():
        logger.error("Processed data not found at %s.", npz_file)
        sys.exit(1)
    data = np.load(str(npz_file))
    X_test = _grayscale_to_rgb(data["X_test"])
    y_test = data["y_test"]

    # ── Load class names ─────────────────────────────────────────────────
    cn_file = data_path / "class_names.json"
    if cn_file.is_file():
        class_names = json.loads(cn_file.read_text(encoding="utf-8"))
    else:
        # Also check output_dir (train.py copies them there).
        cn_alt = out_path / "class_names.json"
        if cn_alt.is_file():
            class_names = json.loads(cn_alt.read_text(encoding="utf-8"))
        else:
            class_names = [str(i) for i in range(int(y_test.max()) + 1)]

    num_classes = len(class_names)
    logger.info("Evaluating %d test samples across %d classes.", len(y_test), num_classes)

    # ── Predict ──────────────────────────────────────────────────────────
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)

    # ── Classification report ────────────────────────────────────────────
    target_names = class_names if class_names else [str(i) for i in range(num_classes)]
    report_str = classification_report(y_test, y_pred, target_names=target_names)
    logger.info("Classification Report:\n%s", report_str)

    report_dict = classification_report(
        y_test, y_pred, target_names=target_names, output_dict=True
    )

    # ── Per-class accuracy ───────────────────────────────────────────────
    cm = confusion_matrix(y_test, y_pred)
    per_class_accuracy: dict[str, float] = {}
    for idx, name in enumerate(target_names):
        total = cm[idx].sum()
        correct = cm[idx, idx]
        acc = float(correct / total) if total > 0 else 0.0
        per_class_accuracy[name] = round(acc, 4)
        logger.info("  %s — accuracy: %.2f%% (%d / %d)", name, acc * 100, correct, total)

    # ── Precision / recall / F1 (macro & weighted) ───────────────────────
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro"
    )
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted"
    )

    # ── Build results dict ───────────────────────────────────────────────
    results: dict = {
        "model_path": str(model_file),
        "test_samples": int(len(y_test)),
        "test_loss": round(float(test_loss), 6),
        "test_accuracy": round(float(test_acc), 6),
        "macro_avg": {
            "precision": round(float(precision_macro), 4),
            "recall": round(float(recall_macro), 4),
            "f1_score": round(float(f1_macro), 4),
        },
        "weighted_avg": {
            "precision": round(float(precision_weighted), 4),
            "recall": round(float(recall_weighted), 4),
            "f1_score": round(float(f1_weighted), 4),
        },
        "per_class_accuracy": per_class_accuracy,
        "classification_report": report_dict,
        "confusion_matrix": cm.tolist(),
    }

    # ── Save artefacts ───────────────────────────────────────────────────
    report_json_path = out_path / "evaluation_report.json"
    report_json_path.write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    logger.info("Evaluation report saved to %s", report_json_path)

    save_confusion_matrix_heatmap(
        y_test, y_pred, class_names, out_path / "eval_confusion_matrix.png"
    )

    logger.info("Evaluation pipeline complete ✓")
    return results


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate a trained hand-gesture classification model."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/best_model.keras",
        help="Path to the saved Keras model (default: models/best_model.keras).",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="dataset/processed",
        help="Directory containing data.npz (default: dataset/processed).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models",
        help="Directory to write evaluation artefacts (default: models).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)
    evaluate(
        model_path=args.model,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
