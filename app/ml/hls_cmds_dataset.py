"""PyTorch dataset for processed HLS-CMDS paired heart/lung/mixed WAV files."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from app.database.db import PROJECT_ROOT
from app.ml.audio_utils import EPS, fit_length, load_wav_mono


TARGET_SAMPLE_RATE_HZ = 4000
SEGMENT_SAMPLES = 60000


@dataclass(frozen=True)
class HlsCmdsPair:
    mixed_id: str
    mixed_path: Path
    heart_path: Path
    lung_path: Path


def _resolve_project_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_split_pairs(
    split: str,
    dataset_root: Path | None = None,
) -> list[HlsCmdsPair]:
    dataset_root = dataset_root or PROJECT_ROOT / "datasets" / "hls_cmds"
    split_path = dataset_root / "metadata" / f"{split}_pairs.csv"
    if not split_path.is_file():
        raise FileNotFoundError(
            f"Missing HLS-CMDS split CSV: {split_path}. "
            "Run `python scripts/prepare_dataset.py` first."
        )

    pairs: list[HlsCmdsPair] = []
    with split_path.open("r", encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            pair = HlsCmdsPair(
                mixed_id=row["mixed_id"],
                mixed_path=_resolve_project_path(row["mixed_path"]),
                heart_path=_resolve_project_path(row["heart_path"]),
                lung_path=_resolve_project_path(row["lung_path"]),
            )
            if (
                pair.mixed_path.is_file()
                and pair.heart_path.is_file()
                and pair.lung_path.is_file()
            ):
                pairs.append(pair)
    if not pairs:
        raise RuntimeError(f"No complete HLS-CMDS pairs found for split: {split}")
    return pairs


def _pad_or_crop(
    waveform: np.ndarray,
    segment_samples: int,
    start: int,
) -> np.ndarray:
    audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if audio.size < segment_samples:
        return fit_length(audio, segment_samples)
    return audio[start : start + segment_samples].astype(np.float32, copy=False)


class HlsCmdsSeparationDataset(Dataset):
    """Return `(mixed, target)` tensors for NeoSSNet fine-tuning.

    The mixed waveform is shaped `(1, T)` and the target is shaped `(2, T)`
    with channel 0 as heart and channel 1 as lung. All signals are mono,
    resampled to 4000 Hz, cropped/padded to 60000 samples, and scaled by the
    mixed-input peak so the target scale stays consistent with the input.
    """

    def __init__(
        self,
        split: str,
        dataset_root: Path | None = None,
        segment_samples: int = SEGMENT_SAMPLES,
        random_crop: bool = False,
        max_items: int | None = None,
        seed: int = 42,
    ) -> None:
        self.split = split
        self.segment_samples = segment_samples
        self.random_crop = random_crop
        self.rng = random.Random(seed)
        pairs = load_split_pairs(split, dataset_root=dataset_root)
        self.pairs = pairs[:max_items] if max_items is not None else pairs

    def __len__(self) -> int:
        return len(self.pairs)

    def _crop_start(self, length: int) -> int:
        if length <= self.segment_samples:
            return 0
        if self.random_crop:
            return self.rng.randrange(0, length - self.segment_samples + 1)
        return (length - self.segment_samples) // 2

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        pair = self.pairs[index]
        mixed = load_wav_mono(
            pair.mixed_path,
            target_sample_rate=TARGET_SAMPLE_RATE_HZ,
        ).waveform
        heart = load_wav_mono(
            pair.heart_path,
            target_sample_rate=TARGET_SAMPLE_RATE_HZ,
        ).waveform
        lung = load_wav_mono(
            pair.lung_path,
            target_sample_rate=TARGET_SAMPLE_RATE_HZ,
        ).waveform

        length = min(mixed.size, heart.size, lung.size)
        start = self._crop_start(length)
        mixed = _pad_or_crop(mixed[:length], self.segment_samples, start)
        heart = _pad_or_crop(heart[:length], self.segment_samples, start)
        lung = _pad_or_crop(lung[:length], self.segment_samples, start)

        mixed_peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
        if mixed_peak > EPS:
            mixed = mixed / mixed_peak
            heart = heart / mixed_peak
            lung = lung / mixed_peak

        mixed_tensor = torch.from_numpy(mixed.astype(np.float32)).unsqueeze(0)
        target_tensor = torch.from_numpy(
            np.stack([heart, lung], axis=0).astype(np.float32)
        )
        return mixed_tensor, target_tensor
