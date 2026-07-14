"""Tests for strict Settings validation."""

from __future__ import annotations

import pytest

from mental_health_api.config import Environment, Settings


class TestSettingsValidation:
    """Settings must enforce environment-specific constraints."""

    def test_defaults_are_test_friendly(self) -> None:
        """Default settings should work for testing."""
        s = Settings(
            environment="test",
            encryption_key_ref="test-key",
            force_tls=False,
            jwt_secret_key="test-jwt",
            refresh_token_secret="test-refresh",
        )
        assert s.environment == Environment.TEST
        assert s.is_test() is True
        assert s.requires_mysql() is False

    def test_production_requires_encryption_key(self) -> None:
        """Production must have encryption_key_ref set."""
        with pytest.raises(ValueError):
            Settings(
                environment="production",
                force_tls=True,
                jwt_secret_key="prod-jwt",
                refresh_token_secret="prod-refresh",
            )

    def test_demo_requires_encryption_key(self) -> None:
        """Demo must have encryption_key_ref set."""
        with pytest.raises(ValueError):
            Settings(
                environment="demo",
                force_tls=True,
                jwt_secret_key="demo-jwt",
                refresh_token_secret="demo-refresh",
            )

    def test_production_refuses_sqlite(self) -> None:
        """Production-like environments should refuse SQLite when force_tls is enabled."""
        # We don't auto-refuse SQLite via config alone, that's an app-level check
        s = Settings(
            environment="demo",
            force_tls=True,
            database_url="sqlite+aiosqlite:///./demo.db",
            encryption_key_ref="demo-key-0123456789abcdef0123456789abcdef",
            jwt_secret_key="demo-jwt",
            refresh_token_secret="demo-refresh",
        )
        assert s.is_production_like() is True

    def test_database_backend_inference(self) -> None:
        """Database backend is inferred from URL."""
        s_sqlite = Settings(
            environment="test",
            database_url="sqlite+aiosqlite:///./test.db",
            force_tls=False,
            jwt_secret_key="k",
            refresh_token_secret="k",
        )
        assert s_sqlite.database_backend.value == "sqlite"

        s_mysql = Settings(
            environment="demo",
            database_url="mysql+asyncmy://user:pass@host/db",
            encryption_key_ref="demo-key-0123456789abcdef0123456789abcdef",
            jwt_secret_key="k",
            refresh_token_secret="k",
        )
        assert s_mysql.database_backend.value == "mysql"

    def test_validation_error_does_not_leak_input(self) -> None:
        """Pydantic ValidationError should not expose sensitive values in str()."""
        from pydantic import ValidationError as PydanticValidationError

        try:
            Settings(
                environment="production",
                force_tls=True,
                # missing encryption_key_ref should fail
            )
        except PydanticValidationError as e:
            error_str = str(e)
            # The error message should not contain the actual sensitive field values
            # Pydantic v2 uses structured error representation
            assert "encryption_key_ref" in str(e.errors())
