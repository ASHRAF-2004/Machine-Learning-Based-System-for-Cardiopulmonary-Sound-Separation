"""Backward-compatible name for the separation algorithm factory."""

from __future__ import annotations

from app.services.separation_algorithm_factory import (
    SeparationAlgorithmFactory,
    UnsupportedModelArchitectureError,
)


class ModelStrategyResolver(SeparationAlgorithmFactory):
    """Compatibility alias used by older code and tests.

    New documentation should refer to SeparationAlgorithmFactory as the
    Factory Method implementation for selecting a separation strategy.
    """

