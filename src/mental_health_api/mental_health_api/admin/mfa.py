# ruff: noqa: TC001
"""TOTP enrollment, replay protection, and one-time recovery codes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import quote

from mental_health_api.database.encryption import EncryptionService


@dataclass
class AdminMfaRecord:
    admin_id: str
    encrypted_seed: str
    enabled: bool = False
    last_accepted_counter: int = -1
    recovery_code_digests: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Enrollment:
    secret: str
    provisioning_uri: str


class TotpMfaService:
    """MFA domain service; persistence can replace the in-memory record mapping."""

    PERIOD_SECONDS = 30
    DIGITS = 6

    def __init__(self, encryption: EncryptionService, *, recovery_pepper: bytes) -> None:
        if len(recovery_pepper) < 32:
            raise ValueError("recovery pepper must be at least 32 bytes")
        self._encryption = encryption
        self._recovery_pepper = recovery_pepper
        self._records: dict[str, AdminMfaRecord] = {}

    def start_enrollment(self, admin_id: str, account_label: str, *, issuer: str = "MentalHealthDemo") -> Enrollment:
        if not admin_id:
            raise ValueError("admin_id is required")
        if admin_id in self._records:
            raise ValueError("MFA enrollment already exists; rotation requires a separate reauthenticated flow")
        secret = _new_base32_secret()
        encrypted = self._encryption.encrypt_field(secret, "admin", admin_id, "totp_seed")
        self._records[admin_id] = AdminMfaRecord(admin_id=admin_id, encrypted_seed=encrypted)
        uri = f"otpauth://totp/{quote(issuer)}:{quote(account_label)}?secret={secret}&issuer={quote(issuer)}&period=30&digits=6"
        return Enrollment(secret=secret, provisioning_uri=uri)

    def confirm_enrollment(self, admin_id: str, code: str, *, at: datetime | None = None) -> list[str]:
        record = self._record(admin_id)
        counter = self._verify_totp(record, code, at=at, allow_replay=False)
        record.enabled = True
        record.last_accepted_counter = counter
        recovery_codes = [secrets.token_urlsafe(12) for _ in range(10)]
        record.recovery_code_digests = {self._recovery_digest(code) for code in recovery_codes}
        return recovery_codes

    def verify_totp(self, admin_id: str, code: str, *, at: datetime | None = None) -> bool:
        record = self._record(admin_id)
        if not record.enabled:
            return False
        try:
            counter = self._verify_totp(record, code, at=at, allow_replay=False)
        except ValueError:
            return False
        record.last_accepted_counter = counter
        return True

    def use_recovery_code(self, admin_id: str, code: str) -> bool:
        record = self._record(admin_id)
        digest = self._recovery_digest(code)
        match = next((item for item in record.recovery_code_digests if hmac.compare_digest(item, digest)), None)
        if match is None:
            return False
        record.recovery_code_digests.remove(match)
        return True

    def _verify_totp(self, record: AdminMfaRecord, code: str, *, at: datetime | None, allow_replay: bool) -> int:
        if len(code) != self.DIGITS or not code.isdigit():
            raise ValueError("invalid TOTP format")
        now = at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("TOTP clock must be timezone-aware")
        base_counter = int(now.timestamp()) // self.PERIOD_SECONDS
        secret = self._decrypt_seed(record)
        for counter in (base_counter - 1, base_counter, base_counter + 1):
            if (allow_replay or counter > record.last_accepted_counter) and hmac.compare_digest(
                generate_totp(secret, counter), code
            ):
                return counter
        raise ValueError("invalid or replayed TOTP")

    def _decrypt_seed(self, record: AdminMfaRecord) -> str:
        secret = self._encryption.decrypt_field(record.encrypted_seed, "admin", record.admin_id, "totp_seed")
        if secret is None:
            raise ValueError("TOTP seed cannot be decrypted")
        return secret

    def _recovery_digest(self, code: str) -> str:
        return hmac.new(self._recovery_pepper, code.encode("utf-8"), hashlib.sha256).hexdigest()

    def _record(self, admin_id: str) -> AdminMfaRecord:
        try:
            return self._records[admin_id]
        except KeyError as exc:
            raise ValueError("MFA enrollment not found") from exc


def generate_totp(secret: str, counter: int) -> str:
    """Generate RFC 6238 SHA-1 TOTP for an already-derived time counter."""
    padding = "=" * (-len(secret) % 8)
    key = base64.b32decode(secret + padding, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 1_000_000).zfill(6)


def _new_base32_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).rstrip(b"=").decode("ascii")
