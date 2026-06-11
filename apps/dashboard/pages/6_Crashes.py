import pandas as pd
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.charts import area, bar, pie
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
page_header("💥 Crashes & Errors", "Crash trends, breakdowns, and stack traces")

# ── Filters ──────────────────────────────────────────────────────────────────
days = date_range(default="Last 7 days")
severity_choice = st.sidebar.selectbox(
    "Severity", ["All", "fatal", "critical", "warning", "error"], index=0
)
severity = None if severity_choice == "All" else severity_choice
exclude_sim = sim_data_filter()

with with_spinner("Fetching crash analytics…"):
    try:
        data = get(
            "/v1/query/crashes/analytics",
            days=days,
            severity=severity,
            exclude_simulated=exclude_sim,
        )
    except Exception as e:
        api_error(e)

totals = data.get("totals", {})

if totals.get("crashes", 0) == 0:
    empty_state(
        "No crashes in this window 🎉",
        "Widen the date range, or run a simulation / integrate the SDK to see crash data.",
    )
    st.stop()

# ── KPI row ──────────────────────────────────────────────────────────────────
crash_free = totals.get("crash_free_rate", 1.0)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total crashes", f"{totals.get('crashes', 0):,}")
c2.metric(
    "Crash-free sessions",
    f"{crash_free:.1%}",
    delta="✓ healthy" if crash_free >= 0.99 else "⚠ degraded",
    delta_color="normal" if crash_free >= 0.99 else "inverse",
)
c3.metric("Affected players", f"{totals.get('affected_players', 0):,}")
c4.metric("Affected sessions", f"{totals.get('affected_sessions', 0):,}")
c5.metric("Unique crashes", f"{totals.get('unique_fingerprints', 0):,}")

st.divider()

# ── Crashes over time (centerpiece) ──────────────────────────────────────────
section("Crashes over time", "📈")
over_time = data.get("over_time", [])
if over_time:
    ot_df = pd.DataFrame(over_time)
    st.plotly_chart(
        area(ot_df, x="day", y="crashes", title="Daily crash count"),
        use_container_width=True,
        key="chart_crashes_over_time",
    )
else:
    empty_state("No time-series data for this window")

# ── Breakdowns ───────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    section("By severity", "🚦")
    by_sev = data.get("by_severity", {})
    if by_sev:
        sev_df = pd.DataFrame(
            {"severity": list(by_sev.keys()), "count": list(by_sev.values())}
        )
        st.plotly_chart(
            pie(sev_df, names="severity", values="count"),
            use_container_width=True,
            key="chart_crash_severity",
        )
    else:
        empty_state("No severity data")

with col_r:
    section("By platform", "🖥️")
    by_plat = data.get("by_platform", {})
    if by_plat:
        plat_df = pd.DataFrame(
            {"platform": list(by_plat.keys()), "count": list(by_plat.values())}
        )
        st.plotly_chart(
            bar(plat_df, x="platform", y="count"),
            use_container_width=True,
            key="chart_crash_platform",
        )
    else:
        empty_state("No platform data")

section("By app version", "🏷️")
by_ver = data.get("by_version", {})
if by_ver:
    ver_df = pd.DataFrame(
        {"app_version": list(by_ver.keys()), "count": list(by_ver.values())}
    )
    st.plotly_chart(
        bar(ver_df, x="app_version", y="count", title="Crashes by app version"),
        use_container_width=True,
        key="chart_crash_version",
    )
else:
    st.caption("No app-version data — crashes are not yet attributed to a version.")

st.divider()

# ── Top crash groups + detail ────────────────────────────────────────────────
section("Top crash groups", "🔍")
top = data.get("top_fingerprints", [])
if top:
    top_df = pd.DataFrame(top)
    display = top_df[
        [c for c in ["exc_type", "message", "count", "severity", "first_seen", "last_seen", "fingerprint"] if c in top_df.columns]
    ].copy()
    for col_name in ["first_seen", "last_seen"]:
        if col_name in display.columns:
            display[col_name] = pd.to_datetime(display[col_name], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display, use_container_width=True, hide_index=True)
    download_csv(display, "crash_groups.csv", key="dl_crash_groups")

    # Detail / stack viewer
    section("Crash detail & stack trace", "📄")
    labels = {
        f"{r.get('exc_type', '?')} — {(r.get('message') or '')[:60]} ({r['fingerprint'][:8]})": r["fingerprint"]
        for r in top
    }
    pick = st.selectbox("Select a crash group", list(labels.keys()), index=0)
    fp = labels[pick]
    chosen = next((r for r in top if r["fingerprint"] == fp), None)
    if chosen:
        d1, d2, d3 = st.columns(3)
        d1.metric("Occurrences", f"{chosen.get('count', 0):,}")
        d2.metric("First seen", str(chosen.get("first_seen", ""))[:16] or "—")
        d3.metric("Last seen", str(chosen.get("last_seen", ""))[:16] or "—")
        st.markdown(
            f"**`{chosen.get('exc_type', '')}`** — {chosen.get('message') or '_no message_'}  \n"
            f"Severity: `{chosen.get('severity', 'unknown')}` · Fingerprint: `{fp}`"
        )
        st.code(chosen.get("stacktrace") or "No stack trace captured.", language="python")
else:
    empty_state("No crash groups in this window")

# ── Recent crash log ─────────────────────────────────────────────────────────
section("Recent crash log", "📋")
recent = data.get("recent", [])
if recent:
    rec_df = pd.DataFrame(recent)
    cols = [c for c in ["occurred_at", "exc_type", "message", "severity", "fingerprint", "player_id", "session_id"] if c in rec_df.columns]
    rec_df = rec_df[cols]
    if "occurred_at" in rec_df.columns:
        rec_df["occurred_at"] = pd.to_datetime(rec_df["occurred_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(rec_df, use_container_width=True, hide_index=True, height=400)
    download_csv(rec_df, "recent_crashes.csv", key="dl_recent_crashes")
else:
    empty_state("No recent crashes")
