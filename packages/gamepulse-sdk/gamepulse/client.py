from __future__ import annotations

import atexit
import threading
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from gamepulse_core import (
    BaseEvent,
    BatchEventsRequest,
    CrashIngestRequest,
    EventCategory,
    SessionEndReason,
    SessionEndRequest,
    SessionStartRequest,
)
from gamepulse_core.version import __version__ as CORE_VERSION

from gamepulse.config import SDKConfig
from gamepulse.context import build_device_context
from gamepulse.queue import EventQueue
from gamepulse.session import Session
from gamepulse.storage import OfflineStore
from gamepulse.transport import Transport
from gamepulse.utils.logging import log

# Send outcomes used by the offline-persistence paths.
_OK = "ok"        # 2xx — accepted by the backend
_RETRY = "retry"  # transient (network / 5xx / offline) — persist and retry later
_DROP = "drop"    # permanent (4xx) — give up, never retry


def _chunks(seq: list, size: int):
    size = max(size, 1)
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _fire_error(cfg: SDKConfig, description: str, count: int) -> None:
    """Call the user's on_send_error callback if one is registered. Never raises."""
    if cfg.on_send_error is None:
        return
    try:
        cfg.on_send_error(description, count)
    except Exception as exc:
        log.warning("gamepulse: on_send_error callback raised: %s", exc)


