#!/usr/bin/env python
"""Run B-18 against the real Compose/MySQL stack and emit machine evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
MATRIX_TESTS = (
    "tests/adversarial/test_all_free_text_entry_points.py",
    "tests/adversarial/test_context_ref_forgery.py",
    "tests/adversarial/test_safety_transaction_rollbacks.py",
    "tests/adversarial/test_safety_answer_replay.py",
    "tests/adversarial/test_dependency_fail_closed.py",
    "tests/security/test_plaintext_absence.py",
    "tests/security/test_log_trace_redaction.py",
    "tests/security/test_cross_subject_matrix.py",
    "tests/integration/test_all_free_text_idempotency.py",
)
REQUIRED_METRICS = {
    "business_writes_on_non_l0": 0,
    "plaintext_hits": 0,
    "cross_subject_reads": 0,
    "safety_screen_calls_per_chat_turn": 1,
}
REQUIRED_CASE_IDS = frozenset(Path(path).stem for path in MATRIX_TESTS)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def _write_evidence(path: Path | None, evidence: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _junit_counts(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    return {
        name: sum(int(suite.attrib.get(name, "0")) for suite in suites)
        for name in ("tests", "failures", "errors", "skipped")
    }


def _junit_files(path: Path) -> set[str]:
    root = ET.parse(path).getroot()
    return {
        Path(case.attrib["file"]).stem for case in root.iter("testcase") if isinstance(case.attrib.get("file"), str)
    }


def _git_sha() -> str:
    return _run(["git", "rev-parse", "HEAD"]).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_instrumentation(
    value: object,
    *,
    run_id: str,
    git_sha: str,
    compose_sha256: str,
    migration_revision: str,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return {}, ["instrumentation evidence must be a JSON object"]
    expected_metadata = {
        "producer": "application_and_mysql_instrumentation",
        "run_id": run_id,
        "git_sha": git_sha,
        "compose_sha256": compose_sha256,
        "database_backend": "mysql",
        "migration_revision": migration_revision,
    }
    for key, expected in expected_metadata.items():
        if value.get(key) != expected:
            errors.append(f"instrumentation provenance mismatch: {key}")
    case_ids = value.get("case_ids")
    if not isinstance(case_ids, list) or set(case_ids) != REQUIRED_CASE_IDS:
        errors.append("instrumentation does not cover the exact B-18 case IDs")
    metrics = value.get("metrics")
    if not isinstance(metrics, dict) or any(metrics.get(key) != expected for key, expected in REQUIRED_METRICS.items()):
        errors.append("instrumentation safety metrics are missing or invalid")
        metrics = {}
    events = value.get("instrumentation_events")
    event_cases: set[str] = set()
    if isinstance(events, list):
        for event in events:
            if (
                isinstance(event, dict)
                and set(event) == {"case_id", "source", "event_count", "nodeids"}
                and event.get("case_id") in REQUIRED_CASE_IDS
                and event.get("source") in {"application", "mysql"}
                and isinstance(event.get("event_count"), int)
                and not isinstance(event.get("event_count"), bool)
                and event["event_count"] > 0
                and isinstance(event.get("nodeids"), list)
                and bool(event["nodeids"])
                and all(isinstance(nodeid, str) and nodeid for nodeid in event["nodeids"])
            ):
                event_cases.add(event["case_id"])
    if event_cases != REQUIRED_CASE_IDS:
        errors.append("application/MySQL instrumentation events do not cover every B-18 case")
    return metrics, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", required=True, type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    compose = (ROOT / args.compose).resolve() if not args.compose.is_absolute() else args.compose.resolve()
    run_id = uuid4().hex
    git_sha = _git_sha()
    compose_sha256 = _sha256(compose) if compose.is_file() else ""
    started_at = datetime.now(UTC)
    evidence: dict[str, Any] = {
        "schema_version": "b18-evidence.v1",
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "git_sha": git_sha,
        "compose": str(compose),
        "compose_sha256": compose_sha256,
        "image_ids": [],
        "migration_revision": None,
        "database_backend": "mysql",
        "tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "metrics": {},
        "errors": [],
        "exit_code": 2,
    }
    missing = [path for path in MATRIX_TESTS if not (ROOT / path).is_file()]
    if not compose.is_file():
        evidence["errors"].append("compose file is missing")
    if missing:
        evidence["errors"].append(f"required B-18 matrix files are missing: {', '.join(missing)}")
    if shutil.which("docker") is None or _run(["docker", "info"]).returncode != 0:
        evidence["errors"].append("Docker engine is unavailable")
    if evidence["errors"]:
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(args.evidence, evidence)
        print("B-18 adversarial gate: FAIL (preflight)")
        return 2

    compose_cmd = ["docker", "compose", "-f", str(compose)]
    config = _run([*compose_cmd, "config", "--quiet"])
    if config.returncode != 0:
        evidence["errors"].append("Compose configuration is invalid")
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(args.evidence, evidence)
        print("B-18 adversarial gate: FAIL (compose config)")
        return 2

    started = False
    return_code = 2
    try:
        up = _run([*compose_cmd, "up", "-d", "--wait", "mysql", "redis", "mailpit"])
        if up.returncode != 0:
            evidence["errors"].append("Compose dependencies failed to become healthy")
            return_code = 2
        else:
            started = True
            image_result = _run([*compose_cmd, "images", "--format", "json"])
            image_ids = re.findall(r"sha256:[0-9a-f]{64}", image_result.stdout)
            if image_result.returncode != 0 or not image_ids:
                evidence["errors"].append("Compose image identities are unavailable")
            else:
                evidence["image_ids"] = sorted(set(image_ids))
            migrate = _run([*compose_cmd, "run", "--rm", "api-test", "alembic", "upgrade", "head"])
            if migrate.returncode != 0:
                evidence["errors"].append("clean MySQL migration failed")
                return_code = 2
            else:
                migration = _run([*compose_cmd, "run", "--rm", "api-test", "alembic", "current"])
                migration_revision = migration.stdout.strip().split()[0] if migration.returncode == 0 else ""
                if not migration_revision:
                    evidence["errors"].append("applied MySQL migration revision is unavailable")
                else:
                    evidence["migration_revision"] = migration_revision
                with tempfile.TemporaryDirectory(prefix="b18-evidence-", dir=ROOT) as temporary:
                    report_dir = Path(temporary)
                    report = report_dir / "pytest.xml"
                    metrics = report_dir / "metrics.json"
                    test_run = _run(
                        [
                            *compose_cmd,
                            "run",
                            "--rm",
                            "--volume",
                            f"{report_dir}:/evidence",
                            "--env",
                            "ADVERSARIAL_METRICS_FILE=/evidence/metrics.json",
                            "--env",
                            f"ADVERSARIAL_RUN_ID={run_id}",
                            "--env",
                            f"ADVERSARIAL_GIT_SHA={git_sha}",
                            "--env",
                            f"ADVERSARIAL_COMPOSE_SHA256={compose_sha256}",
                            "--env",
                            f"ADVERSARIAL_MIGRATION_REVISION={migration_revision}",
                            "api-test",
                            "python",
                            "-m",
                            "pytest",
                            *MATRIX_TESTS,
                            "--junitxml=/evidence/pytest.xml",
                            "-q",
                        ]
                    )
                    if report.is_file():
                        counts = _junit_counts(report)
                        evidence.update(counts)
                        evidence["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
                        evidence["failed"] = counts["failures"] + counts["errors"]
                        if _junit_files(report) != REQUIRED_CASE_IDS:
                            evidence["errors"].append("JUnit evidence does not cover the exact B-18 matrix files")
                    else:
                        evidence["errors"].append("pytest did not produce JUnit evidence")
                    if metrics.is_file():
                        try:
                            loaded_metrics = json.loads(metrics.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError):
                            loaded_metrics = None
                        validated_metrics, metric_errors = _validate_instrumentation(
                            loaded_metrics,
                            run_id=run_id,
                            git_sha=git_sha,
                            compose_sha256=compose_sha256,
                            migration_revision=migration_revision,
                        )
                        evidence["metrics"] = validated_metrics
                        evidence["errors"].extend(metric_errors)
                    else:
                        evidence["errors"].append("adversarial tests did not produce metric evidence")
                    metrics_ok = all(evidence["metrics"].get(key) == value for key, value in REQUIRED_METRICS.items())
                    return_code = 0
                    if (
                        test_run.returncode != 0
                        or evidence["failed"] != 0
                        or evidence["skipped"] != 0
                        or evidence["tests"] == 0
                        or not metrics_ok
                        or evidence["errors"]
                    ):
                        return_code = 1
    finally:
        if started:
            _run([*compose_cmd, "down", "--volumes", "--remove-orphans"])

    evidence["exit_code"] = return_code
    evidence["finished_at"] = datetime.now(UTC).isoformat()
    _write_evidence(args.evidence, evidence)
    print(
        f"B-18 adversarial gate: {'PASS' if return_code == 0 else 'FAIL'} "
        f"({evidence['passed']}/{evidence['tests']} passed, {evidence['skipped']} skipped)"
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
