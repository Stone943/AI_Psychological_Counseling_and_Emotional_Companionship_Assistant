"""Guest session Pydantic schemas for REST request/response."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves this at runtime.

from pydantic import BaseModel, ConfigDict, Field


class GuestSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guest_subject_id: str
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)


class GuestSessionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guest_subject_id: str
    created_at: datetime
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)
