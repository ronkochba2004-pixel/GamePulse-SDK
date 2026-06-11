from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(slots=True)
class Persona:
    name: str
    crash_chance: float       # per session
    rage_quit_chance: float   # per session
    session_min_s: float
    session_max_s: float
    spend_chance: float       # per level


PERSONAS: list[Persona] = [
    Persona("casual",       crash_chance=0.01, rage_quit_chance=0.03, session_min_s=1.0, session_max_s=4.0, spend_chance=0.05),
    Persona("whale",        crash_chance=0.02, rage_quit_chance=0.01, session_min_s=3.0, session_max_s=8.0, spend_chance=0.40),
    Persona("rage_quitter", crash_chance=0.02, rage_quit_chance=0.30, session_min_s=0.5, session_max_s=2.0, spend_chance=0.02),
    Persona("crasher",      crash_chance=0.25, rage_quit_chance=0.05, session_min_s=0.5, session_max_s=2.0, spend_chance=0.05),
]


def pick() -> Persona:
    return random.choice(PERSONAS)
