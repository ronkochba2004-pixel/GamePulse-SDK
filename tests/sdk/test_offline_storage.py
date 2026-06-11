"""Tests for persistent offline storage (storage.py + client integration)."""
from __future__ import annotations

import types

from gamepulse.client import GamePulseClient
from gamepulse.config import SDKConfig
from gamepulse.storage import OfflineStore
from gamepulse_core import BaseEvent, EventCategory


# ── helpers ──────────────────────────────────────────────────────────────────
def _event(name: str = "test", player_id: str = "p1", **payload) -> BaseEvent:
    return BaseEvent(
        type=f"custom.{name}",
        category=EventCategory.CUSTOM,
        name=name,
        player_id=player_id,
        payload=payload,
    )


def _record(ev: BaseEvent) -> tuple[str, dict]:
    return (str(ev.event_id), ev.model_dump(mode="json"))


def _patch_post(monkeypatch, result):
    """Force Transport.post to return a fixed value (or per-call via callable)."""
    calls: list = []

    def fake_post(self, path, json):
        calls.append((path, json))
        return result(path, json) if callable(result) else result

    monkeypatch.setattr("gamepulse.transport.Transport.post", fake_post)
    return calls


_OK_RESP = types.SimpleNamespace(status_code=200)
_BAD_RESP = types.SimpleNamespace(status_code=400)


def _make_client(tmp_path, monkeypatch, post_result) -> GamePulseClient:
    _patch_post(monkeypatch, post_result)
    cfg = SDKConfig(
        api_key="test-key",
        player_id="p1",
        offline_storage=True,
        offline_storage_path=str(tmp_path),
        enable_crash_capture=False,
        flush_interval_s=3600,  # keep the background worker idle during the test
    )
    return GamePulseClient(cfg)


# ── storage-level tests ──────────────────────────────────────────────────────
def test_append_load_remove_roundtrip(tmp_path):
    store = OfflineStore(tmp_path)
    e1, e2 = _event("a"), _event("b")
    store.append_events([_record(e1), _record(e2)])

    loaded = store.load_events()
    assert {i for i, _ in loaded} == {str(e1.event_id), str(e2.event_id)}

    store.remove_events({str(e1.event_id)})
    remaining = store.load_events()
    assert [i for i, _ in remaining] == [str(e2.event_id)]


