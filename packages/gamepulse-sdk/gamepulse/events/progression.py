from __future__ import annotations

from typing import Any

from gamepulse.client import get_client


def start(level: int | str, **extra: Any) -> None:
    get_client().track("progression.level_start", level=level, **extra)


def complete(level: int | str, stars: int | None = None, **extra: Any) -> None:
    get_client().track("progression.level_complete", level=level, stars=stars, **extra)


def fail(level: int | str, reason: str | None = None, **extra: Any) -> None:
    get_client().track("progression.level_fail", level=level, reason=reason, **extra)
