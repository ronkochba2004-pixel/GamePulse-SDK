from __future__ import annotations

from typing import Any

from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"


async def insert_events(sb: SupabaseClient, rows: list[dict[str, Any]]) -> int:
    """Insert a batch of events. (project_id, event_id) unique → duplicates ignored.

    Returns the number of rows actually inserted (excludes duplicates).
    """
    if not rows:
        return 0
    res = (
        sb.schema(SCHEMA)
        .table("events")
        .upsert(rows, on_conflict="project_id,event_id", ignore_duplicates=True)
        .execute()
    )
    return len(res.data or [])
