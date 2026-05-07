"""NeoSSNet strategy implementation for the separation algorithm interface."""

from __future__ import annotations

from pathlib import Path

from app.ml.neossnet_inference import run_neossnet_inference
from app.ml.separation_algorithm import SeparationAlgorithmResult


class NeoSSNetStrategy:
    """Adapter around the existing real NeoSSNet inference function."""

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        if model_config_path is None:
            raise ValueError("NeoSSNet requires a config_path.")

        result = run_neossnet_inference(
            input_wav_path=input_wav_path,
            model_path=model_path,
            model_config_path=model_config_path,
            heart_output_path=heart_output_path,
            lung_output_path=lung_output_path,
            device_name=device_name,
        )

        return SeparationAlgorithmResult(
            heart_file_path=result.heart_file_path,
            lung_file_path=result.lung_file_path,
            sample_rate_hz=result.sample_rate_hz,
            duration_sec=result.duration_sec,
            heart_file_size_bytes=result.heart_file_size_bytes,
            lung_file_size_bytes=result.lung_file_size_bytes,
            input_shape=result.input_shape,
            output_shape=result.output_shape,
        )
