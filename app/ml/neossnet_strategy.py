"""NeoSSNet strategy implementation for the separation algorithm interface."""

from __future__ import annotations

from pathlib import Path

from app.ml.neossnet_inference import run_neossnet_inference
from app.ml.separation_algorithm import SeparationAlgorithmResult
from app.ml.strategies.base import StrategyContext


class NeoSSNetStrategy:
    """Adapter around the existing real NeoSSNet inference function."""

    strategy_key = "neossnet"
    display_name = "NeoSSNet"
    method_type = "deep_learning"

    def load(self, context: StrategyContext) -> None:
        if context.model_path is None:
            raise ValueError("NeoSSNet requires a checkpoint_path.")
        if context.model_config_path is None:
            raise ValueError("NeoSSNet requires a config_path.")

    def preprocess(self, input_audio):
        return input_audio

    def postprocess(self, outputs):
        return outputs

    def save_outputs(self, outputs):
        return outputs

    def evaluate(self, outputs):
        return {}

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path | None,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        if model_path is None:
            raise ValueError("NeoSSNet requires a checkpoint_path.")
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
            metadata={
                "strategy_key": self.strategy_key,
                "strategy_name": self.display_name,
                "method_type": self.method_type,
                "input_shape": result.input_shape,
                "output_shape": result.output_shape,
                "sample_rate_assumption_hz": result.sample_rate_hz,
                "channel_order": "channel_0_heart_channel_1_lung",
                "checkpoint_path": str(result.checkpoint_path),
                "config_path": str(result.config_path),
                "bandpass_enabled": result.bandpass_enabled,
                "input_min": result.input_min,
                "input_max": result.input_max,
                "input_rms": result.input_rms,
                "heart_min": result.heart_min,
                "heart_max": result.heart_max,
                "heart_rms": result.heart_rms,
                "lung_min": result.lung_min,
                "lung_max": result.lung_max,
                "lung_rms": result.lung_rms,
            },
        )
