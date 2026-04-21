from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from .events import SystemEvent


class Observer(ABC):
    @abstractmethod
    def notify(self, event: SystemEvent) -> None:
        raise NotImplementedError


class Subject:
    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        self._observers = [obs for obs in self._observers if obs is not observer]

    def observers(self) -> Iterable[Observer]:
        return tuple(self._observers)

    def emit(self, event: SystemEvent) -> None:
        for observer in self._observers:
            observer.notify(event)
