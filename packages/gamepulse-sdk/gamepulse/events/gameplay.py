from __future__ import annotations

from typing import Any

from gamepulse.client import get_client


def action(name: str, **extra: Any) -> None:
    get_client().track("gameplay.action", action=name, **extra)


def ability(name: str, **extra: Any) -> None:
    get_client().track("gameplay.ability_used", ability=name, **extra)


def score(value: float, **extra: Any) -> None:
    get_client().track("gameplay.score", value=value, **extra)
