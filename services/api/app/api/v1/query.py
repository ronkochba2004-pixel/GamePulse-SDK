from fastapi import APIRouter, Query

from app.deps import ProjectIdDep, SupabaseDep
from app.services import analytics_service

router = APIRouter()


@router.get("/overview")
async def get_overview(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(7, ge=1, le=90),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.overview(sb, project_id, days=days, exclude_simulated=exclude_simulated)


@router.get("/crashes/top")
async def get_top_crashes(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    limit: int = Query(20, ge=1, le=200),
    exclude_simulated: bool = Query(False),
) -> list[dict]:
    return await analytics_service.top_crashes(sb, project_id, limit=limit, exclude_simulated=exclude_simulated)


@router.get("/sessions/analytics")
async def get_session_analytics(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(500, ge=1, le=2000),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.session_analytics(
        sb, project_id, days=days, limit=limit, exclude_simulated=exclude_simulated
    )


@router.get("/crashes/analytics")
async def get_crash_analytics(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(14, ge=1, le=90),
    severity: str | None = Query(None),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.crash_analytics(
        sb, project_id, days=days, severity=severity, exclude_simulated=exclude_simulated
    )


@router.get("/rage-quits")
async def get_rage_quits(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(14, ge=1, le=90),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.rage_quit_analytics(
        sb, project_id, days=days, exclude_simulated=exclude_simulated
    )


@router.get("/sessions/recent")
async def get_recent_sessions(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    limit: int = Query(50, ge=1, le=500),
    exclude_simulated: bool = Query(False),
) -> list[dict]:
    return await analytics_service.recent_sessions(sb, project_id, limit=limit, exclude_simulated=exclude_simulated)


@router.get("/players")
async def get_players(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, ge=1, le=2000),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.players_summary(
        sb, project_id, days=days, limit=limit, exclude_simulated=exclude_simulated
    )


@router.get("/progression/funnel")
async def get_progression_funnel(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(7, ge=1, le=90),
    max_level: int = Query(10, ge=1, le=50),
    exclude_simulated: bool = Query(False),
) -> list[dict]:
    return await analytics_service.progression_funnel(
        sb, project_id, days=days, max_level=max_level, exclude_simulated=exclude_simulated
    )


@router.get("/economy/summary")
async def get_economy_summary(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    days: int = Query(30, ge=1, le=365),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.economy_summary(sb, project_id, days=days, exclude_simulated=exclude_simulated)


@router.get("/events/recent")
async def get_recent_events(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    limit: int = Query(200, ge=1, le=1000),
    category: str | None = Query(None),
    exclude_simulated: bool = Query(False),
) -> list[dict]:
    return await analytics_service.recent_events(
        sb, project_id, limit=limit, category=category, exclude_simulated=exclude_simulated
    )


@router.get("/retention")
async def get_retention(
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    cohort_days: int = Query(14, ge=3, le=90),
    max_day_n: int = Query(7, ge=1, le=14),
    exclude_simulated: bool = Query(False),
) -> dict:
    return await analytics_service.retention_cohort(
        sb, project_id, cohort_days=cohort_days, max_day_n=max_day_n, exclude_simulated=exclude_simulated
    )


@router.get("/players/{player_external_id}/timeline")
async def get_player_timeline(
    player_external_id: str,
    project_id: ProjectIdDep,
    sb: SupabaseDep,
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    return await analytics_service.player_timeline(
        sb, project_id, player_external_id, limit=limit
    )


@router.get("/project")
async def get_project(project_id: ProjectIdDep, sb: SupabaseDep) -> dict:
    return await analytics_service.project_info(sb, project_id)
