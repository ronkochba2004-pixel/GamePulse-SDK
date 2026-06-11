import pandas as pd
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.filters import sim_data_filter
from lib.ui import api_error, empty_state, page_header, section, with_spinner

require_project()
page_header("📈 Retention", "Day-N player retention cohorts")

cohort_days = st.sidebar.slider("Cohort window (days)", 7, 60, 14)
max_day_n = st.sidebar.slider("Max day-N", 3, 14, 7)
exclude_sim = sim_data_filter()

with with_spinner("Calculating retention cohorts…"):
    try:
        data = get("/v1/query/retention", cohort_days=cohort_days, max_day_n=max_day_n, exclude_simulated=exclude_sim)
    except Exception as e:
        api_error(e)

cohorts = data.get("cohorts", [])
day_cols = [f"day_{n}" for n in range(1, max_day_n + 1)]
rate_cols = [f"day_{n}_rate" for n in range(1, max_day_n + 1)]

if not cohorts:
    empty_state(
        "Not enough data for cohort analysis",
        f"You need players from at least 2 different days in the last {cohort_days} days",
    )
    st.stop()

df = pd.DataFrame(cohorts)

# ── Summary KPIs ──────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Cohorts", len(df))
c2.metric("Total players", f"{df['size'].sum():,}")
best_avg = df[rate_cols[0]].mean() if rate_cols and rate_cols[0] in df else 0
c3.metric("Avg Day-1 retention", f"{best_avg:.1%}")

st.divider()

# ── Heatmap ───────────────────────────────────────────────────────────────
section("Retention heatmap (rates)", "🟦")
rate_df = df[["cohort"] + [c for c in rate_cols if c in df.columns]].set_index("cohort")
rate_df.columns = [c.replace("_rate", "").replace("_", " ").title() for c in rate_df.columns]

if not rate_df.empty:
    import plotly.graph_objects as go
    from lib.theme import chart_defaults
    z = rate_df.values.tolist()
    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(rate_df.columns),
        y=list(rate_df.index),
        colorscale="Blues",
        text=[[f"{v:.0%}" for v in row] for row in z],
        texttemplate="%{text}",
        showscale=True,
        zmin=0, zmax=1,
    ))
    fig.update_layout(title="Day-N retention rates by cohort", **chart_defaults())
    st.plotly_chart(fig, use_container_width=True, key="chart_retention_heatmap")

# ── Day-1 trend ───────────────────────────────────────────────────────────
if "day_1_rate" in df.columns:
    section("Day-1 retention trend", "📉")
    trend = df[["cohort", "day_1_rate"]].copy()
    trend["day_1_%"] = (trend["day_1_rate"] * 100).round(1)
    from lib.charts import line
    st.plotly_chart(line(trend, x="cohort", y="day_1_%", title="Day-1 retention % over cohorts"), use_container_width=True, key="chart_day1_trend")

# ── Raw table ─────────────────────────────────────────────────────────────
section("Cohort detail table", "📋")
display = df[["cohort", "size"] + [c for c in day_cols if c in df.columns]].copy()
st.dataframe(display, use_container_width=True, hide_index=True)
