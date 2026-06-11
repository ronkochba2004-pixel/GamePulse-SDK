from fastapi import APIRouter
from gamepulse_core import BatchEventsRequest, BatchEventsResponse

from app.deps import ProjectIdDep, SupabaseDep
from app.services.ingest_service import ingest_batch

router = APIRouter()


@router.post("/batch", response_model=BatchEventsResponse)
async def post_events_batch(
    req: BatchEventsRequest, project_id: ProjectIdDep, sb: SupabaseDep
) -> BatchEventsResponse:
    return await ingest_batch(sb, project_id, req)


@router.post("", response_model=BatchEventsResponse)
async def post_single_event(
    req: BatchEventsRequest, project_id: ProjectIdDep, sb: SupabaseDep
) -> BatchEventsResponse:
    """Single-event ingestion uses the same batch request with one event."""
    return await ingest_batch(sb, project_id, req)