class GamePulseClient:
    _instance: GamePulseClient | None = None
    _lock = threading.Lock()

    def __init__(self, cfg: SDKConfig) -> None:
        self.cfg = cfg
        self.device = build_device_context(cfg.app_version)
        self.transport = Transport(cfg)
        self.queue = EventQueue(cfg, flush_fn=self._flush_batch)
        self.session: Session | None = None
        self._closed = False

        self.store: OfflineStore | None = None
        if cfg.offline_storage and cfg.api_key:
            try:
                self.store = OfflineStore(
                    cfg.offline_storage_path,
                    max_events=cfg.max_offline_events,
                    max_bytes=cfg.max_offline_bytes,
                )
                # Best-effort: flush anything left over from a previous run.
                self._replay_offline()
            except Exception as e:  # never let storage break init
                log.warning("gamepulse: offline storage init failed: %s", e)
                self.store = None

        atexit.register(self.shutdown)

        if cfg.debug:
            import logging as _logging
            _handler = _logging.StreamHandler()
            _handler.setFormatter(_logging.Formatter("%(asctime)s [gamepulse] %(levelname)s %(message)s"))
            log.addHandler(_handler)
            log.setLevel(_logging.DEBUG)

        if cfg.enable_crash_capture and cfg.api_key:
            from gamepulse import crash
            crash.install(self)

    # ---- lifecycle ----

    @classmethod
    def initialize(cls, cfg: SDKConfig) -> GamePulseClient:
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = cls(cfg)
            return cls._instance

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.session and self.session.id and not self.session.ended_at:
                self.end_session(end_reason="timeout")
            self.queue.shutdown()
        finally:
            self.transport.close()

    # ---- session ----

    def start_session(self, **_: Any) -> Session:
        now = datetime.now(UTC)
        if not self.cfg.player_id:
            log.debug("gamepulse: start_session without player_id")
            self.session = Session.new_local()
            return self.session

        req = SessionStartRequest(
            player_external_id=self.cfg.player_id,
            started_at=now,
            device=self.device,
            app_version=self.cfg.app_version,
        )
        resp = self.transport.post("/v1/sessions/start", req.model_dump(mode="json"))
        if resp is None or resp.status_code >= 300:
            status_info = f"HTTP {resp.status_code}" if resp is not None else "network error"
            log.warning("gamepulse: start_session failed (%s) — using local session", status_info)
            _fire_error(self.cfg, status_info, 0)
            self.session = Session.new_local()
            return self.session
        data = resp.json()
        self.session = Session(
            id=UUID(data["session_id"]),
            player_id=UUID(data["player_id"]),
            started_at=now,
        )
        return self.session

    def end_session(self, end_reason: str = "normal") -> None:
        if not self.session or not self.session.id:
            self.session = None
            return
        now = datetime.now(UTC)
        try:
            reason = SessionEndReason(end_reason)
        except ValueError:
            reason = SessionEndReason.NORMAL
        req = SessionEndRequest(session_id=self.session.id, ended_at=now, end_reason=reason)
        resp = self.transport.post("/v1/sessions/end", req.model_dump(mode="json"))
        if resp is not None and resp.status_code >= 300:
            log.warning("gamepulse: end_session -> HTTP %d", resp.status_code)
            _fire_error(self.cfg, f"HTTP {resp.status_code}", 0)
        self.session.ended_at = now
        self.session.end_reason = end_reason
        self.session = None

    # ---- events ----

    def track(self, event_name: str, **payload: Any) -> None:
        try:
            category, name = (
                event_name.split(".", 1) if "." in event_name else ("custom", event_name)
            )
            try:
                category_enum = EventCategory(category)
            except ValueError:
                category_enum = EventCategory.CUSTOM
            ev = BaseEvent(
                type=f"{category_enum.value}.{name}",
                category=category_enum,
                name=name,
                session_id=self.session.id if self.session else None,
                player_id=self.cfg.player_id,
                payload=payload,
                sdk_version=CORE_VERSION,
            )
            self.queue.put(ev)
        except Exception as e:
            log.warning("gamepulse: track failed: %s", e)

    def identify(self, player_id: str, **attributes: Any) -> None:
        self.cfg.player_id = player_id
        if not self.cfg.api_key:
            return
        log.debug("gamepulse: identify player_id=%s attrs=%s", player_id, list(attributes.keys()))
        resp = self.transport.post(
            "/v1/players/identify",
            {"external_id": player_id, "attributes": attributes},
        )
        if resp is None:
            log.warning("gamepulse: identify failed — no response (network error or retries exhausted)")
            _fire_error(self.cfg, "network error", 0)
        elif resp.status_code >= 400:
            log.warning("gamepulse: identify -> HTTP %d", resp.status_code)
            _fire_error(self.cfg, f"HTTP {resp.status_code}", 0)
        else:
            log.debug("gamepulse: identify -> HTTP %d", resp.status_code)

    def flush(self, timeout_s: float | None = None) -> None:
        self.queue.flush(timeout_s)

    # ---- internal ----

    def _post_outcome(self, path: str, payload: dict[str, Any]) -> tuple[str, int | None]:
        """Send one request and classify the result.

        Returns ``(outcome, http_status_or_None)`` where outcome is one of:
        ``_OK`` (2xx accepted), ``_DROP`` (4xx permanent client error — never
        retry), or ``_RETRY`` (network error, 5xx — worth persisting and retrying
        later). ``http_status_or_None`` is None when all retries were exhausted
        without a response (pure network failure).
        """
        resp = self.transport.post(path, payload)
        if resp is None:
            return _RETRY, None
        if resp.status_code < 300:
            return _OK, resp.status_code
        if 400 <= resp.status_code < 500:
            return _DROP, resp.status_code
        return _RETRY, resp.status_code

    def _send_events(self, player_external_id: str, events: list[BaseEvent]) -> tuple[str, int | None]:
        req = BatchEventsRequest(
            player_external_id=player_external_id,
            events=events,
            device=self.device,
        )
        return self._post_outcome("/v1/events/batch", req.model_dump(mode="json"))

    def _send_crash(self, data: dict[str, Any]) -> tuple[str, int | None]:
        return self._post_outcome("/v1/crashes", data)

    def _flush_batch(self, events: list[BaseEvent]) -> None:
        if not self.cfg.api_key or not self.cfg.player_id:
            return
        outcome, status = self._send_events(self.cfg.player_id, events)
        if outcome == _RETRY and self.store is not None:
            self._persist_events(events)
        elif outcome == _DROP:
            log.warning("gamepulse: batch rejected (4xx) — dropping %d event(s)", len(events))
        if outcome != _OK:
            _fire_error(self.cfg, f"HTTP {status}" if status else "network error", len(events))

    def _persist_events(self, events: list[BaseEvent]) -> None:
        try:
            self.store.append_events(  # type: ignore[union-attr]
                [(str(ev.event_id), ev.model_dump(mode="json")) for ev in events]
            )
        except Exception as e:
            log.warning("gamepulse: failed to persist events offline: %s", e)

    def _report_crash(
        self,
        *,
        fingerprint: str,
        exc_type: str,
        message: str | None,
        stacktrace: str,
        occurred_at: datetime,
    ) -> None:
        if not self.cfg.api_key or not self.cfg.player_id:
            return
        req = CrashIngestRequest(
            player_external_id=self.cfg.player_id,
            session_id=self.session.id if self.session else None,
            fingerprint=fingerprint,
            exc_type=exc_type,
            message=message,
            stacktrace=stacktrace,
            occurred_at=occurred_at,
            context={"app_version": self.cfg.app_version},
        )
        data = req.model_dump(mode="json")
        outcome, status = self._send_crash(data)
        if outcome == _RETRY and self.store is not None:
            # Crash reports are high-value — persist so they survive the process
            # ending while offline. The id is stable across retries, so re-reading
            # the same crash next launch maps to one store entry.
            cid = f"{fingerprint}:{occurred_at.isoformat()}"
            try:
                self.store.append_crashes([(cid, data)])
            except Exception as e:
                log.warning("gamepulse: failed to persist crash offline: %s", e)
        if outcome != _OK:
            _fire_error(self.cfg, f"HTTP {status}" if status else "network error", 0)

    # ---- offline replay ----

    def _replay_offline(self) -> None:
        """Best-effort: re-send anything left on disk from a previous run."""
        try:
            self._replay_events()
        except Exception as e:
            log.warning("gamepulse: offline event replay failed: %s", e)
        try:
            self._replay_crashes()
        except Exception as e:
            log.warning("gamepulse: offline crash replay failed: %s", e)

    def _replay_events(self) -> None:
        assert self.store is not None
        pending = self.store.load_events()
        if not pending or not self.cfg.api_key:
            return

        resolved: set[str] = set()  # ids to remove (sent, or permanently unsendable)
        by_player: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for rec_id, data in pending:
            pid = data.get("player_id") or self.cfg.player_id
            if pid:
                by_player[pid].append((rec_id, data))
            else:
                resolved.add(rec_id)  # no player → can never send; drop it

        for pid, items in by_player.items():
            stop = False
            for chunk in _chunks(items, self.cfg.batch_size):
                events: list[BaseEvent] = []
                chunk_ids: list[str] = []
                for rec_id, data in chunk:
                    try:
                        events.append(BaseEvent.model_validate(data))
                        chunk_ids.append(rec_id)
                    except Exception:
                        resolved.add(rec_id)  # corrupt record → drop, don't retry forever
                if not events:
                    continue
                outcome, _ = self._send_events(pid, events)
                if outcome == _OK:
                    resolved.update(chunk_ids)
                elif outcome == _DROP:
                    resolved.update(chunk_ids)  # permanent — drop so it can't block the queue
                    log.warning("gamepulse: dropping %d unsendable offline event(s)", len(chunk_ids))
                else:  # _RETRY — still offline, leave the rest for next launch
                    stop = True
                    break
            if stop:
                break

        if resolved:
            self.store.remove_events(resolved)

    def _replay_crashes(self) -> None:
        assert self.store is not None
        pending = self.store.load_crashes()
        if not pending or not self.cfg.api_key:
            return
        done: set[str] = set()
        for rec_id, data in pending:
            outcome, _ = self._send_crash(data)
            if outcome in (_OK, _DROP):
                done.add(rec_id)  # sent, or permanently rejected — stop tracking it
            else:  # _RETRY — still offline, retry the rest next launch
                break
        if done:
            self.store.remove_crashes(done)


def get_client() -> GamePulseClient:
    if GamePulseClient._instance is None:
        GamePulseClient.initialize(SDKConfig(api_key=None))
    assert GamePulseClient._instance is not None
    return GamePulseClient._instance
