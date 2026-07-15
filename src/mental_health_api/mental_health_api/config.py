"""Strict Settings for mental_health_api.

Production/demo deployments require MySQL, HTTPS/WSS, and external secrets.
Test environment allows SQLite and HTTP.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    TEST = "test"
    DEVELOPMENT = "development"
    DEMO = "demo"
    PRODUCTION = "production"


class DatabaseBackend(StrEnum):
    """Supported database backends."""

    SQLITE = "sqlite"
    MYSQL = "mysql"


class Settings(BaseSettings):
    """Application-wide settings with strict validation.

    Test environment allows SQLite; demo/production require MySQL + https/wss.
    """

    model_config = SettingsConfigDict(
        env_prefix="MENTAL_HEALTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        hide_input_in_errors=True,
    )

    # --- Environment ---
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)

    # --- Server ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # --- Database ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./mental_health.db",
        description="Async database URL. Production must use MySQL.",
    )
    database_url_file: Path | None = Field(
        default=None,
        description="Docker-secret file containing the complete async database URL.",
    )
    database_backend: DatabaseBackend = Field(default=DatabaseBackend.SQLITE)
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_recycle_seconds: int = Field(default=1800, ge=30)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    safety_dependency_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    ai_turn_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    @field_validator("database_backend", mode="before")
    @classmethod
    def _infer_backend(cls, v: str | None, info: ValidationInfo) -> DatabaseBackend:
        if v is not None:
            return DatabaseBackend(v)
        # In Pydantic v2 "before" mode, info.data only contains fields
        # that have already been validated. database_url may not be available.
        # Fallback: always default to SQLITE unless explicitly set.
        return DatabaseBackend.SQLITE

    @model_validator(mode="after")
    def _validate_database_environment(self) -> Settings:
        if self.database_url_file is not None:
            if not self.database_url_file.is_absolute() or not self.database_url_file.is_file():
                raise ValueError("database_url_file must be an available absolute secret path")
            database_url = self.database_url_file.read_text(encoding="utf-8").strip()
            if not database_url:
                raise ValueError("database_url_file is empty")
            self.database_url = database_url
        is_sqlite_url = self.database_url.startswith("sqlite+")
        is_mysql_url = self.database_url.startswith("mysql+asyncmy://")
        if self.database_backend == DatabaseBackend.SQLITE and not is_sqlite_url:
            raise ValueError("database_backend=sqlite requires a sqlite async URL")
        if self.database_backend == DatabaseBackend.MYSQL and not is_mysql_url:
            raise ValueError("database_backend=mysql requires mysql+asyncmy")
        if self.is_production_like() and self.database_backend != DatabaseBackend.MYSQL:
            raise ValueError("demo/production require MySQL")
        if self.is_production_like() and self.database_url_file is None:
            raise ValueError("demo/production database URL must come from database_url_file")
        if self.is_production_like():
            encryption_path = Path(self.encryption_key_ref)
            if (
                not encryption_path.is_absolute()
                or encryption_path == Path("/dev/null")
                or not encryption_path.is_file()
            ):
                raise ValueError("demo/production encryption_key_ref must be an available absolute file")
            raw_key = encryption_path.read_bytes().strip()
            if len(raw_key) == 64:
                try:
                    raw_key = bytes.fromhex(raw_key.decode("ascii"))
                except (UnicodeDecodeError, ValueError) as exc:
                    raise ValueError("encryption key must be 32 raw bytes or 64 lowercase hex characters") from exc
            if len(raw_key) != 32:
                raise ValueError("encryption key must decode to exactly 32 bytes")
        if self.is_production_like() and (
            len(self.jwt_secret_key.get_secret_value()) < 32 or len(self.refresh_token_secret.get_secret_value()) < 32
        ):
            raise ValueError("demo/production token secrets must contain at least 32 characters")
        return self

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- Encryption ---
    encryption_key_ref: str = Field(
        default="",
        description="Path to encryption key file or env var name. REQUIRED for non-test.",
    )

    @field_validator("encryption_key_ref")
    @classmethod
    def _require_key_for_production(cls, v: str, info: ValidationInfo) -> str:
        env = info.data.get("environment")
        if env and env not in (Environment.TEST, Environment.DEVELOPMENT) and not v:
            raise ValueError("encryption_key_ref is required for non-test environments")
        return v

    # --- Token Secrets ---
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-change-me"),
        description="Secret key for JWT signing.",
    )
    refresh_token_secret: SecretStr = Field(
        default=SecretStr("dev-refresh-secret-change-me"),
    )

    @field_validator("jwt_secret_key", "refresh_token_secret", mode="before")
    @classmethod
    def _read_secret_file(cls, value: object) -> object:
        """Resolve absolute Docker-secret paths without ever logging contents."""
        if not isinstance(value, str) or not value.startswith("/"):
            return value
        path = Path(value)
        if not path.is_file():
            raise ValueError("configured secret file is unavailable")
        secret = path.read_text(encoding="utf-8").strip()
        if not secret:
            raise ValueError("configured secret file is empty")
        return secret

    # --- CORS ---
    cors_origins: list[str] = Field(default=["*"])

    # --- TLS ---
    force_tls: bool = Field(default=True)

    @field_validator("force_tls")
    @classmethod
    def _validate_tls_for_env(cls, v: bool, info: ValidationInfo) -> bool:
        env = info.data.get("environment")
        if env and env not in (Environment.TEST, Environment.DEVELOPMENT) and not v:
            raise ValueError("TLS must be enforced in non-test environments")
        return v

    # --- File paths ---
    content_dir: Path = Field(default=Path("content"))
    contracts_dir: Path = Field(default=Path("contracts"))

    # --- Rate Limiting ---
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=60)

    def is_test(self) -> bool:
        return self.environment == Environment.TEST

    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    def is_production_like(self) -> bool:
        return self.environment in (Environment.DEMO, Environment.PRODUCTION)

    def requires_mysql(self) -> bool:
        return self.is_production_like()

    def requires_tls(self) -> bool:
        return self.force_tls
