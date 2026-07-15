"""Verify that Docker Compose files declare expected services and health checks.

These tests validate the compose file structure, not live container state.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent


def load_compose(filename: str) -> dict:
    """Load a docker compose YAML file."""
    path = ROOT / "deploy" / filename
    assert path.exists(), f"{filename} does not exist"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestComposeTestFile:
    """compose.test.yml must include mysql, redis, mailpit, and api-test."""

    @pytest.fixture
    def compose(self) -> dict:
        return load_compose("compose.test.yml")

    def test_has_mysql_service(self, compose) -> None:
        assert "mysql" in compose.get("services", {})
        svc = compose["services"]["mysql"]
        assert "healthcheck" in svc
        assert svc.get("image", "").startswith("mysql")

    def test_mysql_healthcheck(self, compose) -> None:
        svc = compose["services"]["mysql"]
        hc = svc.get("healthcheck", {})
        assert "test" in hc
        assert "interval" in hc

    def test_has_redis_service(self, compose) -> None:
        assert "redis" in compose.get("services", {})
        svc = compose["services"]["redis"]
        assert "healthcheck" in svc
        assert "redis" in svc.get("image", "")

    def test_has_mailpit_service(self, compose) -> None:
        assert "mailpit" in compose.get("services", {})
        svc = compose["services"]["mailpit"]
        assert "healthcheck" in svc

    def test_has_api_test_service(self, compose) -> None:
        assert "api-test" in compose.get("services", {})

    def test_api_test_depends_on(self, compose) -> None:
        svc = compose["services"]["api-test"]
        deps = svc.get("depends_on", {})
        # All deps should be healthy before api-test starts
        for _dep_name, dep_config in deps.items():
            assert dep_config.get("condition") == "service_healthy"

    def test_api_test_environment_matches_settings_prefix(self, compose) -> None:
        environment = compose["services"]["api-test"]["environment"]
        assert environment["MENTAL_HEALTH_DATABASE_BACKEND"] == "mysql"
        assert all(key.startswith("MENTAL_HEALTH_") for key in environment)


class TestComposeDevFile:
    """compose.dev.yml must include mysql, redis, mailpit for local development."""

    @pytest.fixture
    def compose(self) -> dict:
        return load_compose("compose.dev.yml")

    def test_has_infra_services(self, compose) -> None:
        services = compose.get("services", {})
        assert "mysql" in services
        assert "redis" in services
        assert "mailpit" in services

    def test_mysql_has_persistent_volume(self, compose) -> None:
        svc = compose["services"]["mysql"]
        volumes = svc.get("volumes", [])
        assert any("mysql-dev-data" in str(v) for v in volumes)