def test_corrupted_record_does_not_crash(tmp_path):
    store = OfflineStore(tmp_path)
    good = _event("ok")
    store.append_events([_record(good)])
    # Inject a garbage line alongside the valid one.
    with store.events_path.open("a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
        fh.write('{"partial": true}\n')  # valid json but missing id/data

    loaded = store.load_events()  # must not raise
    assert [i for i, _ in loaded] == [str(good.event_id)]


def test_max_offline_events_limit_drops_oldest(tmp_path):
    store = OfflineStore(tmp_path, max_events=5)
    events = [_event(f"e{i}") for i in range(10)]
    for ev in events:
        store.append_events([_record(ev)])

    loaded = store.load_events()
    assert len(loaded) == 5
    # The five most recent survive; the five oldest were dropped.
    assert [i for i, _ in loaded] == [str(e.event_id) for e in events[5:]]


def test_remove_all_deletes_file(tmp_path):
    store = OfflineStore(tmp_path)
    ev = _event("solo")
    store.append_events([_record(ev)])
    assert store.events_path.exists()
    store.remove_events({str(ev.event_id)})
    assert not store.events_path.exists()


# ── client integration tests ─────────────────────────────────────────────────
def test_event_persists_when_upload_fails(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, post_result=None)  # None = offline
    try:
        ev = _event("offline")
        client._flush_batch([ev])
        pending = client.store.load_events()
        assert [i for i, _ in pending] == [str(ev.event_id)]
    finally:
        client.shutdown()


def test_event_dropped_on_permanent_4xx(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, post_result=_BAD_RESP)
    try:
        client._flush_batch([_event("rejected")])
        # 4xx is permanent — nothing should be persisted.
        assert client.store.load_events() == []
    finally:
        client.shutdown()


def test_persisted_event_retried_and_removed_on_startup(tmp_path, monkeypatch):
    # Arrange: a previous run left one unsent event on disk.
    store = OfflineStore(tmp_path)
    ev = _event("from_last_run")
    store.append_events([_record(ev)])
    assert store.load_events()  # sanity

    # Act: new client starts up with a working connection → replay on init.
    calls = _patch_post(monkeypatch, _OK_RESP)
    cfg = SDKConfig(
        api_key="test-key",
        player_id="p1",
        offline_storage=True,
        offline_storage_path=str(tmp_path),
        enable_crash_capture=False,
        flush_interval_s=3600,
    )
    client = GamePulseClient(cfg)
    try:
        # The persisted event was uploaded...
        assert any(path == "/v1/events/batch" for path, _ in calls)
        # ...and cleared from disk after confirmed success.
        assert OfflineStore(tmp_path).load_events() == []
    finally:
        client.shutdown()


def test_persisted_event_kept_when_still_offline(tmp_path, monkeypatch):
    store = OfflineStore(tmp_path)
    ev = _event("still_offline")
    store.append_events([_record(ev)])

    # Startup, but the API is still unreachable (post returns None).
    _patch_post(monkeypatch, None)
    cfg = SDKConfig(
        api_key="test-key",
        player_id="p1",
        offline_storage=True,
        offline_storage_path=str(tmp_path),
        enable_crash_capture=False,
        flush_interval_s=3600,
    )
    client = GamePulseClient(cfg)
    try:
        # Event must remain on disk for the next launch.
        assert [i for i, _ in OfflineStore(tmp_path).load_events()] == [str(ev.event_id)]
    finally:
        client.shutdown()


def test_crash_persists_when_upload_fails(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    client = _make_client(tmp_path, monkeypatch, post_result=None)
    try:
        client._report_crash(
            fingerprint="abc123",
            exc_type="ValueError",
            message="boom",
            stacktrace="Traceback...\nValueError: boom",
            occurred_at=datetime.now(UTC),
        )
        pending = client.store.load_crashes()
        assert len(pending) == 1
        assert pending[0][1]["fingerprint"] == "abc123"
    finally:
        client.shutdown()


def test_crash_retried_and_removed_on_startup(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    # Arrange: a crash left over from a previous (offline) run.
    store = OfflineStore(tmp_path)
    occurred = datetime.now(UTC).isoformat()
    store.append_crashes([(
        f"fp1:{occurred}",
        {
            "player_external_id": "p1",
            "fingerprint": "fp1",
            "exc_type": "RuntimeError",
            "message": "late",
            "stacktrace": "Traceback...",
            "occurred_at": occurred,
            "context": {},
        },
    )])

    calls = _patch_post(monkeypatch, _OK_RESP)
    cfg = SDKConfig(
        api_key="test-key",
        player_id="p1",
        offline_storage=True,
        offline_storage_path=str(tmp_path),
        enable_crash_capture=False,
        flush_interval_s=3600,
    )
    client = GamePulseClient(cfg)
    try:
        assert any(path == "/v1/crashes" for path, _ in calls)
        assert OfflineStore(tmp_path).load_crashes() == []
    finally:
        client.shutdown()


def test_no_offline_files_when_disabled(tmp_path, monkeypatch):
    # offline_storage defaults to False → no store, nothing written even on failure.
    _patch_post(monkeypatch, None)
    cfg = SDKConfig(
        api_key="test-key",
        player_id="p1",
        offline_storage=False,
        enable_crash_capture=False,
        flush_interval_s=3600,
    )
    client = GamePulseClient(cfg)
    try:
        assert client.store is None
        client._flush_batch([_event("nowhere")])  # must not raise
    finally:
        client.shutdown()
