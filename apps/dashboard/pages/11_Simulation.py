import streamlit as st
from lib.api_client import authed_get, authed_post
from lib.auth import require_project
from lib.ui import page_header, section

require_project()
page_header("🎮 Simulation", "Generate realistic demo data for this project")

active = st.session_state.get("active_project", {})
project_id = active.get("id", "")
project_name = active.get("name", "Unknown Project")

st.info(
    "**Demo Data Generator** — all generated players, sessions, events, crashes, and rage quits "
    "are **simulated fake data** scoped exclusively to the active project: "
    f"**{project_name}**.  \nNo real users are affected.",
    icon="ℹ️",
)

st.divider()


def _run_simulation(params: dict) -> None:
    with st.spinner("Running simulation… this may take a few seconds."):
        try:
            result = authed_post(
                f"/v1/manage/projects/{project_id}/simulate",
                json=params,
                timeout=120.0,
            )
            st.session_state["sim_result"] = result
            st.session_state["sim_error"] = None
        except Exception as e:
            st.session_state["sim_result"] = None
            st.session_state["sim_error"] = str(e)
    st.rerun()


tab_quick, tab_custom = st.tabs(["⚡ Quick Simulation", "⚙️ Custom Simulation"])

# ── Quick simulation ───────────────────────────────────────────────────────────
with tab_quick:
    section("Average Simulation", "▶")

    col_left, col_right = st.columns([2, 3], gap="large")

    with col_left:
        st.markdown(
            "Generates a **realistic mix** of player activity spread over the past **7 days**.  \n"
            "Good for populating a fresh project before exploring the dashboards."
        )
        if st.button("▶  Run Average Simulation", type="primary", use_container_width=True):
            _run_simulation({
                "players": 30,
                "time_spread_days": 7,
                "crash_rate": 0.05,
                "rage_quit_rate": 0.10,
                "level_fail_rate": 0.35,
                "spend_rate": 0.15,
            })
        st.caption("Estimated time: 2 – 10 s · Max 200 players · Project-scoped only")

    with col_right:
        st.markdown(
            "**What gets created:**\n"
            "- 30 simulated players with mixed personas (casual, whale, rage-quitter, crasher)\n"
            "- 1–3 sessions per player distributed across the past week\n"
            "- Level start / complete / fail progression events\n"
            "- Gold earn & spend economy events, plus some IAP purchases\n"
            "- A handful of crashes with stack traces\n"
            "- A handful of rage quits\n"
        )

# ── Custom simulation ──────────────────────────────────────────────────────────
with tab_custom:
    section("Custom Simulation", "⚙")

    st.markdown(
        "Configure exactly what scenario to simulate.  \n"
        "Useful for testing edge cases like a crash-heavy release or a whale-heavy cohort."
    )

    with st.form("custom_sim_form"):
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("**Players & time window**")
            n_players = st.slider("Number of players", 1, 200, 30, step=5)
            spread_days = st.slider(
                "Spread data over (days)", 1, 30, 7, step=1,
                help="Sessions are distributed randomly across this many past days.",
            )

        with col_b:
            st.markdown("**Event rates**")
            crash_pct = st.slider(
                "Crash rate", 0, 50, 5, format="%d%%",
                help="Percentage of sessions that end in a crash.",
            )
            rage_pct = st.slider(
                "Rage quit rate", 0, 50, 10, format="%d%%",
                help="Percentage of sessions that end in a rage quit.",
            )
            fail_pct = st.slider(
                "Level fail rate", 0, 100, 35, format="%d%%",
                help="Percentage of level attempts that fail.",
            )
            spend_pct = st.slider(
                "Spend rate (per level)", 0, 100, 15, format="%d%%",
                help="Percentage of completed levels where the player spends gold.",
            )

        st.markdown("**Persona mix** — drag to set the relative weight of each player archetype")
        pc1, pc2, pc3, pc4 = st.columns(4)
        w_casual = pc1.slider("Casual", 0, 10, 5, key="w_casual",
                              help="Low spend, low crash, medium session length.")
        w_whale = pc2.slider("Whale", 0, 10, 1, key="w_whale",
                             help="High IAP spend, long sessions.")
        w_rage = pc3.slider("Rage-quitter", 0, 10, 2, key="w_rage",
                            help="Short sessions, high rage-quit rate.")
        w_crasher = pc4.slider("Crasher", 0, 10, 2, key="w_crasher",
                               help="High crash rate, short sessions.")

        submitted = st.form_submit_button("▶  Run Custom Simulation", type="primary")

    if submitted:
        total_w = w_casual + w_whale + w_rage + w_crasher
        if total_w == 0:
            st.warning("All persona weights are zero — using equal mix.")
            total_w = 4
            w_casual = w_whale = w_rage = w_crasher = 1

        _run_simulation({
            "players": n_players,
            "time_spread_days": spread_days,
            "crash_rate": crash_pct / 100.0,
            "rage_quit_rate": rage_pct / 100.0,
            "level_fail_rate": fail_pct / 100.0,
            "spend_rate": spend_pct / 100.0,
            "persona_mix": {
                "casual": w_casual / total_w,
                "whale": w_whale / total_w,
                "rage_quitter": w_rage / total_w,
                "crasher": w_crasher / total_w,
            },
        })

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.get("sim_error"):
    st.divider()
    st.error(f"Simulation failed: {st.session_state['sim_error']}")

