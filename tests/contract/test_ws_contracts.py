"""Verify WS contract invariants: ClientCommandEnvelope has no sequence,
ServerEventEnvelope has sequence >= 0, type enums match PRD.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def load_schema(filename: str) -> dict:
    path = ROOT / "contracts" / "ws" / filename
    assert path.exists(), f"{path} does not exist"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ws_dir() -> Path:
    return ROOT / "contracts" / "ws"


class TestClientCommands:
    """ClientCommandEnvelope invariants."""

    def test_file_exists(self) -> None:
        assert (ws_dir() / "client_commands.schema.json").exists()

    def test_no_sequence_field(self) -> None:
        schema = load_schema("client_commands.schema.json")
        props = schema.get("properties", {})
        assert "sequence" not in props, "ClientCommandEnvelope MUST NOT contain sequence"

    def test_type_enum_exact(self) -> None:
        schema = load_schema("client_commands.schema.json")
        types = schema["properties"]["type"]["enum"]
        expected = {"message.send", "generation.cancel", "session.resume", "session.ack", "safety.answer"}
        assert set(types) == expected

    def test_rejects_unknown_fields(self) -> None:
        schema = load_schema("client_commands.schema.json")
        assert schema["additionalProperties"] is False


class TestServerEvents:
    """ServerEventEnvelope invariants."""

    def test_file_exists(self) -> None:
        assert (ws_dir() / "server_events.schema.json").exists()

    def test_has_sequence_field(self) -> None:
        schema = load_schema("server_events.schema.json")
        props = schema.get("properties", {})
        assert "sequence" in props, "ServerEventEnvelope MUST contain sequence"
        assert props["sequence"]["minimum"] == 0

    def test_type_enum_exact(self) -> None:
        schema = load_schema("server_events.schema.json")
        types = schema["properties"]["type"]["enum"]
        expected = {
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
        }
        assert set(types) == expected

    def test_rejects_unknown_fields(self) -> None:
        schema = load_schema("server_events.schema.json")
        assert schema["additionalProperties"] is False


class TestPythonModels:
    """Python models match JSON schemas."""

    def test_client_envelope_no_sequence(self) -> None:
        from mental_health_api.contracts.models import ClientCommandEnvelope

        fields = ClientCommandEnvelope.model_fields
        assert "sequence" not in fields, "ClientCommandEnvelope model MUST NOT have sequence"

    def test_server_envelope_has_sequence(self) -> None:
        from mental_health_api.contracts.models import ServerEventEnvelope

        fields = ServerEventEnvelope.model_fields
        assert "sequence" in fields, "ServerEventEnvelope model MUST have sequence"

    def test_server_envelope_extra_forbid(self) -> None:
        from mental_health_api.contracts.models import ServerEventEnvelope

        assert ServerEventEnvelope.model_config.get("extra") == "forbid"


def test_canonical_rows_exist() -> None:
    path = ws_dir() / "canonical_rows.json"
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == "v1"
    assert len(data["client_command_types"]) == 5
    assert len(data["server_event_types"]) == 11
