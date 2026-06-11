from __future__ import annotations

from typing import Any

from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"


async def insert_crash(sb: SupabaseClient, row: dict[str, Any]) -> str:
    res = sb.schema(SCHEMA).table("crashes").insert(row).execute()
    return res.data[0]["id"]


async def top_crashes(
    sb: SupabaseClient,
    project_id: str,
    limit: int = 20,
    exclude_simulated: bool = False,
) -> list[dict]:
    q = (
        sb.schema(SCHEMA)
        .table("crashes")
        .select("fingerprint, exc_type, message, stacktrace, severity, occurred_at, is_simulated")
        .eq("project_id", project_id)
        .order("occurred_at", desc=True)
        .limit(limit)
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    return q.execute().data or []
