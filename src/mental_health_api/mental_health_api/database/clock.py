"""Injectable clock for deterministic time in tests and retention policies."""

from __future__ import annotations

from datetime import datetime, timezone


class Clock:
    """Injectable UTC clock. Default uses real time; tests can freeze."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenClock(Clock):
    """Clock frozen at a specific instant for deterministic testing."""

    def __init__(self, frozen_at: datetime) -> None:
        self._frozen = frozen_at

    def now(self) -> datetime:
        return self._frozen

    def advance(self, **kwargs: int) -> None:
        """Advance the frozen clock by timedelta-compatible kwargs."""
        from datetime import timedelta

        self._frozen += timedelta(**kwargs)
