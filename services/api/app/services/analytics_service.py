from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.db.repositories import crashes as crashes_repo
from app.db.repositories import sessions as sessions_repo
from app.db.supabase import SupabaseClient

SCHEMA = "gamepulse"


def _since_iso(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


# ---------- Overview ----------

async def overview(
    sb: SupabaseClient,
    project_id: str,
    days: int = 7,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    """Live overview computed from the sessions table (no MV refresh required)."""
    since = _since_iso(days)

    q = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("player_id, started_at, duration_s, end_reason")
        .eq("project_id", project_id)
        .gte("started_at", since)
        .order("started_at")
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    rows = q.execute().data or []

    by_day_players: dict[str, set[str]] = defaultdict(set)
    by_day_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions": 0, "duration_total": 0.0, "with_duration": 0, "crashes": 0, "rage_quits": 0}
    )
    total_sessions = 0
    total_crashes = 0
    total_rage = 0
    duration_sum = 0.0
    duration_count = 0

    for r in rows:
        day = r["started_at"][:10]
        by_day_players[day].add(r["player_id"])
        s = by_day_stats[day]
        s["sessions"] += 1
        total_sessions += 1
        if r.get("duration_s") is not None:
            s["duration_total"] += r["duration_s"]
            s["with_duration"] += 1
            duration_sum += r["duration_s"]
            duration_count += 1
        if r.get("end_reason") == "crash":
            s["crashes"] += 1
            total_crashes += 1
        if r.get("end_reason") == "rage_quit":
            s["rage_quits"] += 1
            total_rage += 1

    dau = [{"day": day, "dau": len(players)} for day, players in sorted(by_day_players.items())]
    session_stats = [
        {
            "day": day,
            "sessions": int(s["sessions"]),
            "avg_duration_s": int(s["duration_total"] / s["with_duration"]) if s["with_duration"] else 0,
            "crashes": int(s["crashes"]),
            "rage_quits": int(s["rage_quits"]),
        }
        for day, s in sorted(by_day_stats.items())
    ]
    crash_free_rate = (1.0 - (total_crashes / total_sessions)) if total_sessions else 1.0
    avg_session_s = (duration_sum / duration_count) if duration_count else 0.0

    return {
        "dau": dau,
        "session_stats": session_stats,
        "totals": {
            "sessions": total_sessions,
            "crashes": total_crashes,
            "rage_quits": total_rage,
            "crash_free_rate": round(crash_free_rate, 4),
            "avg_session_s": round(avg_session_s, 1),
        },
    }


# ---------- Crashes / sessions passthroughs ----------

async def top_crashes(
    sb: SupabaseClient,
    project_id: str,
    limit: int = 20,
    exclude_simulated: bool = False,
) -> list[dict]:
    return await crashes_repo.top_crashes(
        sb, project_id, limit=limit, exclude_simulated=exclude_simulated
    )


async def recent_sessions(
    sb: SupabaseClient,
    project_id: str,
    limit: int = 50,
    exclude_simulated: bool = False,
) -> list[dict]:
    return await sessions_repo.recent_sessions(
        sb, project_id, limit=limit, exclude_simulated=exclude_simulated
    )


# ---------- Session analytics ----------

async def session_analytics(
    sb: SupabaseClient,
    project_id: str,
    days: int = 14,
    limit: int = 500,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    """Rich session analytics: time series, end-reason breakdown, and recent rows."""
    since = _since_iso(days)

    # Full window scan for aggregates (no LIMIT — capped at 100k)
    aq = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("player_id, started_at, ended_at, duration_s, end_reason, platform, app_version")
        .eq("project_id", project_id)
        .gte("started_at", since)
        .order("started_at")
        .limit(100_000)
    )
    if exclude_simulated:
        aq = aq.eq("is_simulated", False)
    all_rows = aq.execute().data or []

    # Recent rows for the display table
    rq = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("id, player_id, started_at, ended_at, duration_s, end_reason, platform, app_version, is_simulated")
        .eq("project_id", project_id)
        .order("started_at", desc=True)
        .limit(limit)
    )
    if exclude_simulated:
        rq = rq.eq("is_simulated", False)
    recent = rq.execute().data or []

    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"sessions": 0, "dur_total": 0.0, "dur_count": 0}
    )
    end_reasons: Counter[str] = Counter()
    dur_total = 0.0
    dur_count = 0
    all_durations: list[float] = []

    for r in all_rows:
        day = r["started_at"][:10]
        by_day[day]["sessions"] += 1
        # duration_s is a Postgres generated column; fall back to computing it
        # from timestamps so this works with the in-memory test fake as well.
        d = r.get("duration_s")
        if d is None and r.get("started_at") and r.get("ended_at"):
            try:
                from datetime import datetime as _dt
                s_at = _dt.fromisoformat(r["started_at"].replace("Z", "+00:00"))
                e_at = _dt.fromisoformat(r["ended_at"].replace("Z", "+00:00"))
                d = int((e_at - s_at).total_seconds())
            except Exception:
                pass
        if d is not None:
            by_day[day]["dur_total"] += d
            by_day[day]["dur_count"] += 1
            dur_total += d
            dur_count += 1
            all_durations.append(d)
        end_reasons[r.get("end_reason") or "unknown"] += 1

    all_durations.sort()
    median_dur = all_durations[len(all_durations) // 2] if all_durations else 0

    over_time = [
        {
            "day": day,
            "sessions": s["sessions"],
            "avg_duration_s": int(s["dur_total"] / s["dur_count"]) if s["dur_count"] else 0,
        }
        for day, s in sorted(by_day.items())
    ]

    return {
        "totals": {
            "sessions": len(all_rows),
            "finished": dur_count,
            "avg_duration_s": round(dur_total / dur_count, 1) if dur_count else 0.0,
            "median_duration_s": int(median_dur),
            "crashes": end_reasons.get("crash", 0),
            "rage_quits": end_reasons.get("rage_quit", 0),
        },
        "over_time": over_time,
        "end_reasons": dict(end_reasons),
        "recent": recent,
    }


# ---------- Players ----------

async def players_summary(
    sb: SupabaseClient,
    project_id: str,
    days: int = 30,
    limit: int = 200,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    since = _since_iso(days)
    q = (
        sb.schema(SCHEMA)
        .table("players")
        .select("id, external_id, country, platform, app_version, first_seen_at, last_seen_at")
        .eq("project_id", project_id)
        .gte("last_seen_at", since)
        .order("last_seen_at", desc=True)
        .limit(limit)
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    rows = q.execute().data or []
    return {
        "players": rows,
        "by_country": dict(Counter(r.get("country") or "unknown" for r in rows)),
        "by_platform": dict(Counter(r.get("platform") or "unknown" for r in rows)),
        "by_app_version": dict(Counter(r.get("app_version") or "unknown" for r in rows)),
        "total": len(rows),
    }


# ---------- Progression funnel ----------

async def progression_funnel(
    sb: SupabaseClient,
    project_id: str,
    days: int = 7,
    max_level: int = 10,
    exclude_simulated: bool = False,
) -> list[dict]:
    since = _since_iso(days)

    # Progression events (start / complete / fail)
    pq = (
        sb.schema(SCHEMA)
        .table("events")
        .select("type, payload, player_id")
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .in_("type", ["progression.level_start", "progression.level_complete", "progression.level_fail"])
        .limit(50_000)
    )
    if exclude_simulated:
        pq = pq.eq("is_simulated", False)
    rows = pq.execute().data or []

    # Rage-quit events per level (separate query, same window)
    rq = (
        sb.schema(SCHEMA)
        .table("events")
        .select("payload")
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .eq("type", "error.rage_quit")
        .limit(50_000)
    )
    if exclude_simulated:
        rq = rq.eq("is_simulated", False)
    rq_rows = rq.execute().data or []

    # Unique players and total attempt counts per level
    starts_players: dict[int, set[str]] = defaultdict(set)
    starts_total: Counter[int] = Counter()   # total start events (includes retries)
    completes: dict[int, set[str]] = defaultdict(set)
    fails: dict[int, set[str]] = defaultdict(set)

    for r in rows:
        lvl_raw = (r.get("payload") or {}).get("level")
        try:
            lvl = int(lvl_raw)
        except (TypeError, ValueError):
            continue
        if lvl < 1 or lvl > max_level:
            continue
        pid = r["player_id"]
        if r["type"] == "progression.level_start":
            starts_players[lvl].add(pid)
            starts_total[lvl] += 1
        elif r["type"] == "progression.level_complete":
            completes[lvl].add(pid)
        elif r["type"] == "progression.level_fail":
            fails[lvl].add(pid)

    rage_by_level: Counter[int] = Counter()
    for r in rq_rows:
        lvl_raw = (r.get("payload") or {}).get("level")
        try:
            lvl = int(lvl_raw)
        except (TypeError, ValueError):
            continue
        if 1 <= lvl <= max_level:
            rage_by_level[lvl] += 1

    out: list[dict] = []
    for lvl in range(1, max_level + 1):
        s = len(starts_players[lvl])
        attempts = starts_total[lvl]
        c = len(completes[lvl])
        f = len(fails[lvl])
        rq_count = rage_by_level.get(lvl, 0)
        completion_rate = round(c / s, 4) if s else 0.0
        fail_rate = round(f / s, 4) if s else 0.0
        # avg_attempts: how many starts per unique player who attempted the level
        avg_attempts = round(attempts / s, 2) if s else 0.0
        out.append(
            {
                "level": lvl,
                "starts": s,
                "attempts": attempts,
                "avg_attempts": avg_attempts,
                "completes": c,
                "fails": f,
                "rage_quits": rq_count,
                "completion_rate": completion_rate,
                "fail_rate": fail_rate,
            }
        )
    return out


# ---------- Economy ----------

async def economy_summary(
    sb: SupabaseClient,
    project_id: str,
    days: int = 30,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    since = _since_iso(days)
    q = (
        sb.schema(SCHEMA)
        .table("events")
        .select("type, payload")
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .in_("type", ["economy.currency_earn", "economy.currency_spend", "economy.iap", "economy.iap_purchase"])
        .limit(50_000)
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    rows = q.execute().data or []

    earned: dict[str, float] = defaultdict(float)
    spent: dict[str, float] = defaultdict(float)
    items: Counter[str] = Counter()
    iap_revenue: dict[str, float] = defaultdict(float)
    iap_count = 0

    for r in rows:
        p = r.get("payload") or {}
        t = r["type"]
        if t == "economy.currency_earn":
            earned[str(p.get("currency", "unknown"))] += float(p.get("amount", 0) or 0)
        elif t == "economy.currency_spend":
            spent[str(p.get("currency", "unknown"))] += float(p.get("amount", 0) or 0)
            if p.get("item"):
                items[str(p["item"])] += 1
        elif t in ("economy.iap", "economy.iap_purchase"):
            iap_revenue[str(p.get("currency", "USD"))] += float(p.get("price", 0) or 0)
            iap_count += 1

    return {
        "earned": dict(earned),
        "spent": dict(spent),
        "top_items": items.most_common(20),
        "iap": {"revenue_by_currency": dict(iap_revenue), "count": iap_count},
    }


# ---------- Crash analytics (Crashes page) ----------

async def crash_analytics(
    sb: SupabaseClient,
    project_id: str,
    days: int = 14,
    severity: str | None = None,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    """Rich crash breakdown: totals, crash-free rate, time series, and groupings.

    Platform/version are not stored on the crash row, so they are resolved by
    joining each crash's player to the players table.
    """
    since = _since_iso(days)

    cq = (
        sb.schema(SCHEMA)
        .table("crashes")
        .select(
            "fingerprint, exc_type, message, stacktrace, severity, occurred_at, "
            "player_id, session_id, is_simulated"
        )
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .order("occurred_at", desc=True)
        .limit(50_000)
    )
    if severity:
        cq = cq.eq("severity", severity)
    if exclude_simulated:
        cq = cq.eq("is_simulated", False)
    crashes = cq.execute().data or []

    # Sessions in the window give us the crash-free rate.
    sq = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("id, end_reason")
        .eq("project_id", project_id)
        .gte("started_at", since)
        .limit(100_000)
    )
    if exclude_simulated:
        sq = sq.eq("is_simulated", False)
    sessions = sq.execute().data or []
    total_sessions = len(sessions)
    crashed_sessions = sum(1 for s in sessions if s.get("end_reason") == "crash")

    # Resolve platform/app_version via the players table.
    player_ids = list({c["player_id"] for c in crashes if c.get("player_id")})
    players_map: dict[str, dict] = {}
    if player_ids:
        pr = (
            sb.schema(SCHEMA)
            .table("players")
            .select("id, platform, app_version")
            .eq("project_id", project_id)
            .in_("id", player_ids)
            .execute()
        )
        players_map = {p["id"]: p for p in (pr.data or [])}

    by_day: Counter[str] = Counter()
    by_version: Counter[str] = Counter()
    by_platform: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    fingerprints: dict[str, dict[str, Any]] = {}
    affected_players: set[str] = set()
    affected_sessions: set[str] = set()

    for c in crashes:
        occ = c.get("occurred_at") or ""
        by_day[occ[:10]] += 1
        by_severity[str(c.get("severity") or "unknown")] += 1
        pid = c.get("player_id")
        if pid:
            affected_players.add(pid)
        sid = c.get("session_id")
        if sid:
            affected_sessions.add(sid)
        pl = players_map.get(pid or "", {})
        by_version[str(pl.get("app_version") or "unknown")] += 1
        by_platform[str(pl.get("platform") or "unknown")] += 1

        fp = c.get("fingerprint") or "unknown"
        entry = fingerprints.get(fp)
        if entry is None:
            fingerprints[fp] = {
                "fingerprint": fp,
                "exc_type": c.get("exc_type"),
                "message": c.get("message"),
                "severity": c.get("severity"),
                "stacktrace": c.get("stacktrace"),
                "count": 1,
                "first_seen": occ,
                "last_seen": occ,
            }
        else:
            entry["count"] += 1
            if occ and occ < entry["first_seen"]:
                entry["first_seen"] = occ
            if occ and occ > entry["last_seen"]:
                entry["last_seen"] = occ

    over_time = [{"day": d, "crashes": n} for d, n in sorted(by_day.items())]
    top = sorted(fingerprints.values(), key=lambda x: x["count"], reverse=True)[:50]
    crash_free = (1.0 - (crashed_sessions / total_sessions)) if total_sessions else 1.0

    return {
        "totals": {
            "crashes": len(crashes),
            "unique_fingerprints": len(fingerprints),
            "affected_players": len(affected_players),
            "affected_sessions": len(affected_sessions),
            "total_sessions": total_sessions,
            "crashed_sessions": crashed_sessions,
            "crash_free_rate": round(crash_free, 4),
        },
        "over_time": over_time,
        "by_version": dict(by_version.most_common()),
        "by_platform": dict(by_platform.most_common()),
        "by_severity": dict(by_severity),
        "top_fingerprints": top,
        "recent": crashes[:200],
    }


# ---------- Rage quit analytics (Rage Quits page) ----------

async def rage_quit_analytics(
    sb: SupabaseClient,
    project_id: str,
    days: int = 14,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    """Dedicated frustration analytics: rate, time series, and per-level scoring."""
    since = _since_iso(days)

    sq = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("player_id, started_at, end_reason")
        .eq("project_id", project_id)
        .gte("started_at", since)
        .limit(100_000)
    )
    if exclude_simulated:
        sq = sq.eq("is_simulated", False)
    sessions = sq.execute().data or []
    total_sessions = len(sessions)
    rage_sessions = [s for s in sessions if s.get("end_reason") == "rage_quit"]
    rage_rate = (len(rage_sessions) / total_sessions) if total_sessions else 0.0

    by_day: Counter[str] = Counter(s["started_at"][:10] for s in rage_sessions)
    over_time = [{"day": d, "rage_quits": n} for d, n in sorted(by_day.items())]

    # Per-level rage quits come from the error.rage_quit event payload.
    eq = (
        sb.schema(SCHEMA)
        .table("events")
        .select("payload, player_id, occurred_at, is_simulated")
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .eq("type", "error.rage_quit")
        .order("occurred_at", desc=True)
        .limit(50_000)
    )
    if exclude_simulated:
        eq = eq.eq("is_simulated", False)
    rq_events = eq.execute().data or []

    rage_by_level: Counter[int] = Counter()
    for e in rq_events:
        lvl = (e.get("payload") or {}).get("level")
        try:
            rage_by_level[int(lvl)] += 1
        except (TypeError, ValueError):
            continue

    # Level starts/fails feed a simple per-level frustration score.
    pq = (
        sb.schema(SCHEMA)
        .table("events")
        .select("type, payload")
        .eq("project_id", project_id)
        .gte("occurred_at", since)
        .in_("type", ["progression.level_start", "progression.level_fail"])
        .limit(50_000)
    )
    if exclude_simulated:
        pq = pq.eq("is_simulated", False)
    prog = pq.execute().data or []

    starts_by_level: Counter[int] = Counter()
    fails_by_level: Counter[int] = Counter()
    for r in prog:
        lvl_raw = (r.get("payload") or {}).get("level")
        try:
            lvl = int(lvl_raw)
        except (TypeError, ValueError):
            continue
        if r["type"] == "progression.level_start":
            starts_by_level[lvl] += 1
        else:
            fails_by_level[lvl] += 1

    levels = sorted(set(rage_by_level) | set(fails_by_level) | set(starts_by_level))
    per_level: list[dict[str, Any]] = []
    for lvl in levels:
        rq = rage_by_level.get(lvl, 0)
        fails = fails_by_level.get(lvl, 0)
        starts = starts_by_level.get(lvl, 0)
        fail_rate = (fails / starts) if starts else 0.0
        # Frustration score: rage quits weigh heavily; level difficulty (fail
        # rate) adds to it. Simple, explainable heuristic for an MVP.
        frustration = round(rq * 2.0 + fail_rate * 10.0, 2)
        per_level.append(
            {
                "level": lvl,
                "rage_quits": rq,
                "fails": fails,
                "starts": starts,
                "fail_rate": round(fail_rate, 4),
                "frustration_score": frustration,
            }
        )
    per_level.sort(key=lambda x: x["frustration_score"], reverse=True)

    return {
        "totals": {
            "rage_quits": len(rage_sessions),
            "rage_quit_rate": round(rage_rate, 4),
            "total_sessions": total_sessions,
            "rage_quit_events": len(rq_events),
        },
        "over_time": over_time,
        "by_level": [{"level": lvl, "rage_quits": rage_by_level[lvl]} for lvl in sorted(rage_by_level)],
        "per_level": per_level,
        "recent": rq_events[:100],
    }


# ---------- Recent events (Live Events page) ----------

async def recent_events(
    sb: SupabaseClient,
    project_id: str,
    limit: int = 200,
    category: str | None = None,
    exclude_simulated: bool = False,
) -> list[dict]:
    q = (
        sb.schema(SCHEMA)
        .table("events")
        .select("event_id, type, category, name, payload, occurred_at, player_id, session_id, is_simulated")
        .eq("project_id", project_id)
        .order("occurred_at", desc=True)
        .limit(limit)
    )
    if category:
        q = q.eq("category", category)
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    return q.execute().data or []


# ---------- Retention cohort ----------

async def retention_cohort(
    sb: SupabaseClient,
    project_id: str,
    cohort_days: int = 14,
    max_day_n: int = 7,
    exclude_simulated: bool = False,
) -> dict[str, Any]:
    """Day-N retention for players whose first session fell in the last cohort_days days."""
    since = _since_iso(cohort_days)

    q = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("player_id, started_at")
        .eq("project_id", project_id)
        .gte("started_at", since)
        .order("started_at")
        .limit(100_000)
    )
    if exclude_simulated:
        q = q.eq("is_simulated", False)
    rows = q.execute().data or []

    first_seen: dict[str, str] = {}
    player_days: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        pid = r["player_id"]
        day = r["started_at"][:10]
        if pid not in first_seen:
            first_seen[pid] = day
        player_days[pid].add(day)

    cohort_players: dict[str, list[str]] = defaultdict(list)
    for pid, day in first_seen.items():
        cohort_players[day].append(pid)

    result: list[dict] = []
    for cohort_date in sorted(cohort_players.keys()):
        players = cohort_players[cohort_date]
        cohort_size = len(players)
        base = date.fromisoformat(cohort_date)
        entry: dict[str, Any] = {"cohort": cohort_date, "size": cohort_size}
        for n in range(1, max_day_n + 1):
            target = str(base + timedelta(days=n))
            retained = sum(1 for p in players if target in player_days[p])
            entry[f"day_{n}"] = retained
            entry[f"day_{n}_rate"] = round(retained / cohort_size, 3) if cohort_size else 0.0
        result.append(entry)

    return {"cohorts": result, "max_day_n": max_day_n}


# ---------- Player timeline ----------

async def player_timeline(
    sb: SupabaseClient, project_id: str, player_external_id: str, limit: int = 200
) -> dict[str, Any]:
    p_res = (
        sb.schema(SCHEMA)
        .table("players")
        .select("id, external_id, country, platform, app_version, first_seen_at, last_seen_at, is_simulated")
        .eq("project_id", project_id)
        .eq("external_id", player_external_id)
        .limit(1)
        .execute()
    )
    p_rows = p_res.data or []
    if not p_rows:
        return {"player": None, "events": [], "sessions": [], "crashes": []}
    player = p_rows[0]
    player_id = player["id"]

    events_res = (
        sb.schema(SCHEMA)
        .table("events")
        .select("event_id, type, name, payload, occurred_at, session_id")
        .eq("project_id", project_id)
        .eq("player_id", player_id)
        .order("occurred_at", desc=True)
        .limit(limit)
        .execute()
    )
    sessions_res = (
        sb.schema(SCHEMA)
        .table("sessions")
        .select("id, started_at, ended_at, duration_s, end_reason, platform, app_version, is_simulated")
        .eq("project_id", project_id)
        .eq("player_id", player_id)
        .order("started_at", desc=True)
        .limit(50)
        .execute()
    )
    crashes_res = (
        sb.schema(SCHEMA)
        .table("crashes")
        .select("fingerprint, exc_type, message, severity, occurred_at")
        .eq("project_id", project_id)
        .eq("player_id", player_id)
        .order("occurred_at", desc=True)
        .limit(20)
        .execute()
    )
    return {
        "player": player,
        "events": events_res.data or [],
        "sessions": sessions_res.data or [],
        "crashes": crashes_res.data or [],
    }


# ---------- Project info (Settings page) ----------

async def project_info(sb: SupabaseClient, project_id: str) -> dict[str, Any]:
    res = (
        sb.schema(SCHEMA)
        .table("projects")
        .select("id, name, slug, created_at")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else {"id": project_id}


# ---------- Simulated data counts (Simulation page) ----------

async def simulated_counts(sb: SupabaseClient, project_id: str) -> dict[str, int]:
    """Count simulated records per table for the given project."""

    def _count(table: str) -> int:
        r = (
            sb.schema(SCHEMA)
            .table(table)
            .select("id", count="exact")
            .eq("project_id", project_id)
            .eq("is_simulated", True)
            .execute()
        )
        return r.count if r.count is not None else len(r.data or [])

    return {
        "players": _count("players"),
        "sessions": _count("sessions"),
        "events": _count("events"),
        "crashes": _count("crashes"),
    }
