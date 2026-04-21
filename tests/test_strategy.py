import numpy as np

from cpss.domain.models import AudioSample
from cpss.infrastructure.strategies import FrequencySplitStrategy


def test_frequency_split_biases_low_and_high_bands() -> None:
    sample_rate = 4000
    duration_s = 1.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)

    heart_like = np.sin(2 * np.pi * 80 * t)
    lung_like = 0.5 * np.sin(2 * np.pi * 400 * t)
    mixed = (heart_like + lung_like).astype(np.float32)

    strategy = FrequencySplitStrategy(heart_cutoff_hz=150)
    result = strategy.separate(AudioSample(signal=mixed, sample_rate=sample_rate))

    heart_corr = np.corrcoef(result.heart, heart_like)[0, 1]
    lung_corr = np.corrcoef(result.lung, lung_like)[0, 1]

    assert heart_corr > 0.8
    assert lung_corr > 0.8
