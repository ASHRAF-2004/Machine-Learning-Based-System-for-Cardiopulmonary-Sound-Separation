from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from app.ml.audio_utils import save_wav_mono
from app.ml.hls_cmds_dataset import (
    HlsCmdsSeparationDataset,
    SEGMENT_SAMPLES,
    TARGET_SAMPLE_RATE_HZ,
)


def _write_pair(dataset_root: Path, split: str, sample_id: str = "0001") -> None:
    metadata_dir = dataset_root / "metadata"
    mixed_dir = dataset_root / "processed" / split / "mixed"
    heart_dir = dataset_root / "processed" / split / "heart"
    lung_dir = dataset_root / "processed" / split / "lung"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    mixed_dir.mkdir(parents=True, exist_ok=True)
    heart_dir.mkdir(parents=True, exist_ok=True)
    lung_dir.mkdir(parents=True, exist_ok=True)

    t = np.arange(TARGET_SAMPLE_RATE_HZ, dtype=np.float32) / TARGET_SAMPLE_RATE_HZ
    heart = 0.35 * np.sin(2 * np.pi * 80.0 * t)
    lung = 0.2 * np.sin(2 * np.pi * 650.0 * t)
    mixed = heart + lung

    mixed_path = mixed_dir / f"M{sample_id}.wav"
    heart_path = heart_dir / f"H{sample_id}.wav"
    lung_path = lung_dir / f"L{sample_id}.wav"
    save_wav_mono(mixed_path, mixed, TARGET_SAMPLE_RATE_HZ)
    save_wav_mono(heart_path, heart, TARGET_SAMPLE_RATE_HZ)
    save_wav_mono(lung_path, lung, TARGET_SAMPLE_RATE_HZ)

    with (metadata_dir / f"{split}_pairs.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "split",
                "mixed_id",
                "heart_id",
                "lung_id",
                "mixed_path",
                "heart_path",
                "lung_path",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "split": split,
                "mixed_id": f"M{sample_id}",
                "heart_id": f"H{sample_id}",
                "lung_id": f"L{sample_id}",
                "mixed_path": str(mixed_path),
                "heart_path": str(heart_path),
                "lung_path": str(lung_path),
            }
        )


def test_hls_cmds_dataset_returns_neossnet_shapes(tmp_path: Path) -> None:
    _write_pair(tmp_path, "train")

    dataset = HlsCmdsSeparationDataset(split="train", dataset_root=tmp_path)
    mixed, target = dataset[0]

    assert mixed.shape == (1, SEGMENT_SAMPLES)
    assert target.shape == (2, SEGMENT_SAMPLES)
    assert mixed.dtype.is_floating_point
    assert target.dtype.is_floating_point
    assert float(mixed.abs().max()) <= 1.0
