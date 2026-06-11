from __future__ import annotations

from typing import Any

from gamepulse.client import get_client


def emit(name: str, **payload: Any) -> None:
    get_client().track(f"custom.{name}", **payload)
