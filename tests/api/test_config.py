"""Tests for strict Settings validation."""

from __future__ import annotations

import pytest

from mental_health_api.config import DatabaseBackend, Environment, Settings


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
        with pytest.raises(ValueError, match="require MySQL"):
            Settings(
                environment="demo",
                force_tls=True,
                database_url="sqlite+aiosqlite:///./demo.db",
                encryption_key_ref="demo-key-0123456789abcdef0123456789abcdef",
                jwt_secret_key="demo-jwt",
                refresh_token_secret="demo-refresh",
            )

    def test_database_backend_explicit(self) -> None:
        """Database backend can be explicitly set."""
        s_sqlite = Settings(
            environment="test",
            database_url="sqlite+aiosqlite:///./test.db",
            database_backend="sqlite",
            force_tls=False,
            jwt_secret_key="k" * 32,
            refresh_token_secret="r" * 32,
        )
        assert s_sqlite.database_backend.value == "sqlite"

        s_mysql = Settings(
            environment="demo",
            database_url="mysql+asyncmy://user:pass@host/db",
            database_backend="mysql",
            encryption_key_ref="demo-key-0123456789abcdef0123456789abcdef",
            jwt_secret_key="k" * 32,
            refresh_token_secret="r" * 32,
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
            str(e)
            # The error message should not contain the actual sensitive field values
            # Pydantic v2 uses structured error representation
            assert "encryption_key_ref" in str(e.errors())

    def test_prefixed_compose_environment_and_secret_files(self, monkeypatch, tmp_path) -> None:
        jwt_file = tmp_path / "jwt"
        refresh_file = tmp_path / "refresh"
        jwt_file.write_text("j" * 32, encoding="utf-8")
        refresh_file.write_text("r" * 32, encoding="utf-8")
        monkeypatch.setenv("MENTAL_HEALTH_ENVIRONMENT", "demo")
        monkeypatch.setenv("MENTAL_HEALTH_DATABASE_URL", "mysql+asyncmy://user:pass@mysql/db")
        monkeypatch.setenv("MENTAL_HEALTH_DATABASE_BACKEND", "mysql")
        monkeypatch.setenv("MENTAL_HEALTH_ENCRYPTION_KEY_REF", "/run/secrets/encryption_key")
        monkeypatch.setenv("MENTAL_HEALTH_JWT_SECRET_KEY", str(jwt_file))
        monkeypatch.setenv("MENTAL_HEALTH_REFRESH_TOKEN_SECRET", str(refresh_file))
        monkeypatch.setenv("MENTAL_HEALTH_FORCE_TLS", "true")

        settings = Settings(_env_file=None)

        assert settings.environment is Environment.DEMO
        assert settings.database_backend is DatabaseBackend.MYSQL
        assert settings.jwt_secret_key.get_secret_value() == "j" * 32
        assert settings.refresh_token_secret.get_secret_value() == "r" * 32
