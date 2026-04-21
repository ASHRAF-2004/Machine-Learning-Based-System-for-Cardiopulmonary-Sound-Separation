from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(slots=True)
class SystemEvent:
    event_type: str
    message: str
    created_at: datetime

    @classmethod
    def create(cls, event_type: str, message: str) -> "SystemEvent":
        return cls(event_type=event_type, message=message, created_at=datetime.now(UTC))
