#!/usr/bin/env python
# ruff: noqa: E501  # long JSON strings in export scripts
"""Generate WebSocket contract JSON Schemas from Python models.

Usage:
    uv run python scripts/export_ws_contracts.py --write
    uv run python scripts/export_ws_contracts.py --check
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS_DIR = ROOT / "contracts" / "ws"


def build_client_commands_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://mental-health-platform/contracts/ws/client_commands.schema.json",
        "title": "ClientCommandEnvelope",
        "description": "WebSocket command sent by the client. MUST NOT contain sequence.",
        "type": "object",
        "properties": {
            "protocol_version": {"type": "string", "const": "v1"},
            "command_id": {"type": "string"},
            "conversation_id": {"type": "string"},
            "idempotency_key": {"type": "string"},
            "sent_at": {"type": "string", "format": "date-time"},
            "type": {
                "type": "string",
                "enum": ["message.send", "generation.cancel", "session.resume", "session.ack", "safety.answer"],
            },
            "payload": {"type": "object"},
        },
        "required": [
            "protocol_version",
            "command_id",
            "conversation_id",
            "idempotency_key",
            "sent_at",
            "type",
            "payload",
        ],
        "additionalProperties": False,
    }


def build_server_events_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://mental-health-platform/contracts/ws/server_events.schema.json",
        "title": "ServerEventEnvelope",
        "description": "WebSocket event sent by the server. B is the sole allocator of sequence. First sequence per conversation MUST be 0.",
        "type": "object",
        "properties": {
            "protocol_version": {"type": "string", "const": "v1"},
            "event_id": {"type": "string"},
            "conversation_id": {"type": "string"},
            "message_id": {"type": "string"},
            "sequence": {"type": "integer", "minimum": 0},
            "idempotency_key": {"type": "string"},
            "occurred_at": {"type": "string", "format": "date-time"},
            "type": {
                "type": "string",
                "enum": [
                    "message.accepted",
                    "risk.status",
                    "emotion.result",
                    "response.delta",
                    "response.completed",
                    "response.blocked",
                    "safety.question",
                    "safety.resources",
                    "assessment.result.available",
                    "memory.mode.changed",
                    "error",
                ],
            },
            "payload": {"type": "object"},
        },
        "required": [
            "protocol_version",
            "event_id",
            "conversation_id",
            "sequence",
            "idempotency_key",
            "occurred_at",
            "type",
            "payload",
        ],
        "additionalProperties": False,
    }


def build_canonical_rows() -> dict:
    return {
        "version": "v1",
        "client_command_types": ["message.send", "generation.cancel", "session.resume", "session.ack", "safety.answer"],
        "server_event_types": [
            "message.accepted",
            "risk.status",
            "emotion.result",
            "response.delta",
            "response.completed",
            "response.blocked",
            "safety.question",
            "safety.resources",
            "assessment.result.available",
            "memory.mode.changed",
            "error",
        ],
        "invariants": [
            "ClientCommandEnvelope MUST NOT contain sequence",
            "ServerEventEnvelope.sequence starts at 0 per conversation_id",
            "ServerEventEnvelope.sequence is monotonically increasing within a conversation",
            "B is the sole allocator of sequence; A never reads or reserves sequence",
            "message_ordinal is separate from WS event sequence",
        ],
    }


FILES = {
    "client_commands.schema.json": build_client_commands_schema,
    "server_events.schema.json": build_server_events_schema,
    "canonical_rows.json": build_canonical_rows,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("--write", "--check"):
        print("Usage: python scripts/export_ws_contracts.py [--write|--check]")
        sys.exit(1)

    command = sys.argv[1]

    for filename, builder in FILES.items():
        spec = builder()
        content = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
        content_bytes = content.encode("utf-8")
        target = WS_DIR / filename

        if command == "--write":
            WS_DIR.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content_bytes)
            print(f"Wrote: {target} ({len(content_bytes)} bytes)")
        elif command == "--check":
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                tmp.write(content_bytes)
                tmp_path = Path(tmp.name)
            try:
                if not target.exists():
                    print(f"ERROR: {target} does not exist. Run --write first.")
                    tmp_path.unlink(missing_ok=True)
                    sys.exit(1)
                existing = target.read_bytes()
                if existing != content_bytes:
                    print(f"ERROR: {target} differs from generated output.")
                    print(f"  Temp: {tmp_path}")
                    print("  Run --write to regenerate.")
                    tmp_path.unlink(missing_ok=True)
                    sys.exit(1)
                print(f"OK: {target}")
            finally:
                tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
