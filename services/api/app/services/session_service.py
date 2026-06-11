from __future__ import annotations

from gamepulse_core import SessionEndRequest, SessionStartRequest, SessionStartResponse

from app.db.repositories import players as players_repo
from app.db.repositories import sessions as sessions_repo
from app.db.supabase import SupabaseClient


async def start_session(
    sb: SupabaseClient, project_id: str, req: SessionStartRequest
) -> SessionStartResponse:
    player_id = await players_repo.upsert_player(
        sb,
        project_id=project_id,
        external_id=req.player_external_id,
        platform=(req.device.platform if req.device else None),
        app_version=req.app_version or (req.device.app_version if req.device else None),
    )
    session_id = await sessions_repo.create_session(
        sb,
        project_id=project_id,
        player_id=player_id,
        started_at=req.started_at,
        platform=(req.device.platform if req.device else None),
        app_version=req.app_version,
        device=req.device.model_dump() if req.device else {},
    )
    return SessionStartResponse(session_id=session_id, player_id=player_id)


async def end_session(sb: SupabaseClient, req: SessionEndRequest) -> None:
    reason = req.end_reason if isinstance(req.end_reason, str) else req.end_reason.value
    await sessions_repo.end_session(
        sb,
        session_id=str(req.session_id),
        ended_at=req.ended_at,
        end_reason=reason,
    )
