# ruff: noqa: E501
"""Context reference builder for FreeTextSafetyRequest. B constructs this from auth context."""

from __future__ import annotations


def build_context_ref(entry_point: str, **kwargs: str) -> str:
    """Build a context_ref string from entry_point and contextual IDs."""
    builders: dict[str, callable] = {
        "chat.message": lambda **kw: f"conversation:{kw['conversation_id']}",
        "conversation.title": lambda **kw: (
            f"conversation:{kw['conversation_id']}"
            if kw.get("conversation_id")
            else f"subject:{kw['subject_id']}:new-conversation"
        ),
        "feedback.comment": lambda **kw: f"response:{kw.get('target_id', 'unknown')}",
        "exercise.reflection": lambda **kw: f"exercise-session:{kw['session_id']}:entry:{kw.get('entry_id', 'new')}",
        "emotion.correction_note": lambda **kw: f"emotion-result:{kw['emotion_result_id']}",
        "memory.value": lambda **kw: (
            f"memory:{kw['memory_id']}" if kw.get("memory_id") else f"subject:{kw['subject_id']}:new-memory"
        ),
        "knowledge.search": lambda **kw: f"subject:{kw['subject_id']}:knowledge-search",
        "assessment.optional_note": lambda **kw: f"assessment:{kw['scale']}:{kw['version']}",
        "profile.nickname": lambda **kw: f"profile:{kw['subject_id']}",
        "guest_migration.label": lambda **kw: f"guest-migration:{kw['batch_id']}:item:{kw['item_id']}",
    }
    builder = builders.get(entry_point)
    if builder is None:
        raise ValueError(f"Unknown entry_point: {entry_point}")
    return builder(**kwargs)
