import pandas as pd
import plotly.express as px
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.charts import area, line, pie
from lib.filters import date_range, dimension_filter, search_box, sim_data_filter
from lib.theme import PALETTE, chart_defaults
from lib.ui import (
    api_error,
    download_csv,
    empty_state,
    page_header,
    section,
    with_spinner,
)

require_project()
page_header("🕹️ Sessions", "Session trends, durations, and end-reason breakdown")

# ── Sidebar filters ──────────────────────────────────────────────────────────
days = date_range(default="Last 7 days")
table_limit = st.sidebar.slider("Table rows", 50, 2000, 500, step=50)
exclude_sim = sim_data_filter()

with with_spinner("Loading session analytics…"):
    try:
        data = get(
            "/v1/query/sessions/analytics",
            days=days,
            limit=table_limit,
            exclude_simulated=exclude_sim,
        )
    except Exception as e:
        api_error(e)

totals = data.get("totals", {})

if totals.get("sessions", 0) == 0:
    empty_state(
        "No sessions in this window",
        "Widen the date range, or run a simulation to generate session data.",
    )
    st.stop()

# ── KPI row ──────────────────────────────────────────────────────────────────
avg_s = totals.get("avg_duration_s", 0)
med_s = totals.get("median_duration_s", 0)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total sessions", f"{totals['sessions']:,}")
c2.metric("Finished sessions", f"{totals.get('finished', 0):,}")
c3.metric("Avg duration", f"{avg_s:.0f} s" if avg_s else "—")
c4.metric("Median duration", f"{med_s} s" if med_s else "—")
rage_rate = totals.get("rage_quits", 0) / totals["sessions"] if totals["sessions"] else 0
c5.metric(
    "Rage-quit rate",
    f"{rage_rate:.1%}",
    delta="⚠ high" if rage_rate >= 0.15 else "ok",
    delta_color="inverse" if rage_rate >= 0.15 else "normal",
)

st.divider()

# ── Time series ──────────────────────────────────────────────────────────────
over_time = data.get("over_time", [])
if over_time:
    ot_df = pd.DataFrame(over_time)

    col_l, col_r = st.columns(2)
    with col_l:
        section("Sessions over time", "📅")
        st.plotly_chart(
            area(ot_df, x="day", y="sessions", title="Daily sessions"),
            use_container_width=True,
            key="chart_sessions_ot",
        )
    with col_r:
        section("Avg session duration over time", "⏱️")
        if "avg_duration_s" in ot_df.columns:
            st.plotly_chart(
                line(ot_df, x="day", y="avg_duration_s", title="Avg duration (s)"),
                use_container_width=True,
                key="chart_duration_ot",
            )
        else:
            empty_state("No duration data in this window")

    st.divider()

# ── End reasons + duration histogram ────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    section("Session end reasons", "🏁")
    end_reasons = data.get("end_reasons", {})
    if end_reasons:
        er_df = pd.DataFrame(
            {"reason": list(end_reasons.keys()), "count": list(end_reasons.values())}
        )
        st.plotly_chart(
            pie(er_df, names="reason", values="count"),
            use_container_width=True,
            key="chart_end_reasons",
        )
    else:
        empty_state("No end-reason data")

with col_b:
    section("Session duration distribution", "⏱️")
    recent = data.get("recent", [])
    if recent:
        dur_df = pd.DataFrame(recent)
        finished_df = dur_df.dropna(subset=["duration_s"]) if "duration_s" in dur_df.columns else pd.DataFrame()
        if not finished_df.empty:
            fig = px.histogram(
                finished_df,
                x="duration_s",
                nbins=30,
                labels={"duration_s": "Duration (s)"},
                color_discrete_sequence=[PALETTE[0]],
            )
            fig.update_layout(**chart_defaults(), title="Duration distribution")
            st.plotly_chart(fig, use_container_width=True, key="chart_duration_hist")
        else:
            empty_state("No finished sessions to chart")
    else:
        empty_state("No session data")

st.divider()

# ── Recent sessions table with client-side dimension filters ─────────────────
section("Recent sessions", "📋")

recent = data.get("recent", [])
if recent:
    df = pd.DataFrame(recent)

    # Client-side filters (sidebar)
    df = dimension_filter(df, "platform", key="ses_platform")
    df = dimension_filter(df, "app_version", label="App version", key="ses_appver")
    df = dimension_filter(df, "end_reason", label="End reason", key="ses_endreason")
    df = search_box(df, ["player_id", "id"], label="Search player / session ID", key="ses_search")

    if df.empty:
        empty_state("No sessions match the current filters", "Try clearing the sidebar filters")
    else:
        st.caption(f"Showing {len(df):,} session(s)")
        display = df.copy()
        for col_name in ["started_at", "ended_at"]:
            if col_name in display.columns:
                display[col_name] = (
                    pd.to_datetime(display[col_name], errors="coerce")
                    .dt.strftime("%Y-%m-%d %H:%M:%S")
                )
        shown_cols = [c for c in ["started_at", "ended_at", "duration_s", "end_reason", "platform", "app_version", "player_id", "id"] if c in display.columns]
        st.dataframe(display[shown_cols], use_container_width=True, hide_index=True, height=460)
        download_csv(display[shown_cols], "sessions.csv", key="dl_sessions")

        st.caption(
            "💡 Copy a **player_id** and paste it into the **Player Timeline** page "
            "to see every event for that player."
        )
else:
    empty_state("No sessions to display")
