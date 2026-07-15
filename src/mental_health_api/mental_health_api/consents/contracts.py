"""Frozen consent snapshot consumed by the cloud-model dispatch boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ConsentStatus(StrEnum):
    granted = "granted"
    withdrawn = "withdrawn"
    missing = "missing"


class ConsentType(StrEnum):
    cloud_model_processing = "cloud_model_processing"
    memory = "memory"
    trends = "trends"
    training = "training"


@dataclass(frozen=True)
class ConsentSnapshot:
    """A cloud-dispatch snapshot; other consent types use separate domain records."""

    subject_id: str
    consent_type: ConsentType
    policy_version: int
    consent_version: int
    status: ConsentStatus
    granted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.subject_id:
            raise ValueError("subject_id is required")
        if self.consent_type is not ConsentType.cloud_model_processing:
            raise ValueError("ConsentSnapshotPort only accepts cloud_model_processing")
        if not isinstance(self.status, ConsentStatus):
            raise ValueError("consent status must be a frozen ConsentStatus")
        if isinstance(self.policy_version, bool) or self.policy_version < 1:
            raise ValueError("policy_version must be >=1")
        if isinstance(self.consent_version, bool) or self.consent_version < 0:
            raise ValueError("consent_version must be a non-negative integer")
        for field_name, value in (
            ("granted_at", self.granted_at),
            ("withdrawn_at", self.withdrawn_at),
            ("loaded_at", self.loaded_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)):
                raise ValueError(f"{field_name} must be a UTC timestamp")
        if self.loaded_at > datetime.now(UTC):
            raise ValueError("loaded_at must not be in the future")
        if self.status is ConsentStatus.missing:
            if self.consent_version != 0 or self.granted_at is not None or self.withdrawn_at is not None:
                raise ValueError("missing consent requires version=0 and null timestamps")
        elif self.status is ConsentStatus.granted:
            if (
                self.consent_version < 1
                or self.granted_at is None
                or self.withdrawn_at is not None
                or self.granted_at > self.loaded_at
            ):
                raise ValueError("granted consent requires version>=1, granted_at, and no withdrawn_at")
        elif (
            self.consent_version < 1
            or self.granted_at is None
            or self.withdrawn_at is None
            or self.withdrawn_at < self.granted_at
            or self.withdrawn_at > self.loaded_at
        ):
            raise ValueError("withdrawn consent requires version>=1 and ordered timestamps")

    def to_dict(self) -> dict[str, object]:
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
