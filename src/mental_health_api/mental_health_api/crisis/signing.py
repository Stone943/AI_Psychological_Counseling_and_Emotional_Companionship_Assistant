# ruff: noqa: TC003
"""Ed25519 signing and verification for crisis offline bundles."""

from __future__ import annotations

import base64
import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from mental_health_api.crisis.jcs import canonicalize

SIGNED_FIELDS = frozenset({"sha256", "signature"})
BUNDLE_FIELDS = frozenset(
    {
        "signature_alg",
        "canonicalization",
        "key_id",
        "resource_status",
        "degraded_reason",
        "bundle_version",
        "verified_at",
        "expires_at",
        "resources",
        "sha256",
        "signature",
    }
)
KEY_FIELDS = frozenset({"key_id", "public_key", "not_before", "not_after", "status", "revoked_at"})


def unsigned_object(bundle: dict[str, Any]) -> dict[str, Any]:
    """Copy a bundle and remove the two derived signing fields."""
    result = deepcopy(bundle)
    for field in SIGNED_FIELDS:
        result.pop(field, None)
    return result


def sign_bundle(bundle: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str) -> dict[str, Any]:
    unsigned = unsigned_object(bundle)
    unsigned["signature_alg"] = "Ed25519"
    unsigned["canonicalization"] = "RFC8785-JCS"
    unsigned["key_id"] = key_id
    payload = canonicalize(unsigned)
    signature = private_key.sign(payload)
    return {
        **unsigned,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "signature": _b64url_encode(signature),
    }


def verify_bundle(bundle: dict[str, Any], public_key: Ed25519PublicKey) -> bool:
    try:
        if bundle.get("signature_alg") != "Ed25519" or bundle.get("canonicalization") != "RFC8785-JCS":
            return False
        payload = canonicalize(unsigned_object(bundle))
        if not _constant_hash_equal(bundle.get("sha256"), hashlib.sha256(payload).hexdigest()):
            return False
        public_key.verify(_b64url_decode(bundle["signature"]), payload)
        return True
    except (InvalidSignature, KeyError, TypeError, ValueError):
        return False


def verify_trusted_bundle(
    bundle: dict[str, Any], registry: dict[str, Any], *, now: datetime | None = None
) -> tuple[bool, str | None]:
    """Validate schema, checksum/signature, key state, expiry and baseline resources."""
    clock = now or datetime.now(UTC)
    try:
        if not isinstance(bundle, dict) or not isinstance(registry, dict):
            return False, "checksum_failed"
        if clock.tzinfo is None or set(bundle) != BUNDLE_FIELDS:
            return False, "checksum_failed"
        if bundle["resource_status"] != "active" or bundle["degraded_reason"] is not None:
            return False, "checksum_failed"
        if not isinstance(bundle["resources"], list):
            return False, "checksum_failed"
        numbers = {str(row.get("number")) for row in bundle["resources"] if isinstance(row, dict)}
        if not {"110", "120", "12356"}.issubset(numbers):
            return False, "checksum_failed"
        verified_at = _parse_utc(bundle["verified_at"])
        expires_at = _parse_utc(bundle["expires_at"])
        if verified_at > clock or clock >= expires_at:
            return False, "expired"
        keys = registry.get("keys")
        if not isinstance(keys, list):
            return False, "signature_failed"
        matches = [row for row in keys if isinstance(row, dict) and row.get("key_id") == bundle["key_id"]]
        if len(matches) != 1 or set(matches[0]) != KEY_FIELDS:
            return False, "signature_failed"
        key_row = matches[0]
        if key_row["status"] != "active" or key_row["revoked_at"] is not None:
            return False, "signature_failed"
        if not (_parse_utc(key_row["not_before"]) <= clock < _parse_utc(key_row["not_after"])):
            return False, "signature_failed"
        if not verify_bundle(bundle, public_key_from_b64(key_row["public_key"])):
            return False, "signature_failed"
        return True, None
    except (KeyError, TypeError, ValueError):
        return False, "checksum_failed"


def load_private_key(path: Path) -> Ed25519PrivateKey:
    """Load a raw 32-byte seed or PKCS8 PEM from an external secret file."""
    raw = path.read_bytes()
    if len(raw) == 32:
        return Ed25519PrivateKey.from_private_bytes(raw)
    key = serialization.load_pem_private_key(raw, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("crisis signing key is not Ed25519")
    return key


def public_key_b64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return _b64url_encode(raw)


def public_key_from_b64(value: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(_b64url_decode(value))


def private_seed(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    if "=" in value:
        raise ValueError("padding is forbidden")
    padding = "=" * (-len(value) % 4)
    return base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)


def _constant_hash_equal(actual: Any, expected: str) -> bool:
    import hmac

    return isinstance(actual, str) and hmac.compare_digest(actual, expected)


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)
