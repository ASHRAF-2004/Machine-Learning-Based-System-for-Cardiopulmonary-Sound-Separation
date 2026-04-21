import numpy as np

from cpss.application.orchestrator import SeparationOrchestrator
from cpss.domain.models import AudioSample
from cpss.infrastructure.factory import BaselineFactory
from cpss.infrastructure.logging_observer import InMemoryEventLog


def test_orchestrator_emits_events_and_output_shapes() -> None:
    signal = np.random.randn(2048).astype(np.float32)
    sample = AudioSample(signal=signal, sample_rate=4000)

    orchestrator = SeparationOrchestrator(BaselineFactory())
    event_log = InMemoryEventLog()
    orchestrator.attach(event_log)

    result = orchestrator.run_inference(sample)

    assert result.heart.shape == signal.shape
    assert result.lung.shape == signal.shape
    assert len(event_log.events) == 2
    assert event_log.events[0].event_type == "inference_started"
    assert event_log.events[1].event_type == "inference_completed"
