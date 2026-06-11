import pandas as pd
import streamlit as st
from lib.api_client import get
from lib.auth import require_project
from lib.ui import api_error, empty_state, page_header, section, with_spinner

require_project()
page_header("👤 Player Timeline", "Full event history for a single player")

player_id = st.sidebar.text_input("Player external ID", placeholder="e.g. user_123")
event_limit = st.sidebar.slider("Max events", 50, 1000, 200)

if not player_id:
    empty_state("Enter a player ID in the sidebar to view their timeline")
    st.stop()

with with_spinner(f"Loading timeline for {player_id}…"):
    try:
        data = get(f"/v1/query/players/{player_id}/timeline", limit=event_limit)
    except Exception as e:
        api_error(e)

player = data.get("player")
if not player:
    empty_state(f"Player `{player_id}` not found", "Check the ID and try again")
    st.stop()

# ── Player card ────────────────────────────────────────────────────────────
section("Player profile", "🪪")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Platform", player.get("platform") or "—")
c2.metric("Country", player.get("country") or "—")
c3.metric("App version", player.get("app_version") or "—")
c4.metric("First seen", str(player.get("first_seen_at", ""))[:10])
c5.metric("Last seen", str(player.get("last_seen_at", ""))[:10])

sessions = data.get("sessions", [])
events = data.get("events", [])
crashes = data.get("crashes", [])

st.divider()

# ── Sessions ───────────────────────────────────────────────────────────────
section(f"Sessions ({len(sessions)})", "🕹️")
if sessions:
    sess_df = pd.DataFrame(sessions)
    for col in ["started_at", "ended_at"]:
        if col in sess_df.columns:
            sess_df[col] = pd.to_datetime(sess_df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(sess_df, use_container_width=True, hide_index=True)
else:
    empty_state("No sessions for this player")

# ── Crashes ────────────────────────────────────────────────────────────────
if crashes:
    section(f"Crashes ({len(crashes)})", "💥")
    crash_df = pd.DataFrame(crashes)
    if "occurred_at" in crash_df.columns:
        crash_df["occurred_at"] = pd.to_datetime(crash_df["occurred_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(crash_df, use_container_width=True, hide_index=True)

# ── Event log ──────────────────────────────────────────────────────────────
section(f"Event log ({len(events)})", "📋")
type_filter = st.text_input("Filter by event type", "")
if events:
    ev_df = pd.DataFrame(events)
    if type_filter and "type" in ev_df.columns:
        ev_df = ev_df[ev_df["type"].str.contains(type_filter, case=False, na=False)]
    if "occurred_at" in ev_df.columns:
        ev_df["occurred_at"] = pd.to_datetime(ev_df["occurred_at"], errors="coerce").dt.strftime("%H:%M:%S")
    display_cols = [c for c in ["occurred_at", "type", "name", "payload", "session_id"] if c in ev_df.columns]
    st.dataframe(ev_df[display_cols], use_container_width=True, hide_index=True, height=400)
else:
    empty_state("No events for this player")
