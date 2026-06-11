from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"


async def create_session(
    sb: SupabaseClient,
    *,
    project_id: str,
    player_id: str,
    started_at: datetime,
    platform: str | None,
    app_version: str | None,
    device: dict[str, Any],
) -> str:
    res = (
        sb.schema(SCHEMA)
        .table("sessions")
        .insert(
            {
                "project_id": project_id,
                "player_id": player_id,
                "started_at": started_at.isoformat(),
                "platform": platform,
                "app_version": app_version,
                "device": device,
            }
        )
        .execute()
    )
    return res.data[0]["id"]


async def end_session(
    sb: SupabaseClient,
    *,
    session_id: str,
    ended_at: datetime,
    end_reason: str,
) -> None:
    (
        sb.schema(SCHEMA)
        .table("sessions")
        .update({"ended_at": ended_at.isoformat(), "end_reason": end_reason})
        .eq("id", session_id)
        .execute()
    )


async def recent_sessions(
    sb: SupabaseClient,
    project_id: str,
    limit: int = 50,
    exclude_simulated: bool = False,
) -> list[dict]:
    q = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("*")
        .eq("project_id", project_id)
        .order("started_at", desc=True)
        .limit(limit)
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    return q.execute().data or []
