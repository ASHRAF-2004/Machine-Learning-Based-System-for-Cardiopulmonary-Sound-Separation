"""Strategy context for running a selected separation algorithm."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ml.separation_algorithm import (
    SeparationAlgorithm,
    SeparationAlgorithmResult,
)


@dataclass(frozen=True)
class SeparationEngine:
    """Context that runs separation through the shared algorithm interface."""

    algorithm: SeparationAlgorithm
    device_name: str = "cpu"

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
    ) -> SeparationAlgorithmResult:
        return self.algorithm.separate(
            input_wav_path=input_wav_path,
            model_path=model_path,
            model_config_path=model_config_path,
            heart_output_path=heart_output_path,
            lung_output_path=lung_output_path,
            device_name=self.device_name,
        )
