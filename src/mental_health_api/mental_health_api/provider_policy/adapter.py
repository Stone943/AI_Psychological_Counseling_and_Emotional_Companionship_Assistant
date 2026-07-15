"""ProviderProcessingPolicyPort adapter — default-disabled skeleton.

Per PRD 10.4: B-04 provides only default-disabled adapter.
Only B-16 can provide approved adapter after independent legal/privacy review.
"""

from __future__ import annotations

from datetime import UTC, datetime

from mental_health_api.provider_policy.contracts import ProviderProcessingPolicySnapshot


class ProviderProcessingPolicyPort:
    """Adapter that A calls before each cloud provider dispatch.

    Default: disabled (all approvals null, cross_border blocked).
    Not promoted by user consent — these are separate gates.
    """

    def get_policy(self, provider_id: str) -> ProviderProcessingPolicySnapshot:
        """Return the current processing policy for a provider.
        Always returns disabled until B-16 configuration is approved.
        """
        return ProviderProcessingPolicySnapshot(
            provider_id=provider_id,
            policy_version=1,
            loaded_at=datetime.now(UTC),
        )
