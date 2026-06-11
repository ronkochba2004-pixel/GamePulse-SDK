from __future__ import annotations

from gamepulse_core import BatchEventsRequest, BatchEventsResponse

from app.db.repositories import events as events_repo
from app.db.repositories import players as players_repo
from app.db.supabase import SupabaseClient


async def ingest_batch(
    sb: SupabaseClient, project_id: str, req: BatchEventsRequest
) -> BatchEventsResponse:
    player_id = await players_repo.upsert_player(
        sb,
        project_id=project_id,
        external_id=req.player_external_id,
        platform=(req.device.platform if req.device else None),
        app_version=(req.device.app_version if req.device else None),
    )

    rows = []
    for ev in req.events:
        rows.append(
            {
                "event_id": str(ev.event_id),
                "project_id": project_id,
                "player_id": player_id,
                "session_id": str(ev.session_id) if ev.session_id else None,
                "type": ev.type,
                "category": ev.category if isinstance(ev.category, str) else ev.category.value,
                "name": ev.name,
                "payload": ev.payload,
                "occurred_at": ev.occurred_at.isoformat(),
                "sdk_version": ev.sdk_version,
            }
        )

    inserted = await events_repo.insert_events(sb, rows)
    duplicates = len(rows) - inserted
    return BatchEventsResponse(accepted=inserted, duplicates=max(duplicates, 0))
