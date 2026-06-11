from __future__ import annotations

import hashlib
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.repositories import crashes as crashes_repo
from app.db.repositories import events as events_repo
from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"
_PLATFORMS = ["ios", "android", "pc", "console"]
_APP_VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "1.3.0"]
_COUNTRIES = ["US", "GB", "DE", "FR", "JP", "KR", "BR", "CA", "AU", "IN"]
_ITEMS = ["potion", "shield", "sword_upgrade", "extra_life", "speed_boost", "bomb"]
_IAP_SKUS = [
    ("starter_pack", 0.99),
    ("gem_bundle_100", 1.99),
    ("gem_bundle_500", 7.99),
    ("no_ads", 2.49),
    ("season_pass", 9.99),
]
_CRASH_TYPES = [
    ("NullPointerException", "Attempt to read field on null object reference"),
    ("OutOfMemoryError", "Java heap space exhausted"),
    ("SegmentationFault", "Access violation at address 0x00000000"),
    ("RuntimeException", "Level asset failed to load: assets/level_12.bundle"),
    ("NetworkException", "Connection timed out after 30s"),
    ("AssertionError", "Invariant violated: player.health >= 0"),
]
_CHUNK = 100  # max rows per DB batch call


@dataclass
class SimParams:
    players: int = 30
    time_spread_days: int = 7
    crash_rate: float = 0.05
    rage_quit_rate: float = 0.10
    level_fail_rate: float = 0.35
    spend_rate: float = 0.15
    persona_mix: dict[str, float] = field(default_factory=lambda: {
        "casual": 0.5,
        "whale": 0.1,
        "rage_quitter": 0.2,
        "crasher": 0.2,
    })


@dataclass
class SimResult:
    players_created: int = 0
    sessions_created: int = 0
    events_generated: int = 0
    crashes_generated: int = 0
    rage_quits_generated: int = 0
    economy_events_generated: int = 0
    elapsed_s: float = 0.0


def _pick_persona(mix: dict[str, float]) -> str:
    names = list(mix.keys())
    weights = list(mix.values())
    return random.choices(names, weights=weights, k=1)[0]


def _event(
    *,
    project_id: str,
    player_id: str,
    session_id: str,
    ev_type: str,
    category: str,
    name: str,
    payload: dict[str, Any],
    occurred_at: datetime,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "project_id": project_id,
        "player_id": player_id,
        "session_id": session_id,
        "type": ev_type,
        "category": category,
        "name": name,
        "payload": payload,
        "occurred_at": occurred_at.isoformat(),
        "sdk_version": "sim-1.0",
        "is_simulated": True,
    }


