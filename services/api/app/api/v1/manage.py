from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.db.repositories.projects import hash_api_key
from app.deps import SupabaseDep
from app.security.auth import UserDep
from app.services import analytics_service
from app.services.simulator_service import SimParams, SimResult, run_simulation

SCHEMA = "gamepulse"
router = APIRouter(prefix="/manage", tags=["manage"])


class CreateProjectRequest(BaseModel):
    name: str
    slug: str


@router.get("/projects")
async def list_projects(sb: SupabaseDep, user: UserDep) -> list:
    user_id = user.get("sub")
    res = sb.schema(SCHEMA).table("projects").select("*").eq("owner_id", user_id).execute()
    return res.data or []


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest, sb: SupabaseDep, user: UserDep) -> dict:
    existing = sb.schema(SCHEMA).table("projects").select("id").eq("slug", body.slug).execute()
    if existing.data:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already taken")

    api_key = f"gpk_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(api_key)

    res = sb.schema(SCHEMA).table("projects").insert({
        "name": body.name,
        "slug": body.slug,
        "api_key_hash": key_hash,
        "api_key": api_key,
        "owner_id": user.get("sub"),
    }).execute()

    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project")

    return res.data[0]


@router.get("/projects/{project_id}/config")
async def get_project_config(project_id: str, sb: SupabaseDep, user: UserDep) -> dict:
    res = (
        sb.schema(SCHEMA).table("projects")
        .select("*")
        .eq("id", project_id)
        .eq("owner_id", user.get("sub"))
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return res.data[0]


@router.post("/projects/{project_id}/rotate-key")
async def rotate_api_key(project_id: str, sb: SupabaseDep, user: UserDep) -> dict:
    res = (
        sb.schema(SCHEMA).table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("owner_id", user.get("sub"))
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    new_key = f"gpk_{secrets.token_urlsafe(32)}"
    new_hash = hash_api_key(new_key)

    sb.schema(SCHEMA).table("projects").update({
        "api_key_hash": new_hash,
        "api_key": new_key,
    }).eq("id", project_id).execute()

    return {"api_key": new_key, "message": "Key rotated successfully"}


# ── Simulation ─────────────────────────────────────────────────────────────────

_VALID_PERSONAS = {"casual", "whale", "rage_quitter", "crasher"}


class SimulateRequest(BaseModel):
    players: int = Field(default=30, ge=1, le=200)
    time_spread_days: int = Field(default=7, ge=1, le=90)
    crash_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    rage_quit_rate: float = Field(default=0.10, ge=0.0, le=1.0)
    level_fail_rate: float = Field(default=0.35, ge=0.0, le=1.0)
    spend_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    persona_mix: dict[str, float] | None = Field(default=None)


class SimulateResponse(BaseModel):
    players_created: int
    sessions_created: int
    events_generated: int
    crashes_generated: int
    rage_quits_generated: int
    economy_events_generated: int
    elapsed_s: float


@router.post("/projects/{project_id}/simulate", response_model=SimulateResponse)
async def simulate_project(
    project_id: str,
    body: SimulateRequest,
    sb: SupabaseDep,
    user: UserDep,
) -> SimulateResponse:
    """Generate realistic fake telemetry data for a project (demo/academic feature)."""
    res = (
        sb.schema(SCHEMA).table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("owner_id", user.get("sub"))
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Build & validate persona mix
    if body.persona_mix:
        unknown = set(body.persona_mix) - _VALID_PERSONAS
        if unknown:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown personas: {unknown}. Valid: {_VALID_PERSONAS}",
            )
        total_weight = sum(body.persona_mix.values())
        if total_weight <= 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="persona_mix weights must sum to a positive number",
            )
        # Normalise to sum=1
        persona_mix = {k: v / total_weight for k, v in body.persona_mix.items()}
    else:
        persona_mix = {"casual": 0.5, "whale": 0.1, "rage_quitter": 0.2, "crasher": 0.2}

    params = SimParams(
        players=body.players,
        time_spread_days=body.time_spread_days,
        crash_rate=body.crash_rate,
        rage_quit_rate=body.rage_quit_rate,
        level_fail_rate=body.level_fail_rate,
        spend_rate=body.spend_rate,
        persona_mix=persona_mix,
    )

    result: SimResult = await run_simulation(sb, project_id, params)

    return SimulateResponse(
        players_created=result.players_created,
        sessions_created=result.sessions_created,
        events_generated=result.events_generated,
        crashes_generated=result.crashes_generated,
        rage_quits_generated=result.rage_quits_generated,
        economy_events_generated=result.economy_events_generated,
        elapsed_s=result.elapsed_s,
    )


@router.get("/projects/{project_id}/simulate/stats")
async def simulate_stats(project_id: str, sb: SupabaseDep, user: UserDep) -> dict:
    """Return counts of simulated records for this project."""
    res = (
        sb.schema(SCHEMA).table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("owner_id", user.get("sub"))
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await analytics_service.simulated_counts(sb, project_id)


class ClearSimulatedResponse(BaseModel):
    deleted: dict[str, int]
    message: str


@router.post("/projects/{project_id}/simulate/clear", response_model=ClearSimulatedResponse)
async def simulate_clear(project_id: str, sb: SupabaseDep, user: UserDep) -> ClearSimulatedResponse:
    """Delete all simulated data for this project. Real SDK data is never touched."""
    res = (
        sb.schema(SCHEMA).table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("owner_id", user.get("sub"))
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Count before deletion so we can report accurate numbers
    counts = await analytics_service.simulated_counts(sb, project_id)

    # Delete in FK-safe order: events/crashes first, then sessions, then players
    for table in ("events", "crashes", "sessions", "players"):
        (
            sb.schema(SCHEMA).table(table)
            .delete()
            .eq("project_id", project_id)
            .eq("is_simulated", True)
            .execute()
        )

    total = sum(counts.values())
    return ClearSimulatedResponse(
        deleted=counts,
        message=f"Deleted {total} simulated records across {len(counts)} tables.",
    )
