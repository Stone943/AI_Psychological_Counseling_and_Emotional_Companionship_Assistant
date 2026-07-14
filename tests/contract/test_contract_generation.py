"""Verify export scripts produce stable, byte-identical output."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def run_script(script_name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class TestOpenAPIExport:
    def test_write_creates_file(self) -> None:
        result = run_script("export_openapi.py", "--write")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert (ROOT / "contracts" / "openapi" / "openapi.json").exists()

    def test_check_passes_after_write(self) -> None:
        # Write first to ensure the file exists
        run_script("export_openapi.py", "--write")
        result = run_script("export_openapi.py", "--check")
        assert result.returncode == 0, f"Check failed after write. stderr: {result.stderr}"

    def test_check_fails_on_modified_file(self) -> None:
        import json

        run_script("export_openapi.py", "--write")
        path = ROOT / "contracts" / "openapi" / "openapi.json"
        original = path.read_bytes()
        # Modify the file
        data = json.loads(original)
        data["info"]["title"] = "MODIFIED TITLE"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result = run_script("export_openapi.py", "--check")
        assert result.returncode != 0, "Check should fail on modified file"
        # Restore
        path.write_bytes(original)


class TestWSExport:
    def test_write_creates_files(self) -> None:
        result = run_script("export_ws_contracts.py", "--write")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        for fn in ("client_commands.schema.json", "server_events.schema.json", "canonical_rows.json"):
            assert (ROOT / "contracts" / "ws" / fn).exists(), f"{fn} not created"

    def test_check_passes_after_write(self) -> None:
        run_script("export_ws_contracts.py", "--write")
        result = run_script("export_ws_contracts.py", "--check")
        assert result.returncode == 0, f"Check failed: {result.stderr}"
