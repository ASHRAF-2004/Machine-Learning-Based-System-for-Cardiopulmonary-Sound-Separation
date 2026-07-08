"""Conventional fixed-filter baseline separation strategy."""

from __future__ import annotations

from app.ml.audio_utils import AudioData, frequency_mask_split
from app.ml.strategies.base import BaseSeparationStrategy, SeparatedWaveforms, StrategyContext


class FixedFilterSeparationStrategy(BaseSeparationStrategy):
    """Frequency-mask baseline for workflow and comparison testing."""

    strategy_key = "fixed_filter"
    display_name = "Fixed Filter Baseline"
    method_type = "baseline"

    def separate_waveform(
        self,
        audio: AudioData,
        context: StrategyContext,
    ) -> SeparatedWaveforms:
        heart, lung, metadata = frequency_mask_split(
            audio.waveform,
            audio.sample_rate_hz,
        )
        return SeparatedWaveforms(
            heart=heart,
            lung=lung,
            sample_rate_hz=audio.sample_rate_hz,
            metadata=metadata,
        )
