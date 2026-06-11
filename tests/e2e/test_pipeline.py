"""End-to-end pipeline test.

This test targets a *running* GamePulse API (it does not spin one up itself,
because that requires Supabase credentials and a real Postgres). It is
skipped unless ``GAMEPULSE_E2E_API_URL`` is set in the environment.

Run it locally like:

    GAMEPULSE_E2E_API_URL=http://localhost:8000 \
    GAMEPULSE_E2E_API_KEY=demo-key-please-rotate \
    pytest -q tests/e2e
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import UTC

import gamepulse
import httpx
import pytest

API_URL = os.environ.get("GAMEPULSE_E2E_API_URL")
API_KEY = os.environ.get("GAMEPULSE_E2E_API_KEY", "demo-key-please-rotate")

pytestmark = pytest.mark.skipif(
    not API_URL, reason="Set GAMEPULSE_E2E_API_URL to enable e2e tests"
)


def _api() -> httpx.Client:
    return httpx.Client(
        base_url=API_URL, headers={"X-GamePulse-Key": API_KEY}, timeout=20.0
    )


def test_healthz_reachable() -> None:
    r = httpx.get(f"{API_URL}/healthz", timeout=5.0)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_full_pipeline_ingest_and_query() -> None:
    player_id = f"e2e_{uuid.uuid4().hex[:10]}"

    gamepulse.init(
        api_key=API_KEY,
        project="demo",
        player_id=player_id,
        api_url=API_URL,
        enable_crash_capture=False,
        batch_size=10,
        flush_interval_s=0.5,
    )

    # Drive a quick session through the SDK
    with gamepulse.session():
        gamepulse.progression.start(level=1)
        gamepulse.progression.complete(level=1, stars=3)
        gamepulse.progression.start(level=2)
        gamepulse.progression.fail(level=2, reason="time_out")
        gamepulse.economy.earn(currency="gold", amount=100, source="quest")
        gamepulse.economy.spend(currency="gold", amount=30, item="potion")

    gamepulse.flush()

    # Send a synthetic crash directly via the SDK's internal client
    from datetime import datetime

    from gamepulse.client import get_client
    get_client()._report_crash(  # noqa: SLF001
        fingerprint=f"e2e-{player_id}",
        exc_type="RuntimeError",
        message="synthetic e2e crash",
        stacktrace="Traceback ...\nRuntimeError: synthetic",
        occurred_at=datetime.now(UTC),
    )

    gamepulse.shutdown()

    # Give the backend a moment to commit (Supabase REST is sync but be safe)
    time.sleep(1.0)

    with _api() as c:
        overview = c.get("/v1/query/overview", params={"days": 1}).json()
        assert overview["totals"]["sessions"] >= 1

        sessions = c.get("/v1/query/sessions/recent", params={"limit": 50}).json()
        assert any(True for _ in sessions), "expected at least one recent session"

        events = c.get("/v1/query/events/recent", params={"limit": 200}).json()
        types = {e["type"] for e in events}
        assert "progression.level_start" in types
        assert "progression.level_complete" in types
        assert "economy.currency_spend" in types

        funnel = c.get(
            "/v1/query/progression/funnel", params={"days": 1, "max_level": 5}
        ).json()
        lvl1 = next(r for r in funnel if r["level"] == 1)
        assert lvl1["starts"] >= 1
        assert lvl1["completes"] >= 1

        economy = c.get("/v1/query/economy/summary", params={"days": 1}).json()
        assert economy["spent"].get("gold", 0) >= 30

        crashes = c.get("/v1/query/crashes/top", params={"limit": 20}).json()
        fps = {c["fingerprint"] for c in crashes}
        assert f"e2e-{player_id}" in fps
