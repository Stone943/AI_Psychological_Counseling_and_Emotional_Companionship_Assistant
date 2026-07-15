"""Frozen organizational provider-processing policy snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProviderPolicyStatus(StrEnum):
    disabled = "disabled"
    approved = "approved"
    expired = "expired"


class CrossBorderStatus(StrEnum):
    not_applicable = "not_applicable"
    approved = "approved"
    blocked = "blocked"


@dataclass(frozen=True)
class ProviderProcessingPolicySnapshot:
    provider_id: str
    policy_version: int = 1
    status: ProviderPolicyStatus = ProviderPolicyStatus.disabled
    matrix_sha256: str | None = None
    processor_contract_ref: str | None = None
    independent_review_ref: str | None = None
    data_region: str = ""
    cross_border_status: CrossBorderStatus = CrossBorderStatus.blocked
    approved_at: datetime | None = None
    review_expires_at: datetime | None = None
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.provider_id or isinstance(self.policy_version, bool) or self.policy_version < 1:
            raise ValueError("provider policy identity/version is invalid")
        if not isinstance(self.status, ProviderPolicyStatus) or not isinstance(
            self.cross_border_status, CrossBorderStatus
        ):
            raise ValueError("provider policy status values must use frozen enums")
        for field_name, value in (
            ("approved_at", self.approved_at),
            ("review_expires_at", self.review_expires_at),
            ("loaded_at", self.loaded_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)):
                raise ValueError(f"{field_name} must be a UTC timestamp")
        if self.status is ProviderPolicyStatus.disabled:
            if (
                any(
                    value is not None
                    for value in (
                        self.matrix_sha256,
                        self.processor_contract_ref,
                        self.independent_review_ref,
                        self.approved_at,
                        self.review_expires_at,
                    )
                )
                or self.data_region
                or self.cross_border_status is not CrossBorderStatus.blocked
            ):
                raise ValueError("disabled provider policy must not contain approval evidence")
            return
        approval_evidence_invalid = (
            not isinstance(self.matrix_sha256, str)
            or SHA256_PATTERN.fullmatch(self.matrix_sha256) is None
            or not self.processor_contract_ref
            or not self.independent_review_ref
            or not self.data_region
            or self.approved_at is None
            or self.review_expires_at is None
            or self.approved_at > self.loaded_at
            or self.approved_at >= self.review_expires_at
        )
        if approval_evidence_invalid:
            raise ValueError("provider policy approval evidence is invalid")
        review_expires_at = cast("datetime", self.review_expires_at)
        if self.status is ProviderPolicyStatus.approved:
            if self.cross_border_status is CrossBorderStatus.blocked or self.loaded_at >= review_expires_at:
                raise ValueError("approved provider policy is blocked or expired")
        elif self.cross_border_status is not CrossBorderStatus.blocked or self.loaded_at < review_expires_at:
            raise ValueError("expired provider policy must be past its deadline and block cross-border processing")

    def is_approved(self) -> bool:
        return self.status is ProviderPolicyStatus.approved

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "policy_version": self.policy_version,
            "status": self.status.value,
            "matrix_sha256": self.matrix_sha256,
            "processor_contract_ref": self.processor_contract_ref,
            "independent_review_ref": self.independent_review_ref,
            "data_region": self.data_region,
            "cross_border_status": self.cross_border_status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "review_expires_at": self.review_expires_at.isoformat() if self.review_expires_at else None,
            "loaded_at": self.loaded_at.isoformat(),
        }
