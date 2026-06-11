from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.db.supabase import SupabaseClient, get_supabase
from app.security.api_keys import resolve_project_from_api_key


async def current_project_id(
    api_key: Annotated[str | None, Header(alias="X-GamePulse-Key")] = None,
    sb: SupabaseClient = Depends(get_supabase),
) -> str:
    if not api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing X-GamePulse-Key")
    project_id = await resolve_project_from_api_key(sb, api_key)
    if not project_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return project_id


SupabaseDep = Annotated[SupabaseClient, Depends(get_supabase)]
ProjectIdDep = Annotated[str, Depends(current_project_id)]
