#!/usr/bin/env python3
"""
download_dataset.py — Auto-download the LeapGestRecog dataset from Kaggle.

Downloads the 'gti-upm/leapgestrecog' dataset, extracts it into a target
directory, and validates the expected folder structure (10 subjects × 10
gestures).

Usage:
    python -m ai.download_dataset --output dataset/raw

Environment variables:
    KAGGLE_USERNAME  – Kaggle username (or set in ~/.kaggle/kaggle.json)
    KAGGLE_KEY       – Kaggle API key   (or set in ~/.kaggle/kaggle.json)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import zipfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
DATASET_SLUG = "gti-upm/leapgestrecog"
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
EXPECTED_SUBJECT_COUNT = 10


def _check_kaggle_credentials() -> None:
    """Verify that Kaggle credentials are available.

    Checks for the ``KAGGLE_USERNAME`` / ``KAGGLE_KEY`` environment variables
    **or** the ``~/.kaggle/kaggle.json`` file.  Exits with a clear error
    message when neither source is found.
    """
    env_user = os.environ.get("KAGGLE_USERNAME")
    env_key = os.environ.get("KAGGLE_KEY")

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"

    if env_user and env_key:
        logger.info("Kaggle credentials found in environment variables.")
        return

    if kaggle_json.is_file():
        try:
            data = json.loads(kaggle_json.read_text(encoding="utf-8"))
            if data.get("username") and data.get("key"):
                logger.info("Kaggle credentials found in %s.", kaggle_json)
                return
        except (json.JSONDecodeError, KeyError):
            pass

    logger.error(
        "Kaggle credentials are missing.\n"
        "Please set the KAGGLE_USERNAME and KAGGLE_KEY environment variables,\n"
        "or create a ~/.kaggle/kaggle.json file with the following content:\n\n"
        '  {"username": "<your-username>", "key": "<your-api-key>"}\n\n'
        "You can obtain an API key from https://www.kaggle.com/settings"
    )
    sys.exit(1)


def download_dataset(output_dir: str | Path) -> Path:
    """Download and extract the LeapGestRecog dataset.

    Parameters
    ----------
    output_dir : str | Path
        Directory where the dataset will be extracted.

    Returns
    -------
    Path
        The root directory containing the extracted dataset.
    """
    _check_kaggle_credentials()

    # Lazy-import so that the credential check can provide a friendlier
    # error before kaggle itself complains.
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore[import-untyped]
    except ImportError:
        logger.error(
            "The 'kaggle' Python package is not installed.\n"
            "Install it with:  pip install kaggle"
        )
        sys.exit(1)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("Authenticating with the Kaggle API …")
    api = KaggleApi()
    api.authenticate()

    logger.info("Downloading dataset '%s' → %s …", DATASET_SLUG, output_path)
    api.dataset_download_files(DATASET_SLUG, path=str(output_path), unzip=False)

    # The API downloads a single .zip — find and extract it.
    zip_files = list(output_path.glob("*.zip"))
    if not zip_files:
        logger.error("No .zip file found in %s after download.", output_path)
        sys.exit(1)

    for zf in zip_files:
        logger.info("Extracting %s …", zf.name)
        with zipfile.ZipFile(zf, "r") as z:
            total = len(z.namelist())
            for idx, member in enumerate(z.namelist(), 1):
                z.extract(member, output_path)
                if idx % 500 == 0 or idx == total:
                    logger.info("  Extracted %d / %d entries.", idx, total)
        zf.unlink()
        logger.info("Removed zip archive %s.", zf.name)

    logger.info("Download and extraction complete.")
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────

def _find_dataset_root(base: Path) -> Path:
    """Walk *base* to locate the directory containing subject folders.

    The LeapGestRecog zip may contain a top-level wrapper folder.  This
    helper returns the deepest directory that directly contains the subject
    sub-directories (``00``, ``01``, … ``09``).
    """
    # Fast check: base itself might be the root.
    children = sorted([d.name for d in base.iterdir() if d.is_dir()])
    subject_dirs = [d for d in children if d.isdigit() and 0 <= int(d) <= 9]
    if len(subject_dirs) >= EXPECTED_SUBJECT_COUNT:
        return base

    # Otherwise look one or two levels deeper.
    for depth in (1, 2):
        for candidate in base.rglob("*"):
            if not candidate.is_dir():
                continue
            sub_children = sorted([d.name for d in candidate.iterdir() if d.is_dir()])
            sub_digits = [d for d in sub_children if d.isdigit() and 0 <= int(d) <= 9]
            if len(sub_digits) >= EXPECTED_SUBJECT_COUNT:
                return candidate
    return base


def validate_dataset(output_dir: str | Path) -> bool:
    """Validate the extracted dataset folder structure.

    Parameters
    ----------
    output_dir : str | Path
        Root extraction directory.

    Returns
    -------
    bool
        ``True`` when the dataset passes all checks.
    """
    root = _find_dataset_root(Path(output_dir).resolve())
    logger.info("Dataset root detected at: %s", root)

    subject_dirs = sorted([d for d in root.iterdir() if d.is_dir()])
    logger.info("Found %d subject folder(s).", len(subject_dirs))

    if len(subject_dirs) < EXPECTED_SUBJECT_COUNT:
        logger.warning(
            "Expected at least %d subject folders, found %d.",
            EXPECTED_SUBJECT_COUNT,
            len(subject_dirs),
        )
        return False

    all_ok = True
    total_images = 0
    for subj in subject_dirs:
        gesture_dirs = sorted([g for g in subj.iterdir() if g.is_dir()])
        gesture_names = [g.name for g in gesture_dirs]

        missing = [g for g in EXPECTED_GESTURES if g not in gesture_names]
        if missing:
            logger.warning(
                "Subject %s is missing gesture folder(s): %s",
                subj.name,
                ", ".join(missing),
            )
            all_ok = False

        for gd in gesture_dirs:
            image_count = sum(
                1
                for f in gd.iterdir()
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp")
            )
            total_images += image_count
            if image_count == 0:
                logger.warning("No images found in %s.", gd)
                all_ok = False

    if all_ok:
        logger.info(
            "✓ Dataset validation passed — %d subject(s), %d total image(s).",
            len(subject_dirs),
            total_images,
        )
    else:
        logger.warning("Dataset validation completed with warnings.")

    return all_ok


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download the LeapGestRecog dataset from Kaggle."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/raw",
        help="Directory to extract the dataset into (default: dataset/raw).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download and only validate an existing dataset.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)

    if not args.skip_download:
        download_dataset(args.output)

    validate_dataset(args.output)


if __name__ == "__main__":
    main()
