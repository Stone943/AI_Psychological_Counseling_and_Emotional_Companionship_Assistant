# ruff: noqa: E501  # retention descriptions
"""Retention policies per PRD section 2.6.

All durations use a Clock dependency — never system time directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mental_health_api.database.clock import Clock


@dataclass(frozen=True)
class RetentionPolicy:
    """A single data category's retention rule."""

    category: str
    max_age: timedelta
    description: str


# Frozen retention policies per PRD 2.6
RETENTION_POLICIES: dict[str, RetentionPolicy] = {
    "guest_business": RetentionPolicy(
        "guest_business", timedelta(hours=24), "Guest session/message/assessment/exercise/outbox data"
    ),
    "account_ephemeral": RetentionPolicy(
        "account_ephemeral", timedelta(hours=24), "Account ephemeral conversation data"
    ),
    "account_saved": RetentionPolicy(
        "account_saved", timedelta.max, "Account saved conversations and memories — kept until user deletion"
    ),
    "acked_outbox": RetentionPolicy("acked_outbox", timedelta(days=7), "Acknowledged normal outbox events"),
    "risk_event": RetentionPolicy(
        "risk_event", timedelta(days=30), "Minimal risk events and safety outbox — no free text"
    ),
    "audit_log": RetentionPolicy("audit_log", timedelta(days=90), "Audit log entries — no psychological content"),
    "encrypted_backup": RetentionPolicy("encrypted_backup", timedelta(days=7), "Rolling encrypted backups"),
    "deletion_tombstone": RetentionPolicy(
        "deletion_tombstone", timedelta(days=30), "Deletion tombstones — prevent backup resurrection"
    ),
}


class RetentionCalculator:
    """Calculates expiration deadlines using an injectable clock."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def expires_at(self, policy_key: str, created_at: Clock | None = None) -> int | None:
        """Return the deadline (seconds since epoch) for a given policy.
        Returns None for infinite retention (e.g. account_saved).
        """
        policy = RETENTION_POLICIES.get(policy_key)
        if policy is None:
            return None
        if policy.max_age == timedelta.max:
            return None
        now = self._clock.now()
        deadline = now + policy.max_age
        return int(deadline.timestamp())
