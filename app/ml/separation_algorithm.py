"""Shared interface for cardiopulmonary separation algorithms."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SeparationAlgorithmResult:
    heart_file_path: Path
    lung_file_path: Path
    sample_rate_hz: int
    duration_sec: float
    heart_file_size_bytes: int
    lung_file_size_bytes: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    metadata: dict[str, object] = field(default_factory=dict)


class SeparationAlgorithm(Protocol):
    """Contract implemented by every real separation algorithm."""

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path | None,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        """Separate one mixed WAV file into heart and lung WAV files."""
