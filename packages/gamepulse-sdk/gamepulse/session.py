from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass(slots=True)
class Session:
    id: UUID | None
    player_id: UUID | None
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None

    @classmethod
    def new_local(cls) -> Session:
        return cls(id=None, player_id=None, started_at=datetime.now(UTC))
