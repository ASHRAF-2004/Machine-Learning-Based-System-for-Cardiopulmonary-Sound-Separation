"""Factory for creating separation algorithm strategies from model records."""

from __future__ import annotations

from app.ml.neossnet_strategy import NeoSSNetStrategy
from app.ml.separation_algorithm import SeparationAlgorithm
from app.models.db_models import Model


class UnsupportedModelArchitectureError(ValueError):
    pass


class SeparationAlgorithmFactory:
    """Factory Method participant that creates the selected separation strategy."""

    _registry: dict[str, type[SeparationAlgorithm]] = {
        "neossnet": NeoSSNetStrategy,
    }

    @classmethod
    def create_algorithm(cls, model: Model) -> SeparationAlgorithm:
        architecture = (model.architecture or "").strip().lower()
        strategy_class = cls._registry.get(architecture)
        if strategy_class is None:
            supported = ", ".join(sorted(cls._registry)) or "none"
            raise UnsupportedModelArchitectureError(
                f"Unsupported separation model architecture: {model.architecture}. "
                f"Supported architectures: {supported}."
            )

        return strategy_class()

    @classmethod
    def resolve(cls, model: Model) -> SeparationAlgorithm:
        """Backward-compatible factory method name used by older tests/docs."""

        return cls.create_algorithm(model)
