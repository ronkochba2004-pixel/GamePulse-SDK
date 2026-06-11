from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from gamepulse_core.events import BaseEvent

from gamepulse.config import SDKConfig
from gamepulse.utils.logging import log


class EventQueue:
    """Bounded thread-safe queue with a background flush worker."""

    def __init__(self, cfg: SDKConfig, flush_fn: Callable[[list[BaseEvent]], None]) -> None:
        self.cfg = cfg
        self._flush_fn = flush_fn
        self._q: queue.Queue[BaseEvent] = queue.Queue(maxsize=cfg.max_queue_size)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="gamepulse-flush", daemon=True
        )
        self._thread.start()

    def put(self, event: BaseEvent) -> None:
        try:
            self._q.put_nowait(event)
        except queue.Full:
            log.warning("gamepulse: queue full, dropping event %s", event.type)

    def _drain(self, max_items: int) -> list[BaseEvent]:
        items: list[BaseEvent] = []
        try:
            for _ in range(max_items):
                items.append(self._q.get_nowait())
        except queue.Empty:
            pass
        return items

    def _run(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(self.cfg.flush_interval_s)
            batch = self._drain(self.cfg.batch_size)
            if batch:
                try:
                    self._flush_fn(batch)
                except Exception as e:  # never raise from worker
                    log.warning("gamepulse: flush failed: %s", e)

    def flush(self, timeout_s: float | None = None) -> None:
        # Drain everything currently in the queue. The timeout_s argument is
        # accepted for forward-compat but the synchronous transport already has
        # its own per-call timeout.
        _ = timeout_s
        while True:
            batch = self._drain(self.cfg.batch_size)
            if not batch:
                break
            try:
                self._flush_fn(batch)
            except Exception as e:
                log.warning("gamepulse: flush failed: %s", e)

    def shutdown(self) -> None:
        self.flush()
        self._stop.set()
        self._thread.join(timeout=2.0)
