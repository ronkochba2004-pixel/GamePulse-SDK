from fastapi import APIRouter, status
from gamepulse_core import CrashIngestRequest

from app.db.repositories import crashes as crashes_repo
from app.db.repositories import players as players_repo
from app.deps import ProjectIdDep, SupabaseDep

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_crash(
    req: CrashIngestRequest, project_id: ProjectIdDep, sb: SupabaseDep
) -> dict[str, str]:
    player_id = await players_repo.upsert_player(
        sb, project_id=project_id, external_id=req.player_external_id
    )
    row = {
        "project_id": project_id,
        "player_id": player_id,
        "session_id": str(req.session_id) if req.session_id else None,
        "fingerprint": req.fingerprint,
        "exc_type": req.exc_type,
        "message": req.message,
        "stacktrace": req.stacktrace,
        # Severity is a str-subclass enum, so isinstance(str) is always True;
        # extract .value explicitly to store "fatal" rather than the enum repr.
        "severity": getattr(req.severity, "value", req.severity),
        "occurred_at": req.occurred_at.isoformat(),
        "context": req.context,
    }
    crash_id = await crashes_repo.insert_crash(sb, row)
    return {"id": crash_id}
