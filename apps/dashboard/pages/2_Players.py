import pandas as pd
import streamlit as st
from lib.api_client import get
from lib.auth import require_project
from lib.charts import pie
from lib.filters import lookback_days, row_limit, sim_data_filter
from lib.ui import api_error, empty_state, page_header, section, with_spinner

require_project()
page_header("👥 Players", "Active player breakdown and demographics")

days = lookback_days(default=30, max_days=365)
limit = row_limit(default=500, max_n=2000)
exclude_sim = sim_data_filter()

with with_spinner("Fetching player data…"):
    try:
        data = get("/v1/query/players", days=days, limit=limit, exclude_simulated=exclude_sim)
    except Exception as e:
        api_error(e)

total = data.get("total", 0)
st.metric(f"Active players (last {days} days)", f"{total:,}")
st.divider()

if total == 0:
    empty_state("No players in this window", "Extend the lookback or run the simulator")
    st.stop()

c1, c2, c3 = st.columns(3)

for col, label, data_key, chart_key in (
    (c1, "By platform",    "by_platform",    "chart_platform"),
    (c2, "By country",     "by_country",     "chart_country"),
    (c3, "By app version", "by_app_version", "chart_appver"),
):
    rows = sorted(data.get(data_key, {}).items(), key=lambda kv: -kv[1])[:12]
    df = pd.DataFrame(rows, columns=["label", "count"])
    with col:
        section(label)
        if df.empty:
            empty_state("No data")
        else:
            st.plotly_chart(pie(df, names="label", values="count"), use_container_width=True, key=chart_key)

section("Player list", "📋")
players_df = pd.DataFrame(data.get("players", []))
if not players_df.empty:
    if "first_seen_at" in players_df.columns:
        players_df["first_seen_at"] = pd.to_datetime(players_df["first_seen_at"]).dt.strftime("%Y-%m-%d")
    if "last_seen_at" in players_df.columns:
        players_df["last_seen_at"] = pd.to_datetime(players_df["last_seen_at"]).dt.strftime("%Y-%m-%d")
    st.dataframe(players_df, use_container_width=True, hide_index=True)
