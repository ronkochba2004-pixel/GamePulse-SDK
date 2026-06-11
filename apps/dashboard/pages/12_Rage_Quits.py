import pandas as pd
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.charts import area, bar
from lib.filters import date_range, sim_data_filter
from lib.ui import (
    api_error,
    download_csv,
    empty_state,
    page_header,
    section,
    with_spinner,
)

require_project()
page_header("😤 Rage Quits", "Where and why players quit in frustration")

days = date_range(default="Last 7 days")
exclude_sim = sim_data_filter()

with with_spinner("Analysing frustration signals…"):
    try:
        data = get("/v1/query/rage-quits", days=days, exclude_simulated=exclude_sim)
    except Exception as e:
        api_error(e)

totals = data.get("totals", {})

st.caption(
    "A **rage quit** is a session that ends in frustration (`end_reason = rage_quit`) "
    "or an explicit `error.rage_quit` event. This page surfaces the levels driving it."
)

if totals.get("rage_quits", 0) == 0 and totals.get("rage_quit_events", 0) == 0:
    empty_state(
        "No rage quits detected in this window 🎉",
        "Widen the date range, or run a simulation to see how frustration analytics look.",
    )
    st.stop()

# ── KPIs ─────────────────────────────────────────────────────────────────────
rate = totals.get("rage_quit_rate", 0.0)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rage quits", f"{totals.get('rage_quits', 0):,}")
c2.metric(
    "Rage-quit rate",
    f"{rate:.1%}",
    delta="⚠ high" if rate >= 0.15 else "ok",
    delta_color="inverse" if rate >= 0.15 else "normal",
)
c3.metric("Rage-quit events", f"{totals.get('rage_quit_events', 0):,}")
c4.metric("Total sessions", f"{totals.get('total_sessions', 0):,}")

st.divider()

# ── Over time ────────────────────────────────────────────────────────────────
section("Rage quits over time", "📈")
over_time = data.get("over_time", [])
if over_time:
    ot_df = pd.DataFrame(over_time)
    st.plotly_chart(
        area(ot_df, x="day", y="rage_quits", title="Daily rage quits"),
        use_container_width=True,
        key="chart_rage_over_time",
    )
else:
    empty_state("No rage-quit sessions in this window", "Rage-quit events may still exist below")

# ── By level ─────────────────────────────────────────────────────────────────
section("Rage quits by level", "🎯")
by_level = data.get("by_level", [])
if by_level:
    bl_df = pd.DataFrame(by_level)
    st.plotly_chart(
        bar(bl_df, x="level", y="rage_quits", title="Rage quits per level"),
        use_container_width=True,
        key="chart_rage_by_level",
    )
else:
    empty_state("No per-level rage-quit data", "Emit `error.rage_quit` with a `level` payload to populate this")

# ── Top frustrating levels (frustration score) ───────────────────────────────
section("Top frustrating levels", "🔥")
st.caption(
    "**Frustration score** = (rage quits × 2) + (level fail-rate × 10). "
    "Higher means players are both failing *and* quitting there."
)
per_level = data.get("per_level", [])
if per_level:
    pl_df = pd.DataFrame(per_level)
    pretty = pl_df.rename(
        columns={
            "level": "Level",
            "rage_quits": "Rage quits",
            "fails": "Fails",
            "starts": "Starts",
            "fail_rate": "Fail rate",
            "frustration_score": "Frustration score",
        }
    )
    if "Fail rate" in pretty.columns:
        pretty["Fail rate"] = (pretty["Fail rate"] * 100).round(1).astype(str) + "%"
    st.dataframe(pretty, use_container_width=True, hide_index=True)
    download_csv(pretty, "frustrating_levels.csv", key="dl_frustration")

    worst = per_level[0]
    if worst.get("frustration_score", 0) > 0:
        st.warning(
            f"**Level {worst['level']}** is your biggest frustration hotspot — "
            f"{worst['rage_quits']} rage quit(s) and a {worst['fail_rate']:.0%} fail rate.",
            icon="🔥",
        )
else:
    empty_state("Not enough progression data to score levels")

# ── Recent rage-quit events ──────────────────────────────────────────────────
section("Recent rage-quit events", "📋")
recent = data.get("recent", [])
if recent:
    rec_df = pd.DataFrame(recent)
    if "payload" in rec_df.columns:
        rec_df["level"] = rec_df["payload"].apply(
            lambda p: (p or {}).get("level") if isinstance(p, dict) else None
        )
    cols = [c for c in ["occurred_at", "level", "player_id"] if c in rec_df.columns]
    rec_df = rec_df[cols]
    if "occurred_at" in rec_df.columns:
        rec_df["occurred_at"] = pd.to_datetime(rec_df["occurred_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(rec_df, use_container_width=True, hide_index=True, height=360)
    download_csv(rec_df, "recent_rage_quits.csv", key="dl_recent_rage")
else:
    empty_state("No recent rage-quit events")
