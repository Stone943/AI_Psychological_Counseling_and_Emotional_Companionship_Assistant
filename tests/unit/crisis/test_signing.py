from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mental_health_api.crisis.signing import (
    public_key_b64,
    sign_bundle,
    unsigned_object,
    verify_bundle,
    verify_trusted_bundle,
)


def test_ed25519_bundle_round_trip_and_tamper_rejection() -> None:
    key = Ed25519PrivateKey.generate()
    bundle = sign_bundle(
        {"bundle_version": "v1", "resources": [{"number": "110"}], "sha256": "old", "signature": "old"},
        key,
        key_id="demo-key",
    )
    assert verify_bundle(bundle, key.public_key())
    assert "sha256" not in unsigned_object(bundle)
    assert "signature" not in unsigned_object(bundle)
    tampered = {**bundle, "bundle_version": "v2"}
    assert not verify_bundle(tampered, key.public_key())
    assert "=" not in bundle["signature"]


def test_trusted_bundle_rejects_expired_or_revoked_key() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    key = Ed25519PrivateKey.generate()
    unsigned = {
        "resource_status": "active",
        "degraded_reason": None,
        "bundle_version": "v1",
        "verified_at": (now - timedelta(days=1)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "resources": [{"number": number} for number in ("110", "120", "12356")],
    }
    bundle = sign_bundle(unsigned, key, key_id="demo-key")
    key_row = {
        "key_id": "demo-key",
        "public_key": public_key_b64(key.public_key()),
        "status": "active",
        "not_before": (now - timedelta(days=1)).isoformat(),
        "not_after": (now + timedelta(days=1)).isoformat(),
        "revoked_at": None,
    }
    assert verify_trusted_bundle(bundle, {"keys": [key_row]}, now=now) == (True, None)
    assert verify_trusted_bundle(bundle, {"keys": [{**key_row, "revoked_at": now.isoformat()}]}, now=now) == (
        False,
        "signature_failed",
    )
    assert verify_trusted_bundle(bundle, {"keys": [key_row]}, now=now + timedelta(days=2)) == (False, "expired")
