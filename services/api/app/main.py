from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.router import api_router as v1_router
from app.middleware.content_size import ContentSizeLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.settings import get_settings

log = logging.getLogger("gamepulse.api")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from app import scheduler
    settings = get_settings()
    scheduler.start(interval_s=settings.analytics_refresh_interval_s)
    yield
    scheduler.stop()


def create_app() -> FastAPI:
    from app.logging_config import configure as configure_logging

    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="GamePulse API",
        version="0.1.0",
        description="Ingestion + query API for the GamePulse analytics platform.",
        docs_url="/docs",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_min)
    # Added last so it executes first — reject oversized bodies before any other processing.
    app.add_middleware(ContentSizeLimitMiddleware)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "—")
        log.error("Unhandled error rid=%s %s: %s", rid, type(exc).__name__, exc, exc_info=True)
        body: dict = {"detail": "internal_error", "request_id": rid}
        if settings.environment != "production":
            body["debug"] = f"{type(exc).__name__}: {exc}"
        return JSONResponse(body, status_code=500)

    app.include_router(health_router)
    app.include_router(v1_router, prefix="/v1")
    return app


app = create_app()
