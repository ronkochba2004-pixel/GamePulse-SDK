from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.settings import get_settings

SupabaseClient = Client


@lru_cache
def _client() -> SupabaseClient:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


def get_supabase() -> SupabaseClient:
    return _client()
