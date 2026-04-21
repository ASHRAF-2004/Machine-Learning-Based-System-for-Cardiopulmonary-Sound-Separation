from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class AudioSample:
    """Represents monophonic audio with explicit sample rate."""

    signal: np.ndarray
    sample_rate: int


@dataclass(slots=True)
class SeparationResult:
    """Separated heart/lung outputs and metadata."""

    heart: np.ndarray
    lung: np.ndarray
    strategy_name: str
