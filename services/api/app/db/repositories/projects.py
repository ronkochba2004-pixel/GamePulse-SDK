from __future__ import annotations

import hashlib

from app.db.supabase import SupabaseClient

TABLE = "projects"
SCHEMA = "gamepulse"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def find_project_id_by_api_key(sb: SupabaseClient, api_key: str) -> str | None:
    key_hash = hash_api_key(api_key)
    res = (
        sb.schema(SCHEMA)
        .table(TABLE)
        .select("id")
        .eq("api_key_hash", key_hash)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0]["id"] if rows else None
