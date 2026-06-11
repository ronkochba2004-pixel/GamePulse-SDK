"""Background analytics-view refresh scheduler.

Runs a single daemon thread that calls ``gamepulse.refresh_analytics_views()``
via ``sb.schema("gamepulse").rpc(...)`` — the same schema-routing pattern used
by all other queries in the application — on a configurable interval.

Usage — called automatically from the FastAPI lifespan in ``main.py``:

    scheduler.start(interval_s=settings.analytics_refresh_interval_s)
    ...
    scheduler.stop()

To disable automatic refresh, set ``GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S=0``
in the environment. The scheduler will not start if interval_s is 0.
"""
from __future__ import annotations

import logging
import threading

log = logging.getLogger("gamepulse.scheduler")

_stop_event: threading.Event = threading.Event()
_thread: threading.Thread | None = None


def _do_refresh() -> None:
    try:
        from app.db.supabase import get_supabase
        sb = get_supabase()
        # Use the same schema("gamepulse") pattern as every other query in the
        # app — avoids the public-schema PostgREST wrapper entirely.
        sb.schema("gamepulse").rpc("refresh_analytics_views", {}).execute()
        log.info("analytics views refreshed")
    except Exception as exc:
        log.warning("analytics view refresh failed: %s", exc)


def _loop(interval_s: int) -> None:
    log.info("analytics scheduler started (interval=%ds)", interval_s)
    _do_refresh()  # refresh immediately on startup
    while not _stop_event.wait(interval_s):
        _do_refresh()
    log.info("analytics scheduler stopped")


def start(interval_s: int = 600) -> None:
    """Start the background refresh thread. No-op if interval_s is 0."""
    global _thread, _stop_event
    if interval_s <= 0:
        log.info("analytics scheduler disabled (interval_s=0)")
        return
    _stop_event = threading.Event()
    _thread = threading.Thread(
        target=_loop,
        args=(interval_s,),
        name="gamepulse-scheduler",
        daemon=True,
    )
    _thread.start()


def stop() -> None:
    """Signal the refresh thread to exit and wait for it."""
    _stop_event.set()
    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=5.0)
