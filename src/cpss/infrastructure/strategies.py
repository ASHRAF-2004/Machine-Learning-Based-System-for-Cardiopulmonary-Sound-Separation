from __future__ import annotations

import numpy as np

from cpss.domain.models import AudioSample, SeparationResult
from cpss.domain.strategy import SeparationStrategy


class FrequencySplitStrategy(SeparationStrategy):
    """Baseline strategy: low frequencies -> heart, high frequencies -> lung."""

    def __init__(self, heart_cutoff_hz: float = 150.0) -> None:
        self._heart_cutoff_hz = heart_cutoff_hz

    @property
    def name(self) -> str:
        return "frequency_split_baseline"

    def separate(self, sample: AudioSample) -> SeparationResult:
        signal = np.asarray(sample.signal, dtype=np.float32)
        fft = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(signal.size, d=1.0 / sample.sample_rate)

        heart_mask = freqs <= self._heart_cutoff_hz
        lung_mask = ~heart_mask

        heart_fft = np.where(heart_mask, fft, 0)
        lung_fft = np.where(lung_mask, fft, 0)

        heart = np.fft.irfft(heart_fft, n=signal.size).astype(np.float32)
        lung = np.fft.irfft(lung_fft, n=signal.size).astype(np.float32)

        return SeparationResult(heart=heart, lung=lung, strategy_name=self.name)


class NeoSSNetPlaceholderStrategy(FrequencySplitStrategy):
    """Placeholder for NeoSSNet inference; currently delegates to baseline."""

    @property
    def name(self) -> str:
        return "neossnet_placeholder"
