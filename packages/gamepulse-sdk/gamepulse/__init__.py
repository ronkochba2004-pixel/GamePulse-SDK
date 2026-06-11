"""GamePulse Python SDK — public API surface."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from gamepulse.client import GamePulseClient, get_client
from gamepulse.config import SDKConfig
from gamepulse.events import economy, gameplay, progression
from gamepulse.session import Session

__all__ = [
    "GamePulseClient",
    "SDKConfig",
    "Session",
    "economy",
    "flush",
    "gameplay",
    "identify",
    "init",
    "progression",
    "session",
    "shutdown",
    "track",
]


def init(
    api_key: str | None,
    project: str | None = None,
    player_id: str | None = None,
    api_url: str | None = None,
    **kwargs: Any,
) -> GamePulseClient:
    """Initialize the global SDK client."""
    cfg = SDKConfig(
        api_key=api_key,
        project=project,
        player_id=player_id,
        api_url=api_url or "http://localhost:8000",
        **kwargs,
    )
    return GamePulseClient.initialize(cfg)


def track(event_name: str, **payload: Any) -> None:
    get_client().track(event_name, **payload)


def identify(player_id: str, **attributes: Any) -> None:
    get_client().identify(player_id, **attributes)


def flush(timeout_s: float | None = None) -> None:
    get_client().flush(timeout_s)


def shutdown() -> None:
    get_client().shutdown()


@contextmanager
def session(**kwargs: Any):
    client = get_client()
    sess = client.start_session(**kwargs)
    try:
        yield sess
    except BaseException:
        client.end_session(end_reason="crash")
        raise
    else:
        client.end_session(end_reason="normal")
