"""Test that PublicError canonical rows match PRD 2.5 exactly."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def load_canonical_rows() -> dict:
    path = ROOT / "contracts" / "errors" / "canonical_rows.json"
    assert path.exists(), f"{path} does not exist"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_canonical_rows_exact_count() -> None:
    """PRD 2.5 defines exactly 26 error codes in v1."""
    data = load_canonical_rows()
    assert data["version"] == "v1"
    assert len(data["rows"]) == 26, f"Expected 26 rows, got {len(data['rows'])}"


def test_public_error_schema_forbids_extra() -> None:
    """PublicError schema must reject unknown fields."""
    path = ROOT / "contracts" / "errors" / "public_errors.schema.json"
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["additionalProperties"] is False
    assert "code" in schema["required"]


def test_every_error_has_required_fields() -> None:
    """Each canonical error row must have code, http_status, retryable, client_action."""
    data = load_canonical_rows()
    for row in data["rows"]:
        assert "code" in row
        assert "http_status" in row
        assert "retryable" in row
        assert "client_action" in row


def test_no_duplicate_codes() -> None:
    """Error codes must be unique."""
    data = load_canonical_rows()
    codes = [r["code"] for r in data["rows"]]
    assert len(codes) == len(set(codes)), f"Duplicate codes: { {c for c in codes if codes.count(c) > 1} }"


def test_python_matches_json() -> None:
    """Python CANONICAL_ERRORS must exactly match JSON canonical_rows."""
    from mental_health_api.contracts.public_errors import CANONICAL_ERRORS

    data = load_canonical_rows()
    json_codes = {r["code"] for r in data["rows"]}
    py_codes = set(CANONICAL_ERRORS.keys())
    assert json_codes == py_codes, f"JSON-only: {json_codes - py_codes}, Python-only: {py_codes - json_codes}"


def test_specific_error_codes() -> None:
    """Key safety and auth error codes must be present."""
    from mental_health_api.contracts.public_errors import get_error

    safety = get_error("SAFETY_GATE_UNAVAILABLE")
    assert safety.http_status == 503
    assert safety.retryable is True
    assert safety.client_action == "retry"

    assessment_deleted = get_error("ASSESSMENT_RESULT_DELETED")
    assert assessment_deleted.http_status == 410
    assert assessment_deleted.client_action == "remove_local_copy"

    safety_confirm = get_error("SAFETY_CONFIRMATION_REQUIRED")
    assert safety_confirm.http_status == 423
