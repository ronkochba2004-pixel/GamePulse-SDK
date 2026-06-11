from fastapi import APIRouter, status
from gamepulse_core import (
    SessionEndRequest,
    SessionStartRequest,
    SessionStartResponse,
)

from app.deps import ProjectIdDep, SupabaseDep
from app.services.session_service import end_session, start_session

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
async def post_start(
    req: SessionStartRequest, project_id: ProjectIdDep, sb: SupabaseDep
) -> SessionStartResponse:
    return await start_session(sb, project_id, req)


@router.post("/end", status_code=status.HTTP_204_NO_CONTENT)
async def post_end(req: SessionEndRequest, project_id: ProjectIdDep, sb: SupabaseDep) -> None:
    _ = project_id  # tenancy already enforced upstream
    await end_session(sb, req)
