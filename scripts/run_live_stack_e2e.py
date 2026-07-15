#!/usr/bin/env python
"""B-20 real-stack orchestrator; missing machine evidence always fails closed."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
BACKEND_E2E_TESTS = (
    "tests/e2e/test_live_stack_evidence.py",
    "tests/e2e/test_live_stack_failure_recovery.py",
)
MOBILE_REQUIRED = (
    "package.json",
    "detox.config.js",
    "e2e/liveStack20Turn.e2e.ts",
)
EXPECTED_METRICS: dict[str, int | bool] = {
    "turns_completed": 20,
    "sequence_contiguous": True,
    "resume_after_ack": True,
    "safety_screen_calls_per_chat_turn": 1,
    "unreviewed_tokens": 0,
    "duplicate_logical_events": 0,
    "cross_subject_reads": 0,
    "plaintext_hits": 0,
    "feedback_rows": 1,
}
REQUIRED_CASE_IDS = frozenset(
    {
        "guest_to_account_migration",
        "guest_token_24h",
        "twenty_turn_context",
        "single_screen_per_turn",
        "sequence_ack_resume",
        "generation_cancel",
        "safety_answer_recheck",
        "emotion_result",
        "exercise_catalog_12",
        "knowledge_rag_8",
        "phq9_gad7_q9_safety",
        "crisis_offline_degraded",
        "memory_modes",
        "feedback_persistence",
        "recovery_mailpit",
        "assessment_lifecycle",
        "privacy_export_delete_close",
        "api_restart_recovery",
        "redis_restart_recovery",
        "websocket_resume",
        "idempotency_replay",
        "content_withdrawal",
        "deletion_tombstone",
        "cross_subject_isolation",
    }
)
UPSTREAM_EVIDENCE = {
    "member_a_release_profile": Path("artifacts/evidence/a-release-profile.json"),
    "member_c_harness_ready": Path("mobile/artifacts/evidence/member-c-harness-ready.json"),
    "member_b_runtime": Path("artifacts/evidence/b19-runtime.json"),
}


def _run(
    command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(command, cwd=cwd, env=merged, capture_output=True, text=True, check=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_contract_hashes() -> tuple[str, str]:
    openapi_hash = _sha256(ROOT / "contracts/openapi/openapi.json")
    digest = hashlib.sha256()
    for path in sorted((ROOT / "contracts/ws").glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return openapi_hash, digest.hexdigest()


def _validate_remote_endpoint(base_url: str, errors: list[str]) -> None:
    parsed = urlparse(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        errors.append("remote endpoint must be a credential-free HTTPS base URL")
        return
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if address.is_loopback or address.is_private or address.is_unspecified:
            errors.append("remote endpoint must not be loopback/private/unspecified")
            return
    except ValueError:
        pass
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=10) as response:
            if response.status != 200:
                raise ValueError("health endpoint is not ready")
            health = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        errors.append(f"remote endpoint health verification failed: {type(exc).__name__}")
        return
    openapi_hash, ws_hash = _local_contract_hashes()
    if (
        not isinstance(health, dict)
        or health.get("openapi_sha256") != openapi_hash
        or health.get("ws_sha256") != ws_hash
    ):
        errors.append("remote endpoint contract hashes do not match this checkout")


def _load_evidence(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} machine evidence is unavailable: {type(exc).__name__}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} machine evidence must be an object")
        return {}
    return value


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed.astimezone(UTC)


def _validate_upstream_evidence(git_sha: str, target: str, errors: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for label, relative_path in UPSTREAM_EVIDENCE.items():
        path = ROOT / relative_path
        value = _load_evidence(path, label, errors)
        if not value:
            continue
        if value.get("status") != "PASS" or value.get("git_sha") != git_sha or value.get("target") != target:
            errors.append(f"{label} is not a PASS for this checkout and target")
            continue
        hashes[label] = _sha256(path)
    return hashes


def _validate_producer_evidence(
    path: Path,
    *,
    producer: str,
    run_id: str,
    git_sha: str,
    target: str,
    started_at: datetime,
    errors: list[str],
) -> dict[str, Any]:
    value = _load_evidence(path, producer, errors)
    if not value:
        return {}
    try:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        errors.append(f"{producer} evidence timestamp is unavailable")
        return {}
    producer_started = _parse_utc(value.get("started_at"))
    producer_finished = _parse_utc(value.get("finished_at"))
    required_fields = {
        "schema_version",
        "producer",
        "run_id",
        "git_sha",
        "target",
        "started_at",
        "finished_at",
        "tests_total",
        "success",
        "case_ids",
        "metrics",
    }
    if set(value) != required_fields:
        errors.append(f"{producer} evidence schema is invalid")
    if (
        value.get("schema_version") != "e2e-producer.v1"
        or value.get("producer") != producer
        or value.get("run_id") != run_id
        or value.get("git_sha") != git_sha
        or value.get("target") != target
        or value.get("success") is not True
        or not isinstance(value.get("tests_total"), int)
        or isinstance(value.get("tests_total"), bool)
        or value.get("tests_total", 0) <= 0
        or not isinstance(value.get("case_ids"), list)
        or not all(isinstance(case_id, str) and case_id in REQUIRED_CASE_IDS for case_id in value.get("case_ids", []))
        or len(set(value.get("case_ids", []))) != len(value.get("case_ids", []))
        or not isinstance(value.get("metrics"), dict)
        or producer_started is None
        or producer_finished is None
        or producer_started < started_at
        or producer_started > producer_finished
        or producer_finished > datetime.now(UTC)
        or modified_at < started_at
    ):
        errors.append(f"{producer} evidence is stale or has invalid provenance")
        return {}
    return value


def _merge_metrics(producers: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for producer in producers:
        for key, value in producer.get("metrics", {}).items():
            if key in merged and merged[key] != value:
                errors.append(f"producer metric conflict: {key}")
            else:
                merged[key] = value
    return merged


def _write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--compose", type=Path)
    mode.add_argument("--remote-base-url")
    parser.add_argument("--mobile-dir", required=True, type=Path)
    parser.add_argument("--android-avd", required=True)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()

    remote = args.remote_base_url is not None
    run_mode = "remote_smoke" if remote else "local_full_stack"
    mobile_dir = (ROOT / args.mobile_dir).resolve() if not args.mobile_dir.is_absolute() else args.mobile_dir.resolve()
    evidence_dir = (
        (ROOT / args.evidence_dir).resolve() if not args.evidence_dir.is_absolute() else args.evidence_dir.resolve()
    )
    run_id = uuid4().hex
    started_at = datetime.now(UTC)
    git_sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    local_compose = None
    if not remote:
        local_compose = (ROOT / args.compose).resolve() if not args.compose.is_absolute() else args.compose.resolve()
    target = (
        str(args.remote_base_url).rstrip("/")
        if remote
        else f"local://compose-e2e/{_sha256(local_compose) if local_compose and local_compose.is_file() else 'missing'}"
    )
    producer_dir = evidence_dir / "producers"
    mobile_evidence_path = producer_dir / f"{run_id}.mobile.json"
    backend_evidence_path = producer_dir / f"{run_id}.backend.json"
    evidence: dict[str, Any] = {
        "schema_version": "e2e-evidence.v1",
        "run_id": run_id,
        "mode": run_mode,
        "target": target,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "git_sha": git_sha,
        "tests_passed": False,
        "tests_total": 0,
        "case_ids": [],
        "metrics": {},
        "upstream_evidence_sha256": {},
        "producer_evidence_sha256": {},
        "steps": [],
        "errors": [],
        "synthetic_data_only": bool(args.synthetic_only),
    }
    errors: list[str] = evidence["errors"]
    if not git_sha or len(git_sha) != 40:
        errors.append("checkout git SHA is unavailable")
    evidence["upstream_evidence_sha256"] = _validate_upstream_evidence(git_sha, target, errors)
    missing_mobile = [path for path in MOBILE_REQUIRED if not (mobile_dir / path).is_file()]
    missing_backend = [path for path in BACKEND_E2E_TESTS if not (ROOT / path).is_file()]
    if missing_mobile:
        errors.append(f"required Member C mobile artifacts are missing: {', '.join(missing_mobile)}")
    if missing_backend:
        errors.append(f"required B-20 evidence tests are missing: {', '.join(missing_backend)}")
    for tool in ("adb", "emulator", "npx"):
        if shutil.which(tool) is None:
            errors.append(f"required Android tool is unavailable: {tool}")
    if shutil.which("emulator") is not None:
        avds = _run(["emulator", "-list-avds"]).stdout.splitlines()
        if args.android_avd not in avds:
            errors.append(f"required Android AVD is unavailable: {args.android_avd}")

    compose_cmd: list[str] | None = None
    if remote:
        _validate_remote_endpoint(str(args.remote_base_url), errors)
    else:
        compose = local_compose
        if compose is None:
            raise RuntimeError("local mode requires --compose")
        if sys.platform != "linux" or not Path("/dev/kvm").exists() or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            errors.append("local full-stack mode requires accessible Linux KVM")
        if not compose.is_file() or not (ROOT / "deploy/compose.e2e.yml").is_file():
            errors.append("local Compose base/e2e files are missing")
        if shutil.which("docker") is None or _run(["docker", "info"]).returncode != 0:
            errors.append("Docker engine is unavailable")
        compose_cmd = ["docker", "compose", "-f", str(compose), "-f", str(ROOT / "deploy/compose.e2e.yml")]

    if errors:
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(evidence_dir, evidence)
        print(f"B-20 E2E gate: mode={run_mode}, result=FAIL (preflight)")
        return 2

    producer_dir.mkdir(parents=True, exist_ok=True)
    for producer_path in (mobile_evidence_path, backend_evidence_path):
        producer_path.unlink(missing_ok=True)

    started = False
    result_code = 1
    try:
        if compose_cmd is not None:
            up = _run([*compose_cmd, "up", "-d", "--wait"])
            evidence["steps"].append({"name": "compose_up", "exit_code": up.returncode})
            if up.returncode != 0:
                errors.append("local Compose stack failed to become ready")
                return 1
            started = True

        configuration = "android.emu.release" if remote else "android.emu.e2e"
        detox_env = {
            "APP_PROFILE": "release" if remote else "e2e_local",
            "DEPLOYMENT_TARGET": "aliyun_ecs" if remote else "local_linux",
            "SYNTHETIC_DATA_ONLY": "1" if args.synthetic_only else "0",
            "E2E_RUN_ID": run_id,
            "E2E_GIT_SHA": git_sha,
            "E2E_TARGET": target,
            "E2E_STARTED_AT": started_at.isoformat(),
            "MOBILE_E2E_EVIDENCE_FILE": str(mobile_evidence_path),
            "BACKEND_E2E_EVIDENCE_FILE": str(backend_evidence_path),
        }
        if remote:
            detox_env["API_BASE_URL"] = str(args.remote_base_url).rstrip("/")
            detox_env["WS_BASE_URL"] = (
                str(args.remote_base_url).replace("https://", "wss://").rstrip("/") + "/v1/realtime"
            )
        else:
            detox_env["API_BASE_URL"] = "http://10.0.2.2:8080"
            detox_env["WS_BASE_URL"] = "ws://10.0.2.2:8080/v1/realtime"
            detox_env["LOCAL_E2E"] = "1"
        detox = _run(
            ["npx", "detox", "test", "--configuration", configuration, "--cleanup"],
            cwd=mobile_dir,
            env=detox_env,
        )
        evidence["steps"].append({"name": "detox", "exit_code": detox.returncode})
        backend = _run([sys.executable, "-m", "pytest", *BACKEND_E2E_TESTS, "-q"], env=detox_env)
        evidence["steps"].append({"name": "backend_evidence", "exit_code": backend.returncode})

        mobile_evidence = _validate_producer_evidence(
            mobile_evidence_path,
            producer="mobile_detox",
            run_id=run_id,
            git_sha=git_sha,
            target=target,
            started_at=started_at,
            errors=errors,
        )
        backend_evidence = _validate_producer_evidence(
            backend_evidence_path,
            producer="backend_pytest",
            run_id=run_id,
            git_sha=git_sha,
            target=target,
            started_at=started_at,
            errors=errors,
        )
        producers = [mobile_evidence, backend_evidence]
        metrics = _merge_metrics(producers, errors)
        evidence["metrics"] = metrics
        evidence["tests_total"] = int(mobile_evidence.get("tests_total", 0)) + int(
            backend_evidence.get("tests_total", 0)
        )
        case_ids = {
            case_id for producer in producers for case_id in producer.get("case_ids", []) if isinstance(case_id, str)
        }
        evidence["case_ids"] = sorted(case_ids)
        if case_ids != REQUIRED_CASE_IDS:
            errors.append("producer evidence does not cover the complete frozen B-20 case matrix")
        for label, path in (("mobile_detox", mobile_evidence_path), ("backend_pytest", backend_evidence_path)):
            if path.is_file():
                evidence["producer_evidence_sha256"][label] = _sha256(path)
        for key, expected in EXPECTED_METRICS.items():
            actual = metrics.get(key)
            if key == "turns_completed":
                if not isinstance(actual, int) or actual < int(expected):
                    errors.append(f"machine metric {key} does not meet the 20-turn minimum")
            elif actual != expected:
                errors.append(f"machine metric {key} is missing or invalid")
        evidence["tests_passed"] = (
            detox.returncode == 0 and backend.returncode == 0 and evidence["tests_total"] > 0 and not errors
        )
        result_code = 0 if evidence["tests_passed"] else 1
    finally:
        if started and compose_cmd is not None:
            down = _run([*compose_cmd, "down", "--volumes", "--remove-orphans"])
            evidence["steps"].append({"name": "compose_down", "exit_code": down.returncode})
            if down.returncode != 0:
                errors.append("Compose cleanup failed")
                evidence["tests_passed"] = False
                result_code = 1
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(evidence_dir, evidence)

    print(f"B-20 E2E gate: mode={run_mode}, result={'PASS' if result_code == 0 else 'FAIL'}")
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
