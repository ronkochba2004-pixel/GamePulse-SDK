from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from gamepulse_core.enums import EventCategory, SessionEndReason, Severity


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BaseEvent(BaseModel):
    """Wire-format event. SDK constructs these; API validates them."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    type: str
    category: EventCategory
    name: str
    occurred_at: datetime = Field(default_factory=_utcnow)
    session_id: UUID | None = None
    player_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    sdk_version: str | None = None


# ---------- System ----------

class SessionStartEvent(BaseEvent):
    category: EventCategory = EventCategory.SYSTEM
    type: str = "system.session_start"
    name: str = "session_start"


class SessionEndEvent(BaseEvent):
    category: EventCategory = EventCategory.SYSTEM
    type: str = "system.session_end"
    name: str = "session_end"
    end_reason: SessionEndReason = SessionEndReason.NORMAL


# ---------- Progression ----------

class LevelStartEvent(BaseEvent):
    category: EventCategory = EventCategory.PROGRESSION
    type: str = "progression.level_start"
    name: str = "level_start"


class LevelCompleteEvent(BaseEvent):
    category: EventCategory = EventCategory.PROGRESSION
    type: str = "progression.level_complete"
    name: str = "level_complete"


class LevelFailEvent(BaseEvent):
    category: EventCategory = EventCategory.PROGRESSION
    type: str = "progression.level_fail"
    name: str = "level_fail"


# ---------- Economy ----------

class CurrencyEarnEvent(BaseEvent):
    category: EventCategory = EventCategory.ECONOMY
    type: str = "economy.currency_earn"
    name: str = "currency_earn"


class CurrencySpendEvent(BaseEvent):
    category: EventCategory = EventCategory.ECONOMY
    type: str = "economy.currency_spend"
    name: str = "currency_spend"


# ---------- Gameplay ----------

class GameplayEvent(BaseEvent):
    category: EventCategory = EventCategory.GAMEPLAY
    type: str = "gameplay.action"
    name: str = "action"


# ---------- Errors ----------

class CrashEvent(BaseEvent):
    category: EventCategory = EventCategory.ERROR
    type: str = "error.crash"
    name: str = "crash"
    severity: Severity = Severity.ERROR


# ---------- Custom ----------

class CustomEvent(BaseEvent):
    category: EventCategory = EventCategory.CUSTOM
    type: str = "custom.event"
    name: str = "event"
