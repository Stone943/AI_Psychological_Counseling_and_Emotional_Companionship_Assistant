"""Guest session cleanup — 24-hour TTL expiration worker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class GuestCleanupWorker:
    """Periodic cleanup of expired guest subjects and their data."""

    TTL_HOURS = 24

    def __init__(self) -> None:
        self._last_run: datetime | None = None

    async def run(self) -> int:
        """Delete all guest data past TTL. Returns count of deleted subjects."""
        self._last_run = datetime.now(timezone.utc)
        # Full DB implementation in B-04 domain
        return 0

    def should_run(self) -> bool:
        """Check if enough time has passed since last run."""
        if self._last_run is None:
            return True
        return datetime.now(timezone.utc) - self._last_run > timedelta(hours=1)
