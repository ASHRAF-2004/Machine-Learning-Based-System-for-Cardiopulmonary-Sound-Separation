from __future__ import annotations

from cpss.domain.models import AudioSample, SeparationResult
from cpss.infrastructure.factory import ComponentFactory
from cpss.observer.events import SystemEvent
from cpss.observer.observer import Subject


class SeparationOrchestrator(Subject):
    """Coordinates data flow across layered components."""

    def __init__(self, factory: ComponentFactory) -> None:
        super().__init__()
        self._strategy = factory.create_strategy()

    @property
    def strategy_name(self) -> str:
        return self._strategy.name

    def run_inference(self, sample: AudioSample) -> SeparationResult:
        self.emit(SystemEvent.create("inference_started", f"Using strategy={self._strategy.name}"))
        result = self._strategy.separate(sample)
        self.emit(SystemEvent.create("inference_completed", "Separation complete"))
        return result
