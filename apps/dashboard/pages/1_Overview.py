import pandas as pd
import streamlit as st
from lib.api_client import get
from lib.auth import require_project
from lib.charts import area, multi_bar
from lib.filters import lookback_days, sim_data_filter
from lib.ui import api_error, empty_state, page_header, section, with_spinner

require_project()
page_header("📊 Overview", "Platform-wide health at a glance")

days = lookback_days(default=7)
exclude_sim = sim_data_filter()

with with_spinner("Fetching overview…"):
    try:
        data = get("/v1/query/overview", days=days, exclude_simulated=exclude_sim)
    except Exception as e:
        api_error(e)

totals = data.get("totals", {})

# ── KPI row ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total sessions", f"{totals.get('sessions', 0):,}")
c2.metric("Avg session", f"{totals.get('avg_session_s', 0):.0f} s")
c3.metric("Crashes", f"{totals.get('crashes', 0):,}")
c4.metric("Rage quits", f"{totals.get('rage_quits', 0):,}")
crash_free = totals.get("crash_free_rate", 1.0)
c5.metric(
    "Crash-free rate",
    f"{crash_free:.1%}",
    delta=f"{'✓ healthy' if crash_free >= 0.99 else '⚠ degraded'}",
    delta_color="normal" if crash_free >= 0.99 else "inverse",
)

st.divider()

dau_rows = data.get("dau", [])
stats_rows = data.get("session_stats", [])

col_l, col_r = st.columns(2)

with col_l:
    section("Daily Active Users", "👥")
    if dau_rows:
        dau_df = pd.DataFrame(dau_rows)
        st.plotly_chart(area(dau_df, x="day", y="dau"), use_container_width=True, key="chart_dau")
    else:
        empty_state("No DAU data yet", "Run `make simulate` to generate traffic")

with col_r:
    section("Sessions vs Crashes per Day", "📅")
    if stats_rows:
        stats_df = pd.DataFrame(stats_rows)
        st.plotly_chart(
            multi_bar(stats_df, x="day", ys=["sessions", "crashes", "rage_quits"]),
            use_container_width=True,
            key="chart_session_stats",
        )
    else:
        empty_state("No session data yet")

if stats_rows:
    section("Day-by-day breakdown", "📋")
    df = pd.DataFrame(stats_rows).rename(columns={
        "day": "Day",
        "sessions": "Sessions",
        "avg_duration_s": "Avg duration (s)",
        "crashes": "Crashes",
        "rage_quits": "Rage quits",
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