if st.session_state.get("sim_result"):
    r = st.session_state["sim_result"]
    st.divider()
    section("Simulation complete", "✅")

    c1, c2, c3 = st.columns(3)
    c1.metric("Players created", f"{r.get('players_created', 0):,}")
    c2.metric("Sessions created", f"{r.get('sessions_created', 0):,}")
    c3.metric("Events generated", f"{r.get('events_generated', 0):,}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Crashes generated", f"{r.get('crashes_generated', 0):,}")
    c5.metric("Rage quits generated", f"{r.get('rage_quits_generated', 0):,}")
    c6.metric("Economy events", f"{r.get('economy_events_generated', 0):,}")

    elapsed = r.get("elapsed_s", 0)
    st.caption(f"Completed in {elapsed:.1f} s")

    st.success(
        "Your data is live — head to any dashboard page to explore it:  \n"
        "→ **Overview** — session trends and crash-free rate  \n"
        "→ **Players** — breakdown by country, platform, and version  \n"
        "→ **Funnels** — level completion funnel  \n"
        "→ **Economy** — gold flows and IAP revenue  \n"
        "→ **Crashes** — top error fingerprints with stack traces  \n"
        "→ **Retention** — day-1 / day-7 cohort retention"
    )

    if st.button("Clear results", key="clear_sim_results"):
        st.session_state.pop("sim_result", None)
        st.session_state.pop("sim_error", None)
        st.rerun()

# ── Demo data management ───────────────────────────────────────────────────────
st.divider()
section("Manage Demo Data", "🗑️")

try:
    stats = authed_get(f"/v1/manage/projects/{project_id}/simulate/stats")
except Exception as e:
    st.warning(f"Could not load demo data stats: {e}")
    stats = {}

total_sim = sum(stats.values()) if stats else 0

if total_sim == 0:
    st.caption("No simulated data exists for this project yet.")
else:
    st.markdown("**Current simulated data in this project:**")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Players", f"{stats.get('players', 0):,}")
    sc2.metric("Sessions", f"{stats.get('sessions', 0):,}")
    sc3.metric("Events", f"{stats.get('events', 0):,}")
    sc4.metric("Crashes", f"{stats.get('crashes', 0):,}")

    st.caption(
        "Use the **Hide demo/simulated data** toggle in the sidebar on any analytics page "
        "to exclude this data from charts. Or delete it permanently below."
    )

    if not st.session_state.get("confirm_clear_sim"):
        if st.button("🗑️  Delete all demo data", type="secondary"):
            st.session_state["confirm_clear_sim"] = True
            st.rerun()
    else:
        st.warning(
            f"This will permanently delete **{total_sim:,} simulated records** "
            f"({stats.get('players', 0):,} players, {stats.get('sessions', 0):,} sessions, "
            f"{stats.get('events', 0):,} events, {stats.get('crashes', 0):,} crashes) "
            "from this project. Real SDK data is never touched."
        )
        col_confirm, col_cancel = st.columns([1, 4])
        with col_confirm:
            if st.button("Confirm delete", type="primary"):
                with st.spinner("Deleting simulated data…"):
                    try:
                        result = authed_post(
                            f"/v1/manage/projects/{project_id}/simulate/clear",
                            timeout=30.0,
                        )
                        st.session_state["confirm_clear_sim"] = False
                        st.session_state["clear_result"] = result
                    except Exception as e:
                        st.session_state["confirm_clear_sim"] = False
                        st.error(f"Delete failed: {e}")
                st.rerun()
        with col_cancel:
            if st.button("Cancel"):
                st.session_state["confirm_clear_sim"] = False
                st.rerun()

if st.session_state.get("clear_result"):
    cr = st.session_state.pop("clear_result")
    deleted = cr.get("deleted", {})
    st.success(
        f"Deleted: {deleted.get('players', 0):,} players · "
        f"{deleted.get('sessions', 0):,} sessions · "
        f"{deleted.get('events', 0):,} events · "
        f"{deleted.get('crashes', 0):,} crashes"
    )
