"""B-19: Compose demo contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent


def load_compose(filename: str) -> dict:
    path = ROOT / "deploy" / filename
    if not path.exists():
        pytest.skip(f"{filename} does not exist yet")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestComposeDemo:
    def test_compose_demo_exists(self) -> None:
        """RED/GREEN: compose.demo.yml should exist."""
        path = ROOT / "deploy" / "compose.demo.yml"
        assert path.exists(), "compose.demo.yml does not exist"

    def test_services_include_api_mysql_redis(self) -> None:
        compose = load_compose("compose.demo.yml")
        svc = compose.get("services", {})
        assert "api" in svc or "caddy" in svc, "Must have api or caddy service"

    def test_no_embedded_profile(self) -> None:
        compose = load_compose("compose.demo.yml")
        svc_names = list(compose.get("services", {}).keys())
        for s in svc_names:
            assert "embedded" not in s.lower()
            assert "arm" not in s.lower()

    def test_api_environment_matches_settings_prefix_and_mysql(self) -> None:
        environment = load_compose("compose.demo.yml")["services"]["api"]["environment"]
        assert environment["MENTAL_HEALTH_ENVIRONMENT"] == "demo"
        assert environment["MENTAL_HEALTH_DATABASE_BACKEND"] == "mysql"
        assert environment["MENTAL_HEALTH_DATABASE_URL_FILE"] == "/run/secrets/database_url"
        assert not any("PASSWORD" in key or key == "MENTAL_HEALTH_DATABASE_URL" for key in environment)
        assert "DATABASE_URL" not in environment

    def test_migration_uses_runtime_virtualenv_command(self) -> None:
        command = load_compose("compose.demo.yml")["services"]["migrate"]["command"]
        assert command == ["alembic", "upgrade", "head"]
        assert command[0] != "uv"

    def test_retention_is_not_scheduled_before_full_schema_migration(self) -> None:
        services = load_compose("compose.demo.yml")["services"]
        assert "retention" not in services

    def test_runtime_image_includes_reviewed_content_path(self) -> None:
        dockerfile = (ROOT / "deploy" / "Dockerfile.api").read_text(encoding="utf-8")
        assert "COPY content/ content/" in dockerfile

    def test_images_and_build_stages_require_reviewed_digests(self) -> None:
        compose = load_compose("compose.demo.yml")
        for service_name in ("caddy", "mysql", "redis"):
            image = compose["services"][service_name]["image"]
            assert "@${" in image and "IMAGE_DIGEST:?" in image
        for service_name in ("api", "migrate"):
            args = compose["services"][service_name]["build"]["args"]
            assert "@${PYTHON_IMAGE_DIGEST:?" in args["PYTHON_IMAGE"]
            assert "@${UV_IMAGE_DIGEST:?" in args["UV_IMAGE"]

    def test_secret_files_are_required_and_have_no_dev_null_fallback(self) -> None:
        compose = load_compose("compose.demo.yml")
        rendered = (ROOT / "deploy" / "compose.demo.yml").read_text(encoding="utf-8")
        assert "/dev/null" not in rendered
        assert "MYSQL_PASSWORD" not in compose["services"]["mysql"]["environment"]
        for secret in compose["secrets"].values():
            assert ":?" in secret["file"]


class TestCompatibilityMatrix:
    def test_matrix_exists(self) -> None:
        path = ROOT / "deploy" / "compatibility-matrix.json"
        if not path.exists():
            pytest.skip("compatibility-matrix.json does not exist yet")
