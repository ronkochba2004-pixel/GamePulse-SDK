from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gamepulse_core.constants import DEFAULT_BATCH_SIZE, DEFAULT_FLUSH_INTERVAL_S


@dataclass(slots=True)
class SDKConfig:
    api_key: str | None
    project: str | None = None
    player_id: str | None = None
    api_url: str = "http://localhost:8000"

    # transport
    timeout_s: float = 10.0
    max_retries: int = 3
    backoff_base_s: float = 0.5

    # queue
    batch_size: int = DEFAULT_BATCH_SIZE
    flush_interval_s: float = DEFAULT_FLUSH_INTERVAL_S
    max_queue_size: int = 10_000

    # behavior
    enable_crash_capture: bool = True
    auto_session: bool = True
    app_version: str | None = None
    debug: bool = False

    # offline persistence — survive restarts / API downtime
    offline_storage: bool = False
    offline_storage_path: str | None = None
    max_offline_events: int = 10_000
    max_offline_bytes: int = 5 * 1024 * 1024  # 5 MB

    # error visibility — called on the sending thread when a request fails.
    # signature: on_send_error(description: str, event_count: int)
    # description is e.g. "HTTP 401", "HTTP 500", or "network error"
    # event_count is 0 for non-batch calls (identify, crash)
    on_send_error: Any = field(default=None, compare=False)
