"""Verify retention policies match PRD section 2.6."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mental_health_api.database.clock import FrozenClock
from mental_health_api.database.retention import RETENTION_POLICIES, RetentionCalculator


class TestRetentionPolicies:
    def test_all_policy_keys_exist(self) -> None:
        required = {
            "guest_business",
            "account_ephemeral",
            "account_saved",
            "acked_outbox",
            "risk_event",
            "audit_log",
            "encrypted_backup",
            "deletion_tombstone",
        }
        assert set(RETENTION_POLICIES.keys()) == required

    def test_guest_business_24h(self) -> None:
        p = RETENTION_POLICIES["guest_business"]
        assert p.max_age == timedelta(hours=24)

    def test_account_saved_infinite(self) -> None:
        p = RETENTION_POLICIES["account_saved"]
        assert p.max_age == timedelta.max

    def test_risk_event_30d(self) -> None:
        p = RETENTION_POLICIES["risk_event"]
        assert p.max_age == timedelta(days=30)

    def test_audit_log_90d(self) -> None:
        p = RETENTION_POLICIES["audit_log"]
        assert p.max_age == timedelta(days=90)

    def test_acked_outbox_7d(self) -> None:
        p = RETENTION_POLICIES["acked_outbox"]
        assert p.max_age == timedelta(days=7)

    def test_deletion_tombstone_30d(self) -> None:
        p = RETENTION_POLICIES["deletion_tombstone"]
        assert p.max_age == timedelta(days=30)


class TestRetentionCalculator:
    def test_expires_at_for_24h_policy(self) -> None:
        frozen = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
        clock = FrozenClock(frozen)
        calc = RetentionCalculator(clock)
        deadline = calc.expires_at("guest_business")
        assert deadline is not None
        expected = int((frozen + timedelta(hours=24)).timestamp())
        assert deadline == expected

    def test_infinite_policy_returns_none(self) -> None:
        clock = FrozenClock(datetime.now(timezone.utc))
        calc = RetentionCalculator(clock)
        assert calc.expires_at("account_saved") is None

    def test_unknown_policy_returns_none(self) -> None:
        clock = FrozenClock(datetime.now(timezone.utc))
        calc = RetentionCalculator(clock)
        assert calc.expires_at("nonexistent") is None
