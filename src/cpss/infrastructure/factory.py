from __future__ import annotations

from abc import ABC, abstractmethod

from cpss.domain.strategy import SeparationStrategy
from .strategies import FrequencySplitStrategy, NeoSSNetPlaceholderStrategy


class ComponentFactory(ABC):
    """Abstract factory for constructing core components."""

    @abstractmethod
    def create_strategy(self) -> SeparationStrategy:
        raise NotImplementedError


class BaselineFactory(ComponentFactory):
    def create_strategy(self) -> SeparationStrategy:
        return FrequencySplitStrategy()


class NeoSSNetFactory(ComponentFactory):
    def create_strategy(self) -> SeparationStrategy:
        return NeoSSNetPlaceholderStrategy()
