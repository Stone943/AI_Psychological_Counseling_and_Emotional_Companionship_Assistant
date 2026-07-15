"""Release orchestrators must never turn missing external evidence into PASS."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def test_b18_rejects_missing_compose_and_matrix(tmp_path: Path) -> None:
    evidence = tmp_path / "b18.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_backend_adversarial_gate.py"),
            "--compose",
            "definitely-missing.yml",
            "--evidence",
            str(evidence),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "PASS" not in result.stdout
    assert json.loads(evidence.read_text(encoding="utf-8"))["exit_code"] != 0


def test_b18_rejects_unproven_metric_constants() -> None:
    module = runpy.run_path(str(ROOT / "scripts/run_backend_adversarial_gate.py"))
    metrics, errors = module["_validate_instrumentation"](
        {
            "business_writes_on_non_l0": 0,
            "plaintext_hits": 0,
            "cross_subject_reads": 0,
            "safety_screen_calls_per_chat_turn": 1,
        },
        run_id="a" * 32,
        git_sha="b" * 40,
        compose_sha256="c" * 64,
        migration_revision="revision",
    )
    assert metrics == {}
    assert errors


def test_b20_remote_rejects_unreachable_endpoint_and_missing_mobile(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "remote-evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_live_stack_e2e.py"),
            "--remote-base-url",
            "https://127.0.0.1:1",
            "--mobile-dir",
            "definitely-missing",
            "--android-avd",
            "DefinitelyMissing",
            "--synthetic-only",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    machine_evidence = json.loads((evidence_dir / "evidence.json").read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert "result=PASS" not in result.stdout
    assert machine_evidence["tests_passed"] is False
    assert machine_evidence["errors"]
    verification = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_release_evidence.py"),
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verification.returncode != 0


def test_b20_local_rejects_missing_kvm_docker_mobile_and_tests(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "local-evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_live_stack_e2e.py"),
            "--compose",
            "definitely-missing.yml",
            "--mobile-dir",
            "definitely-missing",
            "--android-avd",
            "DefinitelyMissing",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "result=PASS" not in result.stdout
    assert json.loads((evidence_dir / "evidence.json").read_text(encoding="utf-8"))["tests_passed"] is False


def test_b20_rejects_stale_producer_json(tmp_path: Path) -> None:
    module = runpy.run_path(str(ROOT / "scripts/run_live_stack_e2e.py"))
    started_at = datetime.now(UTC)
    stale = started_at - timedelta(hours=1)
    evidence_path = tmp_path / "stale.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "e2e-producer.v1",
                "producer": "backend_pytest",
                "run_id": "a" * 32,
                "git_sha": "b" * 40,
                "target": "https://deployment.example",
                "started_at": stale.isoformat(),
                "finished_at": stale.isoformat(),
                "tests_total": 1,
                "success": True,
                "case_ids": ["twenty_turn_context"],
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    errors: list[str] = []
    result = module["_validate_producer_evidence"](
        evidence_path,
        producer="backend_pytest",
        run_id="a" * 32,
        git_sha="b" * 40,
        target="https://deployment.example",
        started_at=started_at,
        errors=errors,
    )
    assert result == {}
    assert errors == ["backend_pytest evidence is stale or has invalid provenance"]
