"""Base implementation for interchangeable separation strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.ml.audio_utils import (
    AudioData,
    fit_length,
    is_effectively_silent,
    load_wav_mono,
    peak_normalize,
    save_wav_mono,
)
from app.ml.separation_algorithm import SeparationAlgorithmResult


@dataclass(frozen=True)
class StrategyContext:
    model_path: Path | None
    model_config_path: Path | None
    device_name: str = "cpu"


@dataclass(frozen=True)
class SeparatedWaveforms:
    heart: np.ndarray
    lung: np.ndarray
    sample_rate_hz: int
    metadata: dict[str, object] = field(default_factory=dict)


class BaseSeparationStrategy(ABC):
    """Template method base class for real separation strategies."""

    strategy_key = "base"
    display_name = "Base separation strategy"
    method_type = "baseline"
    target_sample_rate_hz: int | None = None

    def load(self, context: StrategyContext) -> None:
        """Load model files or dependencies when a concrete strategy needs them."""

    def preprocess(self, input_wav_path: Path) -> AudioData:
        audio = load_wav_mono(input_wav_path, target_sample_rate=self.target_sample_rate_hz)
        if is_effectively_silent(audio.waveform):
            raise ValueError("Input audio is empty or fully silent.")
        return audio

    @abstractmethod
    def separate_waveform(
        self,
        audio: AudioData,
        context: StrategyContext,
    ) -> SeparatedWaveforms:
        """Return heart and lung waveforms for prepared mono input."""

    def postprocess(
        self,
        outputs: SeparatedWaveforms,
        input_audio: AudioData,
    ) -> SeparatedWaveforms:
        expected_length = input_audio.waveform.size
        heart = peak_normalize(fit_length(outputs.heart, expected_length))
        lung = peak_normalize(fit_length(outputs.lung, expected_length))

        if is_effectively_silent(heart):
            raise ValueError(f"{self.display_name} produced a silent heart output.")
        if is_effectively_silent(lung):
            raise ValueError(f"{self.display_name} produced a silent lung output.")

        metadata = {
            "strategy_key": self.strategy_key,
            "strategy_name": self.display_name,
            "method_type": self.method_type,
            "input_sample_rate_hz": input_audio.sample_rate_hz,
            "input_duration_sec": input_audio.duration_sec,
            **outputs.metadata,
        }
        return SeparatedWaveforms(
            heart=heart,
            lung=lung,
            sample_rate_hz=outputs.sample_rate_hz,
            metadata=metadata,
        )

    def save_outputs(
        self,
        outputs: SeparatedWaveforms,
        heart_output_path: Path,
        lung_output_path: Path,
    ) -> None:
        save_wav_mono(heart_output_path, outputs.heart, outputs.sample_rate_hz)
        save_wav_mono(lung_output_path, outputs.lung, outputs.sample_rate_hz)

    def evaluate(self, outputs: SeparatedWaveforms) -> dict[str, object]:
        """Return non-reference metadata only; reference metrics are service-level."""

        return {
            "heart_rms": float(np.sqrt(np.mean(np.square(outputs.heart)))),
            "lung_rms": float(np.sqrt(np.mean(np.square(outputs.lung)))),
        }

    def separate(
        self,
        input_wav_path: Path,
        model_path: Path | None,
        model_config_path: Path | None,
        heart_output_path: Path,
        lung_output_path: Path,
        device_name: str = "cpu",
    ) -> SeparationAlgorithmResult:
        context = StrategyContext(
            model_path=model_path,
            model_config_path=model_config_path,
            device_name=device_name,
        )
        self.load(context)
        input_audio = self.preprocess(input_wav_path)
        separated = self.separate_waveform(input_audio, context)
        separated = self.postprocess(separated, input_audio)
        self.save_outputs(separated, heart_output_path, lung_output_path)

        metadata = {**separated.metadata, **self.evaluate(separated)}
        frame_count = int(separated.heart.size)
        return SeparationAlgorithmResult(
            heart_file_path=heart_output_path,
            lung_file_path=lung_output_path,
            sample_rate_hz=separated.sample_rate_hz,
            duration_sec=frame_count / separated.sample_rate_hz,
            heart_file_size_bytes=heart_output_path.stat().st_size,
            lung_file_size_bytes=lung_output_path.stat().st_size,
            input_shape=(1, input_audio.waveform.size),
            output_shape=(1, 2, frame_count),
            metadata=metadata,
        )
