from fastapi import APIRouter, status
from gamepulse_core import IdentifyPlayerRequest

from app.db.repositories import players as players_repo
from app.deps import ProjectIdDep, SupabaseDep

router = APIRouter()


@router.post("/identify", status_code=status.HTTP_200_OK)
async def post_identify(
    req: IdentifyPlayerRequest, project_id: ProjectIdDep, sb: SupabaseDep
) -> dict[str, str]:
    player_id = await players_repo.upsert_player(
        sb,
        project_id=project_id,
        external_id=req.external_id,
        country=req.country,
        platform=req.platform.value if req.platform else None,
        app_version=req.app_version,
        attributes=req.attributes,
    )
    return {"player_id": player_id}
