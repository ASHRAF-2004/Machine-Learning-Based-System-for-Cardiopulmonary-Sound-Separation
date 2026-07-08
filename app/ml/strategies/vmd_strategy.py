"""Variational mode decomposition baseline strategy."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from app.ml.audio_utils import (
    AudioData,
    dominant_frequency_hz,
    fit_length,
    frequency_mask_split,
    resample_linear,
)
from app.ml.strategies.base import BaseSeparationStrategy, SeparatedWaveforms, StrategyContext


@dataclass(frozen=True)
class VmdPreset:
    name: str
    mode_count: int
    alpha: float
    tau: float
    tolerance: float
    segment_seconds: float
    overlap_seconds: float
    max_vmd_duration_seconds: float
    internal_sample_rate_hz: int


VMD_PRESETS: dict[str, VmdPreset] = {
    "fast": VmdPreset(
        name="fast",
        mode_count=3,
        alpha=800.0,
        tau=0.0,
        tolerance=1e-4,
        segment_seconds=6.0,
        overlap_seconds=0.25,
        max_vmd_duration_seconds=30.0,
        internal_sample_rate_hz=1000,
    ),
    "quality": VmdPreset(
        name="quality",
        mode_count=5,
        alpha=1500.0,
        tau=0.0,
        tolerance=1e-6,
        segment_seconds=5.0,
        overlap_seconds=0.5,
        max_vmd_duration_seconds=20.0,
        internal_sample_rate_hz=2000,
    ),
}


class VmdSeparationStrategy(BaseSeparationStrategy):
    """VMD decomposition baseline using the MIT-licensed vmdpy package."""

    strategy_key = "vmd"
    display_name = "VMD Decomposition"
    method_type = "decomposition"
    target_sample_rate_hz = 4000

    def __init__(
        self,
        preset: str = "fast",
        mode_count: int | None = None,
        alpha: float | None = None,
        tau: float | None = None,
        tolerance: float | None = None,
        segment_seconds: float | None = None,
        overlap_seconds: float | None = None,
        max_vmd_duration_seconds: float | None = None,
        internal_sample_rate_hz: int | None = None,
        max_iterations: int | None = None,
    ) -> None:
        if preset not in VMD_PRESETS:
            supported = ", ".join(sorted(VMD_PRESETS))
            raise ValueError(f"Unknown VMD preset '{preset}'. Supported presets: {supported}.")
        preset_config = VMD_PRESETS[preset]
        self.preset = preset_config.name
        self.mode_count = mode_count or preset_config.mode_count
        self.alpha = alpha if alpha is not None else preset_config.alpha
        self.tau = tau if tau is not None else preset_config.tau
        self.tolerance = tolerance if tolerance is not None else preset_config.tolerance
        self.segment_seconds = segment_seconds or preset_config.segment_seconds
        self.overlap_seconds = overlap_seconds if overlap_seconds is not None else preset_config.overlap_seconds
        self.max_vmd_duration_seconds = (
            max_vmd_duration_seconds
            if max_vmd_duration_seconds is not None
            else preset_config.max_vmd_duration_seconds
        )
        self.internal_sample_rate_hz = (
            internal_sample_rate_hz
            if internal_sample_rate_hz is not None
            else preset_config.internal_sample_rate_hz
        )
        self.max_iterations = max_iterations
        self._vmd = None

    def load(self, context: StrategyContext) -> None:
        try:
            from vmdpy import VMD
        except ImportError as error:
            raise RuntimeError(
                "VMD strategy requires vmdpy. Install dependencies with "
                "`pip install -r requirements.txt`."
            ) from error

        self._vmd = VMD

    def _split_modes(
        self,
        segment: np.ndarray,
        sample_rate_hz: int,
    ) -> tuple[np.ndarray, np.ndarray, list[float]]:
        if self._vmd is None:
            raise RuntimeError("VMD dependency was not loaded.")

        segment = np.asarray(segment, dtype=np.float32).reshape(-1)
        original_length = segment.size
        internal_sample_rate = min(sample_rate_hz, self.internal_sample_rate_hz)
        vmd_segment = resample_linear(
            segment,
            sample_rate_hz,
            internal_sample_rate,
        )

        modes, _u_hat, _omega = self._vmd(
            vmd_segment.astype(float),
            self.alpha,
            self.tau,
            self.mode_count,
            0,
            1,
            self.tolerance,
        )
        modes = np.asarray(modes, dtype=np.float32)
        frequencies = [
            dominant_frequency_hz(mode, internal_sample_rate)
            for mode in modes
        ]
        frequency_array = np.asarray(frequencies)
        heart_mask = frequency_array <= 220.0

        if not heart_mask.any() or heart_mask.all():
            order = np.argsort(frequency_array)
            split = max(1, len(order) // 2)
            heart_mask = np.zeros(len(order), dtype=bool)
            heart_mask[order[:split]] = True

        heart = modes[heart_mask].sum(axis=0)
        lung = modes[~heart_mask].sum(axis=0)
        if internal_sample_rate != sample_rate_hz:
            heart = resample_linear(heart, internal_sample_rate, sample_rate_hz)
            lung = resample_linear(lung, internal_sample_rate, sample_rate_hz)
            heart = fit_length(heart, original_length)
            lung = fit_length(lung, original_length)
        return heart.astype(np.float32), lung.astype(np.float32), frequencies

    def _separate_segmented(
        self,
        waveform: np.ndarray,
        sample_rate_hz: int,
    ) -> tuple[np.ndarray, np.ndarray, list[float]]:
        segment_length = max(sample_rate_hz, int(self.segment_seconds * sample_rate_hz))
        if waveform.size <= segment_length:
            return self._split_modes(waveform, sample_rate_hz)

        overlap = max(1, int(self.overlap_seconds * sample_rate_hz))
        overlap = min(overlap, max(1, segment_length // 2))
        step = segment_length - overlap
        heart_output = np.zeros_like(waveform, dtype=np.float32)
        lung_output = np.zeros_like(waveform, dtype=np.float32)
        weights = np.zeros_like(waveform, dtype=np.float32)
        all_frequencies: list[float] = []

        start = 0
        while start < waveform.size:
            end = min(start + segment_length, waveform.size)
            segment = waveform[start:end]
            heart, lung, frequencies = self._split_modes(segment, sample_rate_hz)
            heart = fit_length(heart, segment.size)
            lung = fit_length(lung, segment.size)
            window = np.hanning(segment.size).astype(np.float32)
            if start == 0:
                window[: overlap // 2] = 1.0
            if end == waveform.size:
                window[-overlap // 2 :] = 1.0

            heart_output[start:end] += heart * window
            lung_output[start:end] += lung * window
            weights[start:end] += window
            all_frequencies.extend(frequencies)

            if end == waveform.size:
                break
            start += step

        valid = weights > 1e-8
        heart_output[valid] /= weights[valid]
        lung_output[valid] /= weights[valid]
        return heart_output, lung_output, all_frequencies

    def separate_waveform(
        self,
        audio: AudioData,
        context: StrategyContext,
    ) -> SeparatedWaveforms:
        processing_start = time.perf_counter()
        fallback_reason: str | None = None
        frequencies: list[float] = []

        if audio.duration_sec > self.max_vmd_duration_seconds:
            fallback_reason = (
                f"VMD duration limit exceeded "
                f"({audio.duration_sec:.2f}s > {self.max_vmd_duration_seconds:.2f}s)."
            )
            heart, lung, fallback_metadata = frequency_mask_split(
                audio.waveform,
                audio.sample_rate_hz,
            )
        else:
            try:
                heart, lung, frequencies = self._separate_segmented(
                    audio.waveform,
                    audio.sample_rate_hz,
                )
                fallback_metadata = {}
            except Exception as error:
                fallback_reason = f"VMD failed and used fixed-filter fallback: {error}"
                heart, lung, fallback_metadata = frequency_mask_split(
                    audio.waveform,
                    audio.sample_rate_hz,
                )

        processing_time_ms = int((time.perf_counter() - processing_start) * 1000)
        return SeparatedWaveforms(
            heart=heart,
            lung=lung,
            sample_rate_hz=audio.sample_rate_hz,
            metadata={
                "vmd_modes": self.mode_count,
                "vmd_preset": self.preset,
                "vmd_alpha": self.alpha,
                "vmd_tau": self.tau,
                "vmd_tolerance": self.tolerance,
                "vmd_segment_seconds": self.segment_seconds,
                "vmd_overlap_seconds": self.overlap_seconds,
                "vmd_max_duration_seconds": self.max_vmd_duration_seconds,
                "vmd_internal_sample_rate_hz": self.internal_sample_rate_hz,
                "vmd_max_iterations": self.max_iterations,
                "vmd_max_iterations_supported_by_vmdpy": False,
                "vmd_processing_time_ms": processing_time_ms,
                "vmd_fallback_used": fallback_reason is not None,
                "vmd_fallback_reason": fallback_reason,
                **fallback_metadata,
                "mode_dominant_frequencies_hz": [float(value) for value in frequencies],
                "reproduction_note": (
                    "VMD baseline groups decomposed modes by dominant frequency; "
                    "not a trained ML model. The vmdpy package does not expose "
                    "a maximum-iteration argument, so max_iterations is recorded "
                    "for configuration clarity only."
                ),
            },
        )


class VmdFastSeparationStrategy(VmdSeparationStrategy):
    strategy_key = "vmd_fast"
    display_name = "VMD Decomposition (Fast)"

    def __init__(self) -> None:
        super().__init__(preset="fast")


class VmdQualitySeparationStrategy(VmdSeparationStrategy):
    strategy_key = "vmd_quality"
    display_name = "VMD Decomposition (Quality)"

    def __init__(self) -> None:
        super().__init__(preset="quality")
