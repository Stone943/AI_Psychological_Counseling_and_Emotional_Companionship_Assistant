#!/usr/bin/env python
# ruff: noqa: E501  # long JSON-embedded strings are fine in export scripts
"""Generate OpenAPI 3.1 spec from FastAPI app and contracts.

Usage:
    uv run python scripts/export_openapi.py --write   # write openapi.json
    uv run python scripts/export_openapi.py --check   # byte-compare with existing file
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "openapi.json"


def build_openapi_spec() -> dict:
    """Build the OpenAPI specification from the FastAPI app and contract models."""
    # For B-02, we generate a skeleton OpenAPI from the contract models.
    # Full route registration happens in B-04 through B-17.
    from mental_health_api.contracts.public_errors import CANONICAL_ERRORS

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Mental Health API",
            "description": "AI Psychological Counseling and Emotional Companionship Assistant — Backend API",
            "version": "0.1.0",
        },
        "servers": [
            {"url": "https://localhost", "description": "Demo / Production"},
            {"url": "http://localhost:8000", "description": "Local development"},
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "operationId": "health_check",
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"status": {"type": "string"}, "version": {"type": "string"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "PublicError": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "request_id": {"type": "string"},
                        "retryable": {"type": "boolean"},
                        "client_action": {"type": "string"},
                        "retry_after_seconds": {"type": "integer"},
                    },
                    "required": ["code", "retryable", "client_action"],
                    "additionalProperties": False,
                },
            }
        },
    }

    # Add error code documentation
    errors_doc: dict[str, dict] = {}
    for code, spec_err in sorted(CANONICAL_ERRORS.items()):
        errors_doc[code] = {
            "http_status": spec_err.http_status,
            "retryable": spec_err.retryable,
            "client_action": spec_err.client_action,
        }
    spec["info"]["x-error-codes"] = errors_doc  # type: ignore[index]

    return spec


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("--write", "--check"):
        print("Usage: python scripts/export_openapi.py [--write|--check]")
        sys.exit(1)

    command = sys.argv[1]
    spec = build_openapi_spec()
    content = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
    content_bytes = content.encode("utf-8")

    if command == "--write":
        OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
        OPENAPI_PATH.write_bytes(content_bytes)
        print(f"Wrote: {OPENAPI_PATH} ({len(content_bytes)} bytes)")
    elif command == "--check":
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(content_bytes)
            tmp_path = Path(tmp.name)

        try:
            existing = OPENAPI_PATH.read_bytes()
            if existing != content_bytes:
                print(f"ERROR: {OPENAPI_PATH} differs from generated output.")
                print(f"  Existing: {len(existing)} bytes")
                print(f"  Generated: {len(content_bytes)} bytes")
                print(f"  Temp file: {tmp_path}")
                print("  Run --write to regenerate.")
                sys.exit(1)
            print(f"OK: {OPENAPI_PATH} matches generated output ({len(content_bytes)} bytes)")
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
