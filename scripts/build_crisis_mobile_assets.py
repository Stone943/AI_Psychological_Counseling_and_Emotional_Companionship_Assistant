"""Verify and copy signed crisis public assets into an existing mobile project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mental_health_api.crisis.signing import verify_trusted_bundle

SERVER_BUNDLE = Path("content/crisis/offline-bundle.zh-CN.v1.json")
SERVER_KEYS = Path("content/crisis/trusted-keys.json")
MOBILE_DIR = Path("mobile/src/assets/crisis")


def _validated_bytes() -> tuple[bytes, bytes]:
    bundle_bytes = SERVER_BUNDLE.read_bytes()
    key_bytes = SERVER_KEYS.read_bytes()
    bundle = json.loads(bundle_bytes)
    registry = json.loads(key_bytes)
    valid, reason = verify_trusted_bundle(bundle, registry)
    if not valid:
        raise ValueError(f"crisis bundle validation failed: {reason}")
    return bundle_bytes, key_bytes


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    bundle_bytes, key_bytes = _validated_bytes()
    if not Path("mobile").is_dir():
        raise SystemExit("Member C mobile project is unavailable")
    targets = {
        MOBILE_DIR / SERVER_BUNDLE.name: bundle_bytes,
        MOBILE_DIR / SERVER_KEYS.name: key_bytes,
    }
    if args.write:
        MOBILE_DIR.mkdir(parents=True, exist_ok=True)
        for path, payload in targets.items():
            path.write_bytes(payload)
        return 0
    for path, payload in targets.items():
        if not path.exists() or path.read_bytes() != payload:
            raise SystemExit(f"mobile crisis asset drift: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
