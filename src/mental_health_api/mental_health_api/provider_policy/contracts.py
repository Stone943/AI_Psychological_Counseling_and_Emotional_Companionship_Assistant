"""ProviderProcessingPolicySnapshot DTO — per PRD 10.4."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum


class ProviderPolicyStatus(str, Enum):
    disabled = "disabled"
    approved = "approved"
    expired = "expired"


class CrossBorderStatus(str, Enum):
    not_applicable = "not_applicable"
    approved = "approved"
    blocked = "blocked"


class ProviderProcessingPolicySnapshot:
    """Immutable snapshot of organizational provider processing policy.

    Default: disabled with all approval references null, cross_border blocked.
    Only B-16 can create approved snapshots after independent review.
    """

    def __init__(
        self,
        provider_id: str,
        policy_version: int = 1,
        status: ProviderPolicyStatus | None = None,
        matrix_sha256: str | None = None,
        processor_contract_ref: str | None = None,
        independent_review_ref: str | None = None,
        data_region: str = "",
        cross_border_status: CrossBorderStatus | None = None,
        approved_at: datetime | None = None,
        review_expires_at: datetime | None = None,
        loaded_at: datetime | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.policy_version = policy_version
        self.status = status or ProviderPolicyStatus.disabled
        self.matrix_sha256 = matrix_sha256
        self.processor_contract_ref = processor_contract_ref
        self.independent_review_ref = independent_review_ref
        self.data_region = data_region
        self.cross_border_status = cross_border_status or CrossBorderStatus.blocked
        self.approved_at = approved_at
        self.review_expires_at = review_expires_at
        self.loaded_at = loaded_at or datetime.now(UTC)

    def is_approved(self) -> bool:
        """Check if policy is currently approved and not expired."""
        if self.status != ProviderPolicyStatus.approved:
            return False
        if self.cross_border_status == CrossBorderStatus.blocked:
            return False
        if self.review_expires_at and self.loaded_at >= self.review_expires_at:
            return False
        return bool(self.approved_at and self.processor_contract_ref and self.independent_review_ref)

    def to_dict(self) -> dict:
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
