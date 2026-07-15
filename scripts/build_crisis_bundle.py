"""Build or verify the signed China-mainland crisis offline bundle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mental_health_api.crisis.jcs import canonicalize
from mental_health_api.crisis.release_validation import validate_register, validate_release
from mental_health_api.crisis.signing import load_private_key, sign_bundle

SOURCE = Path("content/crisis/china-mainland.zh-CN.v1.json")
OUTPUT = Path("content/crisis/offline-bundle.zh-CN.v1.json")
VECTORS = Path("contracts/crisis/canonical_vectors.json")
REVIEW_REGISTER = Path("content/reviews/review-register.json")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _build(
    source: dict[str, Any], review_register: list[dict[str, Any]], key_file: Path, key_id: str
) -> dict[str, Any]:
    if source.get("status") != "published":
        raise ValueError("crisis source is not published")
    validate_register(review_register)
    validate_release(source, review_register)
    now = datetime.now(UTC)
    verified_at = datetime.fromisoformat(str(source["verified_at"]).replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(str(source["expires_at"]).replace("Z", "+00:00"))
    if verified_at.tzinfo is None or expires_at.tzinfo is None or verified_at > now or now >= expires_at:
        raise ValueError("crisis source validity window is invalid")
    resources = source.get("resources")
    if not isinstance(resources, list):
        raise ValueError("crisis resources must be a list")
    numbers = {str(item.get("number")) for item in resources if isinstance(item, dict)}
    if not {"110", "120", "12356"}.issubset(numbers):
        raise ValueError("crisis source must include 110, 120 and 12356")
    unsigned = {
        "bundle_version": source["version"],
        "resource_status": "active",
        "degraded_reason": None,
        "verified_at": source["verified_at"],
        "expires_at": source["expires_at"],
        "resources": resources,
    }
    return sign_bundle(unsigned, load_private_key(key_file), key_id=key_id)


def _check_vectors() -> int:
    rows = _load_json(VECTORS)
    if not isinstance(rows, list):
        raise ValueError("canonical vectors must be an array")
    for row in rows:
        actual = canonicalize(row["value"]).decode("utf-8")
        if actual != row["canonical"]:
            raise ValueError(f"canonical vector failed: {row['id']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--check-vectors", action="store_true")
    parser.add_argument("--key-id")
    args = parser.parse_args()
    if args.check_vectors:
        return _check_vectors()
    key_path = os.environ.get("CRISIS_SIGNING_KEY_FILE")
    if not key_path or not args.key_id:
        parser.error("CRISIS_SIGNING_KEY_FILE and --key-id are required")
    source = _load_json(SOURCE)
    review_register = _load_json(REVIEW_REGISTER)
    if not isinstance(source, dict) or not isinstance(review_register, list):
        raise ValueError("crisis source/review register shape is invalid")
    built = _build(source, review_register, Path(key_path), args.key_id)
    rendered = json.dumps(built, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
        return 0
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=True) as candidate:
        candidate.write(rendered)
        candidate.flush()
        if not OUTPUT.exists() or OUTPUT.read_bytes() != Path(candidate.name).read_bytes():
            raise SystemExit("signed crisis bundle drift detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
