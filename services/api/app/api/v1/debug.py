from __future__ import annotations

from fastapi import APIRouter

from app.deps import SupabaseDep

router = APIRouter(tags=["debug"])

SCHEMA = "gamepulse"
REQUIRED_TABLES = ["projects", "players", "sessions", "events", "crashes"]


@router.get("/debug/connectivity")
async def connectivity_check(sb: SupabaseDep) -> dict:
    """
    Tests Supabase connectivity and gamepulse schema access.
    Returns a detailed report — useful for initial setup debugging.
    Remove or gate behind auth in production.
    """
    results: dict = {"schema": SCHEMA, "tables": {}}
    schema_ok = True

    for table in REQUIRED_TABLES:
        try:
            res = sb.schema(SCHEMA).table(table).select("count", count="exact").limit(0).execute()
            results["tables"][table] = {"ok": True, "count": res.count}
        except Exception as e:
            schema_ok = False
            results["tables"][table] = {"ok": False, "error": str(e)}

    results["schema_accessible"] = schema_ok
    if not schema_ok:
        results["fix"] = (
            f"Add '{SCHEMA}' to Supabase exposed schemas: "
            "Dashboard → Settings → API → Exposed schemas"
        )
    return results
