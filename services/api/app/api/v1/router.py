from fastapi import APIRouter

from app.api.v1 import crashes, debug, ingest, manage, projects, query, sessions

api_router = APIRouter()
api_router.include_router(ingest.router, prefix="/events", tags=["ingest"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(crashes.router, prefix="/crashes", tags=["crashes"])
api_router.include_router(projects.router, prefix="/players", tags=["players"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(manage.router, tags=["manage"])
api_router.include_router(debug.router, tags=["debug"])
