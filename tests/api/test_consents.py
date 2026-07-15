# ruff: noqa: E501
"""B-04: Consent API tests — must fail before implementation."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError
from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from mental_health_api.app import create_app
from mental_health_api.config import Settings
from mental_health_api.consents.contracts import ConsentSnapshot, ConsentStatus, ConsentType
from mental_health_api.contracts.models import (
    ConsentSnapshot as PublicConsentSnapshot,
)
from mental_health_api.contracts.models import (
    FreeTextSafetyResult,
)
from mental_health_api.contracts.models import (
    ProviderProcessingPolicySnapshot as PublicProviderPolicySnapshot,
)


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

        with pytest.raises(ValueError):
            ConsentSnapshot(
                subject_id="s",
                consent_type=ConsentType.cloud_model_processing,
                policy_version=1,
                consent_version=0,
                status=ConsentStatus.missing,
                granted_at=datetime.now(UTC),
            )

    def test_granted_without_granted_at_raises(self) -> None:
        with pytest.raises(ValueError):
            ConsentSnapshot(
                subject_id="s",
                consent_type=ConsentType.cloud_model_processing,
                policy_version=1,
                consent_version=1,
                status=ConsentStatus.granted,
                granted_at=None,
            )

    def test_consent_invariants_survive_python_optimized_mode(self) -> None:
        code = """
from mental_health_api.consents.contracts import ConsentSnapshot, ConsentStatus, ConsentType
try:
    ConsentSnapshot('s', ConsentType.cloud_model_processing, 1, 0, ConsentStatus.granted)
except ValueError:
    raise SystemExit(0)
raise SystemExit(1)
"""
        result = subprocess.run([sys.executable, "-O", "-c", code], check=False)
        assert result.returncode == 0

    def test_snapshot_rejects_unknown_type_status_and_mutation(self) -> None:
        snap = ConsentSnapshot(
            subject_id="s",
            consent_type=ConsentType.cloud_model_processing,
            policy_version=1,
            consent_version=0,
            status=ConsentStatus.missing,
        )
        with pytest.raises(FrozenInstanceError):
            snap.status = ConsentStatus.withdrawn  # type: ignore[misc]
        with pytest.raises(ValueError, match="cloud_model_processing"):
            ConsentSnapshot("s", ConsentType.memory, 1, 0, ConsentStatus.missing)
        with pytest.raises(ValueError, match="frozen ConsentStatus"):
            ConsentSnapshot("s", ConsentType.cloud_model_processing, 1, 0, "unknown")  # type: ignore[arg-type]

    def test_public_consent_is_discriminated_and_frozen(self) -> None:
        from datetime import datetime

        snap = PublicConsentSnapshot(
            subject_id="s",
            consent_type="cloud_model_processing",
            policy_version=1,
            consent_version=0,
            status="missing",
            loaded_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError):
            snap.status = "withdrawn"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            PublicConsentSnapshot(
                subject_id="s",
                consent_type="cloud_model_processing",
                policy_version=1,
                consent_version=999,
                status="missing",
                granted_at=datetime.now(UTC),
                loaded_at=datetime.now(UTC),
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
            matrix_sha256="a" * 64,
            processor_contract_ref="contract-ref",
            independent_review_ref="review-ref",
            data_region="CN-mainland",
            cross_border_status=CrossBorderStatus.approved,
            approved_at=now,
            review_expires_at=future,
        )
        assert snap.is_approved()

    @pytest.mark.parametrize(
        ("changes", "message"),
        [
            ({"policy_version": 0}, "identity/version"),
            ({"matrix_sha256": None}, "approval evidence"),
            ({"matrix_sha256": "short"}, "approval evidence"),
            ({"data_region": ""}, "approval evidence"),
            ({"review_expires_at": None}, "approval evidence"),
        ],
    )
    def test_approved_policy_rejects_incomplete_evidence(self, changes: dict, message: str) -> None:
        from datetime import datetime, timedelta

        from mental_health_api.provider_policy.contracts import (
            CrossBorderStatus,
            ProviderPolicyStatus,
            ProviderProcessingPolicySnapshot,
        )

        now = datetime.now(UTC)
        values = {
            "provider_id": "provider",
            "policy_version": 1,
            "status": ProviderPolicyStatus.approved,
            "matrix_sha256": "a" * 64,
            "processor_contract_ref": "contract-ref",
            "independent_review_ref": "review-ref",
            "data_region": "CN-mainland",
            "cross_border_status": CrossBorderStatus.approved,
            "approved_at": now,
            "review_expires_at": now + timedelta(days=1),
            "loaded_at": now,
        }
        values.update(changes)
        with pytest.raises(ValueError, match=message):
            ProviderProcessingPolicySnapshot(**values)

    def test_provider_snapshot_is_frozen(self) -> None:
        from mental_health_api.provider_policy.contracts import ProviderPolicyStatus, ProviderProcessingPolicySnapshot

        snap = ProviderProcessingPolicySnapshot(provider_id="p")
        with pytest.raises(FrozenInstanceError):
            snap.status = ProviderPolicyStatus.approved  # type: ignore[misc]

    def test_expired_policy_preserves_evidence_but_blocks_processing(self) -> None:
        from datetime import datetime, timedelta

        from mental_health_api.provider_policy.contracts import (
            CrossBorderStatus,
            ProviderPolicyStatus,
            ProviderProcessingPolicySnapshot,
        )

        now = datetime.now(UTC)
        snap = ProviderProcessingPolicySnapshot(
            provider_id="p",
            status=ProviderPolicyStatus.expired,
            matrix_sha256="a" * 64,
            processor_contract_ref="contract-ref",
            independent_review_ref="review-ref",
            data_region="CN-mainland",
            cross_border_status=CrossBorderStatus.blocked,
            approved_at=now - timedelta(days=30),
            review_expires_at=now - timedelta(days=1),
            loaded_at=now,
        )
        assert not snap.is_approved()

    def test_public_provider_policy_rejects_unbound_approval(self) -> None:
        from datetime import datetime

        with pytest.raises(ValidationError):
            PublicProviderPolicySnapshot(
                provider_id="p",
                policy_version=1,
                status="approved",
                loaded_at=datetime.now(UTC),
            )


class TestPublicSafetyResult:
    def test_block_cannot_carry_allow_proof(self) -> None:
        with pytest.raises(ValidationError):
            FreeTextSafetyResult(
                decision="block",
                screening_decision_id="allow-proof",
                risk_decision="L3",
                safe_template_id="urgent-support",
                safety_action_ids=["call_110"],
            )

    def test_valid_block_has_no_decision_id(self) -> None:
        result = FreeTextSafetyResult(
            decision="block",
            risk_decision="L3",
            safe_template_id="urgent-support",
            safety_action_ids=["call_110"],
        )
        assert result.screening_decision_id is None
