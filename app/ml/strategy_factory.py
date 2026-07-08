"""Factory for creating separation strategies from registry records."""

from __future__ import annotations

from app.ml.neossnet_strategy import NeoSSNetStrategy
from app.ml.separation_algorithm import SeparationAlgorithm
from app.ml.strategies.fixed_filter_strategy import FixedFilterSeparationStrategy
from app.ml.strategies.nmf_strategy import NmfSeparationStrategy
from app.ml.strategies.vmd_strategy import (
    VmdFastSeparationStrategy,
    VmdQualitySeparationStrategy,
    VmdSeparationStrategy,
)
from app.models.db_models import Model


class UnsupportedModelArchitectureError(ValueError):
    pass


class SeparationAlgorithmFactory:
    """Factory Method participant for method/strategy selection."""

    _registry: dict[str, type[SeparationAlgorithm]] = {
        "fixed_filter": FixedFilterSeparationStrategy,
        "fixedfilter": FixedFilterSeparationStrategy,
        "neossnet": NeoSSNetStrategy,
        "nmf": NmfSeparationStrategy,
        "vmd": VmdSeparationStrategy,
        "vmd_fast": VmdFastSeparationStrategy,
        "vmd_quality": VmdQualitySeparationStrategy,
    }

    @classmethod
    def strategy_key_for_model(cls, model: Model) -> str:
        strategy_key = (getattr(model, "strategy_key", None) or "").strip().lower()
        if strategy_key:
            return strategy_key
        return (model.architecture or "").strip().replace(" ", "").lower()

    @classmethod
    def create_algorithm(cls, model: Model) -> SeparationAlgorithm:
        strategy_key = cls.strategy_key_for_model(model)
        strategy_class = cls._registry.get(strategy_key)
        if strategy_class is None:
            supported = ", ".join(sorted(cls._registry)) or "none"
            raise UnsupportedModelArchitectureError(
                f"Unsupported separation strategy: {strategy_key or model.architecture}. "
                f"Supported strategies: {supported}."
            )
        return strategy_class()

    @classmethod
    def resolve(cls, model: Model) -> SeparationAlgorithm:
        return cls.create_algorithm(model)
