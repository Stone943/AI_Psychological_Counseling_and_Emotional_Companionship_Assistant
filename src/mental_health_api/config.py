"""Strict Settings for mental_health_api.

Production/demo deployments require MySQL, HTTPS/WSS, and external secrets.
Test environment allows SQLite and HTTP.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    TEST = "test"
    DEVELOPMENT = "development"
    DEMO = "demo"
    PRODUCTION = "production"


class DatabaseBackend(str, Enum):
    """Supported database backends."""

    SQLITE = "sqlite"
    MYSQL = "mysql"


class Settings(BaseSettings):
    """Application-wide settings with strict validation.

    Test environment allows SQLite; demo/production require MySQL + https/wss.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
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
    database_backend: DatabaseBackend = Field(default=DatabaseBackend.SQLITE)

    @field_validator("database_backend", mode="before")
    @classmethod
    def _infer_backend(cls, v: str | None, info: ValidationInfo) -> DatabaseBackend:
        if v is not None:
            return DatabaseBackend(v)
        url = info.data.get("database_url", "")
        if "mysql" in url or "asyncmy" in url:
            return DatabaseBackend.MYSQL
        if "sqlite" in url:
            return DatabaseBackend.SQLITE
        return DatabaseBackend.SQLITE

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
        if env and env not in (Environment.TEST, Environment.DEVELOPMENT):
            if not v:
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

    # --- CORS ---
    cors_origins: list[str] = Field(default=["*"])

    # --- TLS ---
    force_tls: bool = Field(default=True)

    @field_validator("force_tls")
    @classmethod
    def _validate_tls_for_env(cls, v: bool, info: ValidationInfo) -> bool:
        env = info.data.get("environment")
        if env and env not in (Environment.TEST, Environment.DEVELOPMENT):
            if not v:
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
