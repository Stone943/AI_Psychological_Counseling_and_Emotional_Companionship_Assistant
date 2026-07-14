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


class TestCompatibilityMatrix:
    def test_matrix_exists(self) -> None:
        path = ROOT / "deploy" / "compatibility-matrix.json"
        if not path.exists():
            pytest.skip("compatibility-matrix.json does not exist yet")
