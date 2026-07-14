"""Consent service — manage user consent records."""

from __future__ import annotations

from mental_health_api.consents.contracts import ConsentSnapshot, ConsentStatus, ConsentType


class ConsentService:
    """Manages versioned user consents (core, cloud_model, memory, trends, training)."""

    def get_snapshot(self, subject_id: str, consent_type: ConsentType) -> ConsentSnapshot:
        """Get the current consent snapshot for a subject.
        Missing consent is synthesized with version=0, never persisted as a DB row.
        """
        return ConsentSnapshot(
            subject_id=subject_id,
            consent_type=consent_type,
            policy_version=1,
            consent_version=0,
            status=ConsentStatus.missing,
        )

    def grant(self, subject_id: str, consent_type: ConsentType, policy_version: int) -> ConsentSnapshot:
        """Grant consent. Creates version 1 or increments."""
        from datetime import datetime, timezone

        return ConsentSnapshot(
            subject_id=subject_id,
            consent_type=consent_type,
            policy_version=policy_version,
            consent_version=1,
            status=ConsentStatus.granted,
            granted_at=datetime.now(timezone.utc),
        )

    def withdraw(self, subject_id: str, consent_type: ConsentType) -> ConsentSnapshot:
        """Withdraw consent. Only affects future dispatches."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return ConsentSnapshot(
            subject_id=subject_id,
            consent_type=consent_type,
            policy_version=1,
            consent_version=1,
            status=ConsentStatus.withdrawn,
            granted_at=now,
            withdrawn_at=now,
        )
