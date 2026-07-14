# ruff: noqa: E501
"""Ten free-text entry points — PRD 14.1 frozen set. Adding an entry requires contract version bump."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreeTextEntry:
    entry_point: str
    route_pattern: str
    field_name: str
    max_length: int
    description: str


# v1 frozen entries — PRD 14.1 exact set
ENTRIES: dict[str, FreeTextEntry] = {
    "chat.message": FreeTextEntry("chat.message", "/v1/realtime", "payload.text", 10000, "Chat message via WebSocket"),
    "conversation.title": FreeTextEntry(
        "conversation.title", "/v1/conversations", "title", 256, "Conversation title (create/patch)"
    ),
    "feedback.comment": FreeTextEntry("feedback.comment", "/v1/feedback", "comment", 2000, "Feedback optional comment"),
    "exercise.reflection": FreeTextEntry(
        "exercise.reflection", "/v1/exercise-sessions", "text", 5000, "Exercise reflection entry"
    ),
    "emotion.correction_note": FreeTextEntry(
        "emotion.correction_note", "/v1/emotions", "correction_note", 2000, "Emotion correction note"
    ),
    "memory.value": FreeTextEntry("memory.value", "/v1/memories", "value", 5000, "Memory item value"),
    "knowledge.search": FreeTextEntry(
        "knowledge.search", "/v1/knowledge/search", "query", 1000, "Knowledge search query"
    ),
    "assessment.optional_note": FreeTextEntry(
        "assessment.optional_note", "/v1/assessments", "optional_note", 2000, "Assessment optional note"
    ),
    "profile.nickname": FreeTextEntry("profile.nickname", "/v1/profile", "nickname", 128, "User profile nickname"),
    "guest_migration.label": FreeTextEntry(
        "guest_migration.label", "/v1/guest-migrations", "items[*].label", 256, "Guest migration item label"
    ),
}


def is_registered(entry_point: str) -> bool:
    return entry_point in ENTRIES


def get_entry(entry_point: str) -> FreeTextEntry | None:
    return ENTRIES.get(entry_point)
