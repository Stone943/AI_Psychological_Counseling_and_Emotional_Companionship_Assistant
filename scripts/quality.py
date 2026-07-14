#!/usr/bin/env python
"""Unified quality command for mental_health_api.

Usage:
    uv run python scripts/quality.py python    # lint + format check + mypy + test
    uv run python scripts/quality.py all       # python + any future js/mobile checks
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], description: str) -> int:
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"  {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def python_quality() -> int:
    """Run all Python quality checks."""
    exit_code = 0

    # Lock check
    if run(["uv", "lock", "--check"], "uv lock --check") != 0:
        exit_code = 1

    # Ruff lint
    ruff_check = [
        "uv",
        "run",
        "ruff",
        "check",
        "src/mental_health_api",
        "tests/",
        "scripts/",
    ]
    if run(ruff_check, "Ruff lint") != 0:
        exit_code = 1

    # Ruff format check
    ruff_format = [
        "uv",
        "run",
        "ruff",
        "format",
        "--check",
        "src/mental_health_api",
        "tests/",
        "scripts/",
    ]
    if run(ruff_format, "Ruff format check") != 0:
        exit_code = 1

    # Mypy
    mypy_cmd = [
        "uv",
        "run",
        "mypy",
        "src/mental_health_api",
        "--config-file",
        str(ROOT / "pyproject.toml"),
    ]
    if run(mypy_cmd, "Mypy type check") != 0:
        exit_code = 1

    # Pytest
    pytest_cmd = [
        "uv",
        "run",
        "pytest",
        "-q",
    ]
    if run(pytest_cmd, "Pytest") != 0:
        exit_code = 1

    return exit_code


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/quality.py [python|all]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "python":
        sys.exit(python_quality())
    elif command == "all":
        exit_code = python_quality()
        sys.exit(exit_code)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