async def run_simulation(
    sb: SupabaseClient,
    project_id: str,
    params: SimParams,
) -> SimResult:
    wall_start = time.monotonic()
    result = SimResult()
    run_id = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)

    # ── Phase 1: generate player metadata in memory ────────────────────────────
    player_metas: list[dict[str, Any]] = []
    for i in range(params.players):
        persona = _pick_persona(params.persona_mix)
        crash_chance = params.crash_rate
        rage_quit_chance = params.rage_quit_rate
        spend_chance = params.spend_rate
        if persona == "crasher":
            crash_chance = min(1.0, params.crash_rate * 5)
        elif persona == "rage_quitter":
            rage_quit_chance = min(1.0, params.rage_quit_rate * 5)
        elif persona == "whale":
            spend_chance = min(1.0, params.spend_rate * 3)

        player_metas.append({
            "external_id": f"sim_{run_id}_{i:04d}",
            "persona": persona,
            "platform": random.choice(_PLATFORMS),
            "country": random.choice(_COUNTRIES),
            "app_version": random.choice(_APP_VERSIONS),
            "crash_chance": crash_chance,
            "rage_quit_chance": rage_quit_chance,
            "spend_chance": spend_chance,
        })

    # ── Phase 2: bulk upsert players, collect their DB UUIDs ──────────────────
    player_upsert_rows = [
        {
            "project_id": project_id,
            "external_id": p["external_id"],
            "last_seen_at": now.isoformat(),
            "platform": p["platform"],
            "app_version": p["app_version"],
            "country": p["country"],
            "attributes": {"persona": p["persona"], "sim": True, "run_id": run_id},
            "is_simulated": True,
        }
        for p in player_metas
    ]

    upsert_res = (
        sb.schema(SCHEMA)
        .table("players")
        .upsert(player_upsert_rows, on_conflict="project_id,external_id")
        .execute()
    )
    player_id_map: dict[str, str] = {
        row["external_id"]: row["id"] for row in (upsert_res.data or [])
    }

    # Fallback select in case upsert didn't return all rows
    if len(player_id_map) < params.players:
        external_ids = [p["external_id"] for p in player_metas]
        sel_res = (
            sb.schema(SCHEMA)
            .table("players")
            .select("id, external_id")
            .eq("project_id", project_id)
            .in_("external_id", external_ids)
            .execute()
        )
        for row in (sel_res.data or []):
            player_id_map[row["external_id"]] = row["id"]

    result.players_created = len(player_id_map)

    # ── Phase 3: generate sessions + events + crashes in memory ───────────────
    session_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    crash_rows: list[dict[str, Any]] = []

    for p in player_metas:
        player_id = player_id_map.get(p["external_id"])
        if not player_id:
            continue

        n_sessions = random.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]

        for _ in range(n_sessions):
            session_id = str(uuid.uuid4())
            days_ago = random.uniform(0.0, float(params.time_spread_days))
            session_start = now - timedelta(days=days_ago)
            session_duration_s = random.uniform(30.0, 300.0)
            session_end = session_start + timedelta(seconds=session_duration_s)

            crashed = random.random() < p["crash_chance"]
            rage_quit = (not crashed) and random.random() < p["rage_quit_chance"]
            end_reason = "crash" if crashed else ("rage_quit" if rage_quit else "natural")

            session_rows.append({
                "id": session_id,
                "project_id": project_id,
                "player_id": player_id,
                "started_at": session_start.isoformat(),
                "ended_at": session_end.isoformat(),
                "end_reason": end_reason,
                "platform": p["platform"],
                "app_version": p["app_version"],
                "device": {
                    "platform": p["platform"],
                    "app_version": p["app_version"],
                    "country": p["country"],
                },
                "is_simulated": True,
            })

            t = session_start
            level = random.randint(1, 5)
            max_levels = random.randint(2, 6)

            # session.start event
            event_rows.append(_event(
                project_id=project_id, player_id=player_id, session_id=session_id,
                ev_type="session.start", category="system", name="session_start",
                payload={"platform": p["platform"]}, occurred_at=t,
            ))

            # Gold earn at session start
            if random.random() < 0.6:
                t += timedelta(seconds=random.uniform(1, 5))
                event_rows.append(_event(
                    project_id=project_id, player_id=player_id, session_id=session_id,
                    ev_type="economy.currency_earn", category="economy", name="currency_earn",
                    payload={
                        "currency": "gold",
                        "amount": random.randint(10, 50),
                        "source": random.choice(["quest", "daily_bonus", "level_reward"]),
                    },
                    occurred_at=t,
                ))
                result.economy_events_generated += 1

            # Whale IAP at session start
            if p["persona"] == "whale" and random.random() < 0.15:
                sku, price = random.choice(_IAP_SKUS)
                t += timedelta(seconds=random.uniform(1, 3))
                event_rows.append(_event(
                    project_id=project_id, player_id=player_id, session_id=session_id,
                    ev_type="economy.iap_purchase", category="economy", name="iap_purchase",
                    payload={"sku": sku, "price": price, "currency": "USD"},
                    occurred_at=t,
                ))
                result.economy_events_generated += 1

            # Level loop
            for lv_idx in range(max_levels):
                if t >= session_end:
                    break

                t += timedelta(seconds=random.uniform(2, 8))
                event_rows.append(_event(
                    project_id=project_id, player_id=player_id, session_id=session_id,
                    ev_type="progression.level_start", category="progression",
                    name="level_start", payload={"level": level}, occurred_at=t,
                ))

                t += timedelta(seconds=random.uniform(10, 40))

                # Crash on final level attempt
                if crashed and lv_idx == max_levels - 1:
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="error.crash", category="error", name="crash",
                        payload={"level": level, "reason": "sim_crash"}, occurred_at=t,
                    ))
                    exc_type, message = random.choice(_CRASH_TYPES)
                    fingerprint = hashlib.md5(
                        f"{exc_type}:{message}".encode()
                    ).hexdigest()[:16]
                    crash_rows.append({
                        "project_id": project_id,
                        "player_id": player_id,
                        "session_id": session_id,
                        "fingerprint": fingerprint,
                        "exc_type": exc_type,
                        "message": message,
                        "stacktrace": (
                            f"at {exc_type}.handle(GameLoop.java:42)\n"
                            "at Session.tick(Session.java:128)\n"
                            "at Main.run(Main.java:17)"
                        ),
                        "severity": random.choice(["fatal", "critical", "warning"]),
                        "occurred_at": t.isoformat(),
                        "context": {"level": level, "platform": p["platform"]},
                        "is_simulated": True,
                    })
                    result.crashes_generated += 1
                    break

                # Level complete or fail
                if random.random() > params.level_fail_rate:
                    stars = random.choices([1, 2, 3], weights=[0.30, 0.45, 0.25])[0]
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="progression.level_complete", category="progression",
                        name="level_complete",
                        payload={"level": level, "stars": stars}, occurred_at=t,
                    ))
                    # Earn gold for completion
                    t += timedelta(seconds=1)
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="economy.currency_earn", category="economy", name="currency_earn",
                        payload={
                            "currency": "gold",
                            "amount": level * 10 + stars * 5,
                            "source": "level_reward",
                        },
                        occurred_at=t,
                    ))
                    result.economy_events_generated += 1
                    # Spend on powerup
                    if random.random() < p["spend_chance"]:
                        t += timedelta(seconds=random.uniform(1, 3))
                        item = random.choice(_ITEMS)
                        cost = random.randint(5, 30) * level
                        event_rows.append(_event(
                            project_id=project_id, player_id=player_id, session_id=session_id,
                            ev_type="economy.currency_spend", category="economy", name="currency_spend",
                            payload={"currency": "gold", "amount": cost, "item": item},
                            occurred_at=t,
                        ))
                        result.economy_events_generated += 1
                else:
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="progression.level_fail", category="progression",
                        name="level_fail",
                        payload={
                            "level": level,
                            "reason": random.choice(["time_out", "lives_exhausted", "gave_up"]),
                        },
                        occurred_at=t,
                    ))

                # Occasional gameplay action
                if random.random() < 0.4:
                    t += timedelta(seconds=random.uniform(1, 5))
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="gameplay.action", category="gameplay",
                        name=random.choice(["jump", "attack", "dodge", "special"]),
                        payload={"level": level}, occurred_at=t,
                    ))

                # Rage quit on final level
                if rage_quit and lv_idx == max_levels - 1:
                    t += timedelta(seconds=random.uniform(1, 5))
                    event_rows.append(_event(
                        project_id=project_id, player_id=player_id, session_id=session_id,
                        ev_type="error.rage_quit", category="error", name="rage_quit",
                        payload={"level": level}, occurred_at=t,
                    ))
                    result.rage_quits_generated += 1
                    break

                level = min(level + 1, 20)

    result.sessions_created = len(session_rows)

    # ── Phase 4: bulk DB writes ────────────────────────────────────────────────
    # Sessions in chunks of _CHUNK
    for i in range(0, len(session_rows), _CHUNK):
        sb.schema(SCHEMA).table("sessions").insert(session_rows[i:i + _CHUNK]).execute()

    # Events in chunks of _CHUNK (uses existing dedup upsert)
    for i in range(0, len(event_rows), _CHUNK):
        inserted = await events_repo.insert_events(sb, event_rows[i:i + _CHUNK])
        result.events_generated += inserted

    # Crashes in one batch
    for i in range(0, len(crash_rows), _CHUNK):
        sb.schema(SCHEMA).table("crashes").insert(crash_rows[i:i + _CHUNK]).execute()

    result.elapsed_s = round(time.monotonic() - wall_start, 2)
    return result
