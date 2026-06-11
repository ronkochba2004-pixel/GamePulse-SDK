import pandas as pd
import streamlit as st
from lib.api_client import get_cached as get
from lib.auth import require_project
from lib.charts import bar, pie
from lib.filters import lookback_days, sim_data_filter
from lib.ui import api_error, empty_state, page_header, section, with_spinner

require_project()
page_header("💰 Economy", "Currency flows, item purchases, and in-app revenue")

days = lookback_days(default=30, max_days=365)
exclude_sim = sim_data_filter()

with with_spinner("Fetching economy data…"):
    try:
        data = get("/v1/query/economy/summary", days=days, exclude_simulated=exclude_sim)
    except Exception as e:
        api_error(e)

earned = data.get("earned", {})
spent = data.get("spent", {})
iap = data.get("iap", {}) or {}
top_items = data.get("top_items", [])

has_data = bool(earned or spent or top_items or iap.get("count", 0))

if not has_data:
    empty_state(
        "No economy events in this window",
        "The simulator generates currency_earn, currency_spend, and iap events",
    )
    st.stop()

# IAP KPI strip
iap_rev = iap.get("revenue_by_currency", {})
iap_count = iap.get("count", 0)
total_iap_usd = sum(v for k, v in iap_rev.items() if k in ("USD", "usd"))
c1, c2, c3 = st.columns(3)
c1.metric("IAP transactions", f"{iap_count:,}")
c2.metric("IAP revenue (USD)", f"${total_iap_usd:,.2f}")
c3.metric("Currencies tracked", len({*earned.keys(), *spent.keys()}))

st.divider()
col_l, col_r = st.columns(2)

with col_l:
    section("Currency earned", "📈")
    if earned:
        df_e = pd.DataFrame(list(earned.items()), columns=["Currency", "Amount"])
        st.plotly_chart(bar(df_e, x="Currency", y="Amount"), use_container_width=True, key="chart_earned")
    else:
        empty_state("No earn events")

with col_r:
    section("Currency spent", "📉")
    if spent:
        df_s = pd.DataFrame(list(spent.items()), columns=["Currency", "Amount"])
        st.plotly_chart(bar(df_s, x="Currency", y="Amount"), use_container_width=True, key="chart_spent")
    else:
        empty_state("No spend events")

col_a, col_b = st.columns(2)

with col_a:
    section("Top items purchased", "🛒")
    if top_items:
        items_df = pd.DataFrame(top_items, columns=["Item", "Count"])
        st.plotly_chart(
            pie(items_df, names="Item", values="Count", hole=0.35),
            use_container_width=True,
            key="chart_top_items",
        )
    else:
        empty_state("No item data")

with col_b:
    section("IAP revenue by currency", "💳")
    if iap_rev:
        rev_df = pd.DataFrame(list(iap_rev.items()), columns=["Currency", "Revenue"])
        st.plotly_chart(bar(rev_df, x="Currency", y="Revenue"), use_container_width=True, key="chart_iap_rev")
    else:
        empty_state("No IAP events")
