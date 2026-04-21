from __future__ import annotations

from abc import ABC, abstractmethod
from .models import AudioSample, SeparationResult


class SeparationStrategy(ABC):
    """Strategy interface for model-agnostic separation behavior."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def separate(self, sample: AudioSample) -> SeparationResult:
        raise NotImplementedError
