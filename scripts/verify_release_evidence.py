#!/usr/bin/env python
"""Independently re-verify a B-20 evidence directory and its bound producer files."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from run_live_stack_e2e import (
    EXPECTED_METRICS,
    REQUIRED_CASE_IDS,
    ROOT,
    UPSTREAM_EVIDENCE,
    _parse_utc,
    _sha256,
    _validate_producer_evidence,
)

EXPECTED_FIELDS = {
    "schema_version",
    "run_id",
    "mode",
    "target",
    "started_at",
    "finished_at",
    "git_sha",
    "tests_passed",
    "tests_total",
    "case_ids",
    "metrics",
    "upstream_evidence_sha256",
    "producer_evidence_sha256",
    "steps",
    "errors",
    "synthetic_data_only",
}


def _load(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"evidence is unavailable: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("evidence must be a JSON object")
    return value


def verify(evidence_dir: Path) -> list[str]:
    errors: list[str] = []
    evidence_path = evidence_dir / "evidence.json"
    evidence = _load(evidence_path)
    if set(evidence) != EXPECTED_FIELDS or evidence.get("schema_version") != "e2e-evidence.v1":
        errors.append("final evidence schema is invalid")
    run_id = evidence.get("run_id")
    git_sha = evidence.get("git_sha")
    target = evidence.get("target")
    started_at = _parse_utc(evidence.get("started_at"))
    finished_at = _parse_utc(evidence.get("finished_at"))
    current_git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    if (
        not isinstance(run_id, str)
        or len(run_id) != 32
        or any(char not in "0123456789abcdef" for char in run_id)
        or not isinstance(git_sha, str)
        or git_sha != current_git_sha
        or not isinstance(target, str)
        or not target
        or started_at is None
        or finished_at is None
        or started_at > finished_at
        or finished_at > datetime.now(UTC)
    ):
        errors.append("final evidence identity, checkout, target, or time window is invalid")
        return errors
    if evidence.get("tests_passed") is not True or evidence.get("errors") != []:
        errors.append("final evidence does not record a clean PASS")
    tests_total = evidence.get("tests_total")
    if not isinstance(tests_total, int) or isinstance(tests_total, bool) or tests_total < 1:
        errors.append("final evidence has no executed tests")
    case_ids = evidence.get("case_ids")
    if not isinstance(case_ids, list) or set(case_ids) != REQUIRED_CASE_IDS:
        errors.append("final evidence does not cover the frozen B-20 case matrix")
    metrics = evidence.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("final evidence metrics are invalid")
    else:
        for key, expected in EXPECTED_METRICS.items():
            actual = metrics.get(key)
            if (key == "turns_completed" and (not isinstance(actual, int) or actual < 20)) or (
                key != "turns_completed" and actual != expected
            ):
                errors.append(f"final evidence metric is invalid: {key}")
    steps = evidence.get("steps")
    if (
        not isinstance(steps, list)
        or len(steps) < 2
        or any(
            not isinstance(step, dict) or set(step) != {"name", "exit_code"} or step.get("exit_code") != 0
            for step in steps
        )
    ):
        errors.append("final evidence execution steps are incomplete")

    upstream_hashes = evidence.get("upstream_evidence_sha256")
    if not isinstance(upstream_hashes, dict):
        errors.append("upstream evidence hash map is invalid")
    else:
        for label, relative_path in UPSTREAM_EVIDENCE.items():
            path = ROOT / relative_path
            if not path.is_file() or upstream_hashes.get(label) != _sha256(path):
                errors.append(f"upstream evidence hash mismatch: {label}")

    producer_hashes = evidence.get("producer_evidence_sha256")
    if not isinstance(producer_hashes, dict):
        errors.append("producer evidence hash map is invalid")
        return errors
    producer_dir = evidence_dir / "producers"
    for producer, suffix in (("mobile_detox", "mobile"), ("backend_pytest", "backend")):
        path = producer_dir / f"{run_id}.{suffix}.json"
        before = len(errors)
        _validate_producer_evidence(
            path,
            producer=producer,
            run_id=run_id,
            git_sha=git_sha,
            target=target,
            started_at=started_at,
            errors=errors,
        )
        if len(errors) == before and producer_hashes.get(producer) != _sha256(path):
            errors.append(f"producer evidence hash mismatch: {producer}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    try:
        errors = verify(evidence_dir)
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("B-20 release evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
