from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"


async def upsert_player(
    sb: SupabaseClient,
    project_id: str,
    external_id: str,
    *,
    country: str | None = None,
    platform: str | None = None,
    app_version: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> str:
    """Upsert and return internal player UUID."""
    payload = {
        "project_id": project_id,
        "external_id": external_id,
        "last_seen_at": datetime.now(UTC).isoformat(),
    }
    if country is not None:
        payload["country"] = country
    if platform is not None:
        payload["platform"] = platform
    if app_version is not None:
        payload["app_version"] = app_version
    if attributes is not None:
        payload["attributes"] = attributes

    res = (
        sb.schema(SCHEMA)
        .table("players")
        .upsert(payload, on_conflict="project_id,external_id")
        .execute()
    )
    rows = res.data or []
    if rows:
        return rows[0]["id"]

    # fallback select if upsert did not return the row
    sel = (
        sb.schema(SCHEMA)
        .table("players")
        .select("id")
        .eq("project_id", project_id)
        .eq("external_id", external_id)
        .limit(1)
        .execute()
    )
    return sel.data[0]["id"]
