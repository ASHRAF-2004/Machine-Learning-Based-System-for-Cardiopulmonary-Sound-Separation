from cpss.observer.events import SystemEvent
from cpss.observer.observer import Observer


class InMemoryEventLog(Observer):
    def __init__(self) -> None:
        self.events: list[SystemEvent] = []

    def notify(self, event: SystemEvent) -> None:
        self.events.append(event)
