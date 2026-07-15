# ruff: noqa: E501
"""B-04: Consent API tests — must fail before implementation."""

from __future__ import annotations

from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient

from mental_health_api.app import create_app
from mental_health_api.config import Settings
from mental_health_api.consents.contracts import ConsentSnapshot, ConsentStatus, ConsentType


class TestConsentSnapshot:
    def test_missing_consent(self) -> None:
        snap = ConsentSnapshot(
            subject_id="subj-1",
            consent_type=ConsentType.cloud_model_processing,
            policy_version=1,
            consent_version=0,
            status=ConsentStatus.missing,
        )
        assert snap.consent_version == 0
        assert snap.granted_at is None
        assert snap.withdrawn_at is None

    def test_granted_consent(self) -> None:
        from datetime import datetime

        now = datetime.now(UTC)
        snap = ConsentSnapshot(
            subject_id="subj-1",
            consent_type=ConsentType.cloud_model_processing,
            policy_version=1,
            consent_version=1,
            status=ConsentStatus.granted,
            granted_at=now,
        )
        assert snap.consent_version == 1
        assert snap.granted_at is not None
        assert snap.withdrawn_at is None

    def test_withdrawn_consent(self) -> None:
        from datetime import datetime

        now = datetime.now(UTC)
        snap = ConsentSnapshot(
            subject_id="subj-1",
            consent_type=ConsentType.cloud_model_processing,
            policy_version=1,
            consent_version=2,
            status=ConsentStatus.withdrawn,
            granted_at=now,
            withdrawn_at=now,
        )
        assert snap.withdrawn_at is not None

    def test_missing_with_granted_at_raises(self) -> None:
        from datetime import datetime

        with pytest.raises(AssertionError):
            ConsentSnapshot(
                subject_id="s",
                consent_type=ConsentType.cloud_model_processing,
                policy_version=1,
                consent_version=0,
                status=ConsentStatus.missing,
                granted_at=datetime.now(UTC),
            )

    def test_granted_without_granted_at_raises(self) -> None:
        with pytest.raises(AssertionError):
            ConsentSnapshot(
                subject_id="s",
                consent_type=ConsentType.cloud_model_processing,
                policy_version=1,
                consent_version=1,
                status=ConsentStatus.granted,
                granted_at=None,
            )


class TestConsentAPI:
    @pytest.fixture
    def app(self):
        settings = Settings(
            environment="test",
            force_tls=False,
            jwt_secret_key="k",
            refresh_token_secret="r",
            database_url="sqlite+aiosqlite:///./test.db",
        )
        return create_app(settings)

    @pytest.mark.asyncio
    async def test_list_consents_requires_auth(self, app) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/consents")
            assert resp.status_code == 401


class TestProviderPolicy:
    def test_default_disabled(self) -> None:
        from mental_health_api.provider_policy.contracts import CrossBorderStatus, ProviderProcessingPolicySnapshot

        snap = ProviderProcessingPolicySnapshot(provider_id="test-provider")
        assert snap.status.value == "disabled"
        assert snap.cross_border_status == CrossBorderStatus.blocked
        assert not snap.is_approved()

    def test_approved_requires_all_refs(self) -> None:
        from datetime import datetime

        from mental_health_api.provider_policy.contracts import (
            CrossBorderStatus,
            ProviderPolicyStatus,
            ProviderProcessingPolicySnapshot,
        )

        now = datetime.now(UTC)
        future = datetime(2030, 1, 1, tzinfo=UTC)
        snap = ProviderProcessingPolicySnapshot(
            provider_id="p",
            status=ProviderPolicyStatus.approved,
            matrix_sha256="abc",
            processor_contract_ref="contract-ref",
            independent_review_ref="review-ref",
            cross_border_status=CrossBorderStatus.approved,
            approved_at=now,
            review_expires_at=future,
        )
        assert snap.is_approved()
