"""Generate a one-time, local-only Ed25519 demo key and public registry."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mental_health_api.crisis.signing import private_seed, public_key_b64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-key-file", required=True, type=Path)
    parser.add_argument("--trusted-keys", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args()
    if args.private_key_file.exists():
        parser.error("private key already exists; refusing to overwrite")
    repo_root = Path(__file__).resolve().parents[1]
    secret_root = (repo_root / ".local" / "secrets").resolve()
    candidate = args.private_key_file.resolve(strict=False)
    if not candidate.is_relative_to(secret_root):
        parser.error("demo private keys must live below .local/secrets")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if candidate.parent.resolve() != candidate.parent or candidate.is_symlink():
        parser.error("demo private key path must not escape through a symbolic link")

    key = Ed25519PrivateKey.generate()
    fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(private_seed(key))
    os.chmod(candidate, 0o600)

    now = datetime.now(UTC).replace(microsecond=0)
    registry = {
        "version": "1",
        "keys": [
            {
                "key_id": args.key_id,
                "public_key": public_key_b64(key.public_key()),
                "status": "active",
                "not_before": now.isoformat().replace("+00:00", "Z"),
                "not_after": (now + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
                "revoked_at": None,
            }
        ],
    }
    args.trusted_keys.parent.mkdir(parents=True, exist_ok=True)
    args.trusted_keys.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
