# ruff: noqa: E501
#!/usr/bin/env python
"""B-18 Backend Adversarial Gate — run all safety/correctness matrix tests and produce evidence.

Usage:
    uv run python scripts/run_backend_adversarial_gate.py --compose deploy/compose.test.yml --evidence artifacts/evidence/backend-adversarial.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ADVERSARIAL_TESTS = [
    "tests/adversarial/test_all_free_text_entry_points.py",
    "tests/adversarial/test_context_ref_forgery.py",
    "tests/adversarial/test_safety_answer_replay.py",
    "tests/adversarial/test_dependency_fail_closed.py",
]


def run_tests() -> dict:
    """Run all adversarial tests and return structured results."""
    evidence = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "exit_code": 0,
        "tests": [],
    }

    for test_path in ADVERSARIAL_TESTS:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        test_name = Path(test_path).stem
        evidence["tests"].append({"name": test_name, "exit_code": result.returncode})
        if result.returncode == 0:
            evidence["passed"] += 1
        else:
            evidence["failed"] += 1
            evidence["exit_code"] = 1

    evidence["total"] = evidence["passed"] + evidence["failed"]
    return evidence


def main() -> None:
    evidence_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--evidence" and i + 1 < len(sys.argv):
            evidence_dir = Path(sys.argv[i + 1])

    evidence = run_tests()

    if evidence_dir:
        evidence_dir.parent.mkdir(parents=True, exist_ok=True)
        evidence_dir.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    print(f"Adversarial gate: {evidence['passed']}/{evidence['total']} passed, {evidence['failed']} failed")
    sys.exit(evidence["exit_code"])


if __name__ == "__main__":
    main()
