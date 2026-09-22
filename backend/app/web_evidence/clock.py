"""Injectable clock for deterministic tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from ..models import utc_now


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return utc_now()


class FakeClock:
    def __init__(self, start: datetime | None = None):
        self._now = start or datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)
