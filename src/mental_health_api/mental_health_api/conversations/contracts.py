"""Conversation Pydantic schemas."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import datetime


class PersistenceMode(str, Enum):
    ephemeral = "ephemeral"
    saved = "saved"


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    persistence_mode: PersistenceMode = PersistenceMode.saved


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str
    subject_id: str
    title: str | None = None
    mode: str = "chat"
    persistence_mode: str = "saved"
    risk_state: str = "L0"
    next_event_sequence: int = 0
    created_at: datetime
    updated_at: datetime
