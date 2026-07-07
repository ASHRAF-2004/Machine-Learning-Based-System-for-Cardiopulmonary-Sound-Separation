"""Shared timestamp helpers for API-created records."""

from __future__ import annotations

from datetime import datetime


def current_time_text() -> str:
    """Return a timezone-aware timestamp in the server's local timezone."""

    return datetime.now().astimezone().replace(microsecond=0).isoformat()
