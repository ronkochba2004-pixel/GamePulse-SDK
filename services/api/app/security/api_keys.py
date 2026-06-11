from __future__ import annotations

from app.db.repositories.projects import find_project_id_by_api_key
from app.db.supabase import SupabaseClient


async def resolve_project_from_api_key(sb: SupabaseClient, api_key: str) -> str | None:
    """Look up the internal project UUID for a given SDK API key.

    Keys are stored hashed; the lookup is exact-match on sha256.
    """
    return await find_project_id_by_api_key(sb, api_key)
