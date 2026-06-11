from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from gamepulse_core.constants import MAX_PAYLOAD_BYTES


def _event(type_: str, **payload):
    cat, name = type_.split(".", 1)
    return {
        "event_id": str(uuid4()),
        "type": type_,
        "category": cat,
        "name": name,
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": payload,
        "session_id": None,
        "player_id": "p1",
        "sdk_version": "0.1.0",
    }


def test_batch_ingest_and_overview(client):
    body = {
        "player_external_id": "p1",
        "device": {"platform": "linux", "os_version": "5.10"},
        "events": [
            _event("progression.level_start", level=1),
            _event("progression.level_complete", level=1, stars=2),
            _event("economy.currency_spend", currency="gold", amount=10, item="potion"),
        ],
    }
    r = client.post("/v1/events/batch", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["accepted"] == 3

    # duplicates should be rejected on retry
    r2 = client.post("/v1/events/batch", json=body)
    assert r2.status_code == 200
    assert r2.json()["accepted"] == 0

    events = client.get("/v1/query/events/recent").json()
    types = {e["type"] for e in events}
    assert "progression.level_start" in types
    assert "economy.currency_spend" in types


def test_session_lifecycle(client):
    started = datetime.now(UTC).isoformat()
    r = client.post(
        "/v1/sessions/start",
        json={
            "player_external_id": "p_session",
            "started_at": started,
            "device": {"platform": "windows"},
            "app_version": "1.0.0",
        },
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    ended = datetime.now(UTC).isoformat()
    r2 = client.post(
        "/v1/sessions/end",
        json={"session_id": session_id, "ended_at": ended, "end_reason": "normal"},
    )
    assert r2.status_code == 204

    sessions = client.get("/v1/query/sessions/recent").json()
    assert any(s["id"] == session_id for s in sessions)


def test_crash_ingest_and_query(client):
    r = client.post(
        "/v1/crashes",
        json={
            "player_external_id": "p_crash",
            "fingerprint": "abc123",
            "exc_type": "ValueError",
            "message": "boom",
            "stacktrace": "Traceback\nValueError: boom",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 201, r.text

    crashes = client.get("/v1/query/crashes/top").json()
    assert any(c["fingerprint"] == "abc123" for c in crashes)


def test_oversized_payload_rejected(client):
    # Build a body whose serialized size exceeds MAX_PAYLOAD_BYTES (256 KB).
    body = {
        "player_external_id": "p1",
        "events": [_event("custom.large", data="x" * (MAX_PAYLOAD_BYTES + 1))],
    }
    raw = json.dumps(body).encode()
    assert len(raw) > MAX_PAYLOAD_BYTES, "test body must exceed the limit"

    r = client.post(
        "/v1/events/batch",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


def test_normal_payload_accepted(client):
    # Confirm that a normal-sized batch is still accepted after the size check.
    body = {
        "player_external_id": "p1",
        "events": [_event("custom.small", note="fine")],
    }
    r = client.post("/v1/events/batch", json=body)
    assert r.status_code == 200
    assert r.json()["accepted"] == 1


def test_crash_analytics_endpoint(client):
    r = client.post(
        "/v1/crashes",
        json={
            "player_external_id": "p_crash_an",
            "fingerprint": "fp_analytics",
            "exc_type": "ValueError",
            "message": "boom",
            "stacktrace": "Traceback\nValueError: boom",
            "severity": "fatal",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert r.status_code == 201, r.text

    data = client.get("/v1/query/crashes/analytics", params={"days": 7}).json()
    assert data["totals"]["crashes"] >= 1
    assert data["totals"]["affected_players"] >= 1
    assert "over_time" in data and "by_severity" in data
    assert data["by_severity"].get("fatal", 0) >= 1
    fps = {f["fingerprint"] for f in data["top_fingerprints"]}
    assert "fp_analytics" in fps


def test_rage_quit_analytics_endpoint(client):
    # A session that ends in a rage quit.
    started = datetime.now(UTC).isoformat()
    sid = client.post(
        "/v1/sessions/start",
        json={"player_external_id": "rage_p", "started_at": started},
    ).json()["session_id"]
    client.post(
        "/v1/sessions/end",
        json={"session_id": sid, "ended_at": datetime.now(UTC).isoformat(), "end_reason": "rage_quit"},
    )
    # The matching rage-quit event carrying the level.
    client.post(
        "/v1/events/batch",
        json={
            "player_external_id": "rage_p",
            "events": [_event("error.rage_quit", level=4)],
        },
    )

    data = client.get("/v1/query/rage-quits", params={"days": 7}).json()
    assert data["totals"]["rage_quit_events"] >= 1
    assert data["totals"]["rage_quits"] >= 1
    by_level = {row["level"]: row["rage_quits"] for row in data["by_level"]}
    assert by_level.get(4, 0) >= 1
    assert any(row["level"] == 4 for row in data["per_level"])


def test_session_analytics_endpoint(client):
    started = datetime.now(UTC).isoformat()
    sid = client.post(
        "/v1/sessions/start",
        json={
            "player_external_id": "sa_player",
            "started_at": started,
            "device": {"platform": "linux"},
            "app_version": "2.0.0",
        },
    ).json()["session_id"]
    client.post(
        "/v1/sessions/end",
        json={"session_id": sid, "ended_at": datetime.now(UTC).isoformat(), "end_reason": "normal"},
    )

    data = client.get("/v1/query/sessions/analytics", params={"days": 7}).json()
    assert data["totals"]["sessions"] >= 1
    assert data["totals"]["finished"] >= 1
    assert "over_time" in data
    assert len(data["over_time"]) >= 1
    assert data["over_time"][0]["sessions"] >= 1
    assert "end_reasons" in data
    assert data["end_reasons"].get("normal", 0) >= 1
    assert len(data["recent"]) >= 1


def test_funnel_includes_attempts_and_rage_quits(client):
    # Two starts for level 3 from same player (one retry)
    client.post(
        "/v1/events/batch",
        json={
            "player_external_id": "retry_p",
            "events": [
                _event("progression.level_start", level=3),
                _event("progression.level_fail", level=3, reason="time"),
                _event("progression.level_start", level=3),   # retry
                _event("progression.level_complete", level=3, stars=1),
                _event("error.rage_quit", level=3),
            ],
        },
    )

    funnel = client.get("/v1/query/progression/funnel", params={"days": 7, "max_level": 5}).json()
    lvl3 = next((r for r in funnel if r["level"] == 3), None)
    assert lvl3 is not None
    # starts = unique players = 1, attempts = total starts = 2
    assert lvl3["starts"] == 1
    assert lvl3["attempts"] == 2
    assert lvl3["avg_attempts"] == 2.0
    assert lvl3["completes"] == 1
    assert lvl3["rage_quits"] >= 1
    assert "fail_rate" in lvl3


def test_progression_funnel_endpoint(client):
    body = {
        "player_external_id": "funnel_p",
        "events": [
            _event("progression.level_start", level=1),
            _event("progression.level_complete", level=1, stars=1),
            _event("progression.level_start", level=2),
            _event("progression.level_fail", level=2, reason="time"),
        ],
    }
    client.post("/v1/events/batch", json=body)

    funnel = client.get("/v1/query/progression/funnel", params={"days": 7, "max_level": 3}).json()
    assert any(r["level"] == 1 and r["starts"] >= 1 and r["completes"] >= 1 for r in funnel)
