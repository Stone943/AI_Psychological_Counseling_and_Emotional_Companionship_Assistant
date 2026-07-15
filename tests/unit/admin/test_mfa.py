from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mental_health_api.admin.mfa import TotpMfaService, generate_totp
from mental_health_api.database.encryption import EncryptionService


def test_totp_enrollment_replay_and_recovery_code() -> None:
    service = TotpMfaService(EncryptionService(b"e" * 32), recovery_pepper=b"r" * 32)
    enrollment = service.start_enrollment("admin-1", "admin@example.invalid")
    now = datetime(2026, 7, 15, tzinfo=UTC)
    counter = int(now.timestamp()) // service.PERIOD_SECONDS
    code = generate_totp(enrollment.secret, counter)
    recovery_codes = service.confirm_enrollment("admin-1", code, at=now)
    assert not service.verify_totp("admin-1", code, at=now)
    assert service.use_recovery_code("admin-1", recovery_codes[0])
    assert not service.use_recovery_code("admin-1", recovery_codes[0])
    with pytest.raises(ValueError, match="already exists"):
        service.start_enrollment("admin-1", "admin@example.invalid")
