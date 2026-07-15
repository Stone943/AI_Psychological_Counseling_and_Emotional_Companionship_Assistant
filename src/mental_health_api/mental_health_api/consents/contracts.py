"""Consent contracts — ConsentSnapshot DTOs for A's ConsentSnapshotPort."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum


class ConsentStatus(str, Enum):
    granted = "granted"
    withdrawn = "withdrawn"
    missing = "missing"


class ConsentType(str, Enum):
    cloud_model_processing = "cloud_model_processing"
    memory = "memory"
    trends = "trends"
    training = "training"


class ConsentSnapshot:
    """Immutable snapshot of a user's consent state at a point in time.

    Invariants (per PRD 10.4):
    - missing: consent_version=0, granted_at=null, withdrawn_at=null
    - granted: consent_version>=1, granted_at non-null, withdrawn_at=null
    - withdrawn: consent_version>=1, both times non-null, withdrawn_at >= granted_at
    """

    def __init__(
        self,
        subject_id: str,
        consent_type: ConsentType,
        policy_version: int,
        consent_version: int,
        status: ConsentStatus,
        granted_at: datetime | None = None,
        withdrawn_at: datetime | None = None,
    ) -> None:
        self.subject_id = subject_id
        self.consent_type = consent_type
        self.policy_version = policy_version
        self.consent_version = consent_version
        self.status = status
        self.granted_at = granted_at
        self.withdrawn_at = withdrawn_at
        self.loaded_at = datetime.now(UTC)

        self._validate()

    def _validate(self) -> None:
        if self.status == ConsentStatus.missing:
            assert self.consent_version == 0, "missing consent must have version=0"
            assert self.granted_at is None, "missing consent must have granted_at=null"
            assert self.withdrawn_at is None, "missing consent must have withdrawn_at=null"
        elif self.status == ConsentStatus.granted:
            assert self.consent_version >= 1, "granted consent must have version>=1"
            assert self.granted_at is not None, "granted consent must have granted_at"
            assert self.withdrawn_at is None, "granted consent must have withdrawn_at=null"
        elif self.status == ConsentStatus.withdrawn:
            assert self.consent_version >= 1, "withdrawn consent must have version>=1"
            assert self.granted_at is not None, "withdrawn consent must have granted_at"
            assert self.withdrawn_at is not None, "withdrawn consent must have withdrawn_at"
            assert self.withdrawn_at >= self.granted_at, "withdrawn_at must be >= granted_at"

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "consent_type": self.consent_type.value,
            "policy_version": self.policy_version,
            "consent_version": self.consent_version,
            "status": self.status.value,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "loaded_at": self.loaded_at.isoformat(),
        }
