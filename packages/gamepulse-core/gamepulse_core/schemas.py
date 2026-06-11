from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from gamepulse_core.constants import MAX_BATCH_SIZE
from gamepulse_core.enums import Platform, SessionEndReason, Severity
from gamepulse_core.events import BaseEvent


class DeviceContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    platform: Platform = Platform.UNKNOWN
    os_version: str | None = None
    locale: str | None = None
    python_version: str | None = None
    app_version: str | None = None


# ---------- Players ----------

class IdentifyPlayerRequest(BaseModel):
    external_id: str
    country: str | None = None
    platform: Platform | None = None
    app_version: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


# ---------- Sessions ----------

class SessionStartRequest(BaseModel):
    player_external_id: str
    started_at: datetime
    device: DeviceContext = Field(default_factory=DeviceContext)
    app_version: str | None = None


class SessionStartResponse(BaseModel):
    session_id: UUID
    player_id: UUID


class SessionEndRequest(BaseModel):
    session_id: UUID
    ended_at: datetime
    end_reason: SessionEndReason = SessionEndReason.NORMAL


# ---------- Events ----------

class BatchEventsRequest(BaseModel):
    player_external_id: str
    events: list[BaseEvent] = Field(..., max_length=MAX_BATCH_SIZE)
    device: DeviceContext | None = None


class BatchEventsResponse(BaseModel):
    accepted: int
    rejected: int = 0
    duplicates: int = 0


# ---------- Crashes ----------

class CrashIngestRequest(BaseModel):
    player_external_id: str
    session_id: UUID | None = None
    fingerprint: str
    exc_type: str
    message: str | None = None
    stacktrace: str
    severity: Severity = Severity.ERROR
    occurred_at: datetime
    context: dict[str, Any] = Field(default_factory=dict)
