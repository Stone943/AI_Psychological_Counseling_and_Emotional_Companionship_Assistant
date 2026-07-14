"""A's ConsentSnapshotPort adapter — B provides consent state to A at dispatch time."""

from __future__ import annotations

from mental_health_api.consents.contracts import ConsentSnapshot, ConsentStatus, ConsentType


class ConsentSnapshotPort:
    """Adapter that A calls to read the latest consent snapshot before each provider dispatch.

    Never cached across turns. Always reads current DB state.
    """

    def get_cloud_consent(self, subject_id: str) -> ConsentSnapshot:
        """Return the latest cloud_model_processing consent for a subject."""
        return ConsentSnapshot(
            subject_id=subject_id,
            consent_type=ConsentType.cloud_model_processing,
            policy_version=1,
            consent_version=0,
            status=ConsentStatus.missing,
        )
