import pandas as pd
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.charts import bar, funnel, multi_bar
from lib.filters import date_range, sim_data_filter
from lib.theme import DANGER, SUCCESS, WARNING
from lib.ui import (
    api_error,
    download_csv,
    empty_state,
    page_header,
    section,
    with_spinner,
)

require_project()
page_header("🎯 Funnels & Progression", "Level-by-level completion, failure, and frustration analysis")

st.caption(
    "This page shows how players progress through your levels. "
    "A **completion rate** near 100% means the level is too easy; a sudden drop "
    "often signals a difficulty spike, tutorial gap, or a bug. "
    "**Rage quits** and the **frustration score** highlight levels players find unfair, "
    "not just hard."
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
days = date_range(default="Last 7 days")
max_level = st.sidebar.slider("Max level to show", 3, 30, 15)
sort_by = st.sidebar.selectbox(
    "Sort table by",
    ["Level (ascending)", "Worst completion rate", "Most failures", "Most rage quits", "Highest frustration"],
    index=0,
)
problem_threshold = st.sidebar.slider(
    "Flag as problem below completion %", 10, 90, 50, step=5,
    help="Levels whose completion rate is below this threshold are highlighted.",
)
exclude_sim = sim_data_filter()

with with_spinner("Loading progression data…"):
    try:
        rows = get(
            "/v1/query/progression/funnel",
            days=days,
            max_level=max_level,
            exclude_simulated=exclude_sim,
        )
    except Exception as e:
        api_error(e)

df = pd.DataFrame(rows)
active = df[df["starts"] > 0].copy() if not df.empty else pd.DataFrame()

if active.empty:
    empty_state(
        "No progression events in this window",
        "Run the simulator — it generates level_start, level_complete, and level_fail events — "
        "or integrate the SDK and track `gamepulse.progression.start(level=N)`.",
    )
    st.stop()

# ── Compute derived columns ──────────────────────────────────────────────────
# Drop-off rate between consecutive levels: what % of players who started
# level N *didn't* start level N+1?
levels_present = sorted(active["level"].tolist())
starts_map = dict(zip(active["level"], active["starts"], strict=False))

drop_offs: dict[int, float] = {}
for i, lvl in enumerate(levels_present[:-1]):
    next_lvl = levels_present[i + 1]
    s_now = starts_map.get(lvl, 0)
    s_next = starts_map.get(next_lvl, 0)
    drop_offs[lvl] = round(1.0 - (s_next / s_now), 4) if s_now else 0.0
# Last level has no "next" — drop-off defined as players who never completed it
if levels_present:
    last = levels_present[-1]
    row = active[active["level"] == last].iloc[0]
    s = row["starts"]
    c = row["completes"]
    drop_offs[last] = round(1.0 - (c / s), 4) if s else 0.0

active["drop_off_rate"] = active["level"].map(drop_offs).fillna(0.0)

# Frustration score (same definition as Rage Quits page)
active["frustration_score"] = (
    active["rage_quits"] * 2.0 + active["fail_rate"] * 10.0
).round(2)

# Flag problem levels
problem_rate = problem_threshold / 100.0
active["is_problem"] = active["completion_rate"] < problem_rate

# ── KPI strip ────────────────────────────────────────────────────────────────
n_problem = int(active["is_problem"].sum())
worst_lvl = int(active.loc[active["completion_rate"].idxmin(), "level"])
best_rate = active["completion_rate"].max()
total_rage = int(active["rage_quits"].sum()) if "rage_quits" in active.columns else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Levels with data", len(active))
c2.metric(
    "Problem levels",
    n_problem,
    delta=f"below {problem_threshold}% completion",
    delta_color="inverse" if n_problem > 0 else "normal",
)
c3.metric("Worst completion — level", worst_lvl,
          delta=f"{best_rate:.0%} best rate")
c4.metric("Total rage quits", f"{total_rage:,}")

st.divider()

# ── Charts ───────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    section("Player funnel — starts per level", "🔻")
    st.caption(
        "Each bar shows how many unique players started that level. "
        "A steep drop between levels reveals where players are abandoning the game entirely."
    )
    st.plotly_chart(
        funnel(active, x="starts", y="level", title="Players who started each level"),
        use_container_width=True,
        key="chart_funnel",
    )

with col_r:
    section("Completion rate per level", "✅")
    rate_df = active.copy()
    rate_df["completion_%"] = (rate_df["completion_rate"] * 100).round(1)
    fig = bar(rate_df, x="level", y="completion_%", title="% who completed each level")
    # Colour bars below threshold red, above green
    colors = [DANGER if r < problem_threshold else SUCCESS for r in rate_df["completion_%"]]
    fig.update_traces(marker_color=colors)
    st.plotly_chart(fig, use_container_width=True, key="chart_completion_rate")

col_a, col_b = st.columns(2)

with col_a:
    section("Failures vs rage quits per level", "💢")
    st.caption(
        "**Failures** = players who tried and ran out of lives/time. "
        "**Rage quits** = players who gave up in frustration mid-level."
    )
    combo_df = active[active["starts"] > 0].copy()
    if not combo_df.empty:
        st.plotly_chart(
            multi_bar(combo_df, x="level", ys=["fails", "rage_quits"]),
            use_container_width=True,
            key="chart_fails_rage",
        )
    else:
        empty_state("No failure or rage-quit data")

with col_b:
    section("Drop-off rate per level", "📉")
    st.caption(
        "The % of players who started a level but never started the *next* one. "
        "High drop-off at level N means players stop playing after hitting that wall."
    )
    drop_df = active.copy()
    drop_df["drop_off_%"] = (drop_df["drop_off_rate"] * 100).round(1)
    fig2 = bar(drop_df, x="level", y="drop_off_%", title="Drop-off % per level")
    drop_colors = [DANGER if v >= 50 else (WARNING if v >= 25 else SUCCESS) for v in drop_df["drop_off_%"]]
    fig2.update_traces(marker_color=drop_colors)
    st.plotly_chart(fig2, use_container_width=True, key="chart_dropoff")

st.divider()

# ── Problem-level callout ────────────────────────────────────────────────────
if n_problem > 0:
    problem_levels = active[active["is_problem"]].sort_values("completion_rate")
    worst = problem_levels.iloc[0]
    lvl_list = ", ".join(f"**{int(r['level'])}**" for _, r in problem_levels.iterrows())
    st.warning(
        f"⚠️ **{n_problem} problem level(s)** with completion rate below "
        f"{problem_threshold}%: {lvl_list}  \n"
        f"Level **{int(worst['level'])}** is worst ({worst['completion_rate']:.0%} completion, "
        f"{int(worst['fails'])} fail(s), {int(worst['rage_quits'])} rage quit(s)).",
        icon="🔥",
    )

# ── Per-level detail table ───────────────────────────────────────────────────
section("Per-level breakdown", "📋")

# Apply sort
sort_map = {
    "Level (ascending)": ("level", True),
    "Worst completion rate": ("completion_rate", True),
    "Most failures": ("fails", False),
    "Most rage quits": ("rage_quits", False),
    "Highest frustration": ("frustration_score", False),
}
sort_col, sort_asc = sort_map[sort_by]
sorted_df = active.sort_values(sort_col, ascending=sort_asc)

display = sorted_df.rename(columns={
    "level": "Level",
    "starts": "Unique starters",
    "attempts": "Total attempts",
    "avg_attempts": "Avg attempts",
    "completes": "Completions",
    "fails": "Failures",
    "rage_quits": "Rage quits",
    "completion_rate": "Completion %",
    "fail_rate": "Fail %",
    "drop_off_rate": "Drop-off %",
    "frustration_score": "Frustration score",
}).copy()

for col_name in ["Completion %", "Fail %", "Drop-off %"]:
    if col_name in display.columns:
        display[col_name] = (display[col_name] * 100).round(1).astype(str) + "%"

# Drop internal flag column
display = display.drop(columns=["is_problem"], errors="ignore")

st.dataframe(display, use_container_width=True, hide_index=True)
download_csv(display, "funnel_breakdown.csv", key="dl_funnel")

st.caption(
    "**Avg attempts** — how many times a typical player tried this level before passing or quitting.  \n"
    "**Drop-off %** — share of players who started this level but never started the next one.  \n"
    "**Frustration score** — rage quits × 2 + fail rate × 10. Higher = more frustrating."
)
