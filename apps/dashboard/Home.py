import streamlit as st
from lib.api_client import API_URL, is_healthy
from lib.auth import require_login
from lib.ui import error_state, page_header


def home_page():
    page_header(
        "🎮 GamePulse",
        "Real-time game analytics — sessions, progression, economy, crashes",
    )

    if is_healthy():
        st.success(f"API connected — `{API_URL}`", icon="✅")
    else:
        error_state(
            f"Cannot reach API at `{API_URL}`. "
            "Set `GAMEPULSE_DASHBOARD_API_URL` and run `make api`."
        )

    st.markdown(
        """
        ### Navigation

        Use the **sidebar** to jump between modules:

        | Page | What you'll find |
        |------|-----------------|
        | 📊 Overview | DAU, sessions, crash-free rate — the executive summary |
        | 👥 Players | Active players, breakdown by platform / country |
        | 🕹️ Sessions | Recent sessions, duration histogram, end-reason pie |
        | 🎯 Funnels | Level-completion funnel, per-level pass rates |
        | 💰 Economy | Currency flows, item popularity, IAP revenue |
        | 💥 Crashes | Top crash fingerprints, stack viewer |
        | 📡 Live Events | Tail of recent telemetry events |
        | 📈 Retention | Day-N retention cohorts |
        | 👤 Player Timeline | Per-player event history |
        | 🎮 Simulation | Generate realistic demo data for any project |
        | ⚙️ Settings | Project config, SDK snippet, env inspector |

        ---

        ### Quick start

        ```bash
        make api          # FastAPI on :8000
        make dashboard    # Streamlit on :8501
        make simulate     # Generate 25 synthetic players for 60 s
        ```

        Or use the **Simulation** page to generate demo data directly from the dashboard.
        """
    )


st.set_page_config(
    page_title="GamePulse",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown(
        "<div style='padding:10px 0 6px 0;'>"
        "<span style='font-size:1.25rem;font-weight:700;letter-spacing:-.01em;'>🎮 GamePulse</span><br>"
        "<span style='font-size:0.78rem;color:#64748b;'>Game Analytics SDK</span>"
        "</div>",
        unsafe_allow_html=True,
    )

require_login()

pg = st.navigation(
    {
        "": [
            st.Page(home_page, title="Home", icon="🏠", default=True, url_path=""),
            st.Page("pages/0_Projects.py", title="Projects", icon="📁"),
        ],
        "Analytics": [
            st.Page("pages/1_Overview.py", title="Overview", icon="📊"),
            st.Page("pages/2_Players.py", title="Players", icon="👥"),
            st.Page("pages/3_Sessions.py", title="Sessions", icon="🕹️"),
            st.Page("pages/4_Funnels.py", title="Funnels", icon="🎯"),
            st.Page("pages/5_Economy.py", title="Economy", icon="💰"),
            st.Page("pages/6_Crashes.py", title="Crashes", icon="💥"),
            st.Page("pages/12_Rage_Quits.py", title="Rage Quits", icon="😤"),
            st.Page("pages/7_Live_Events.py", title="Live Events", icon="📡"),
            st.Page("pages/9_Retention.py", title="Retention", icon="📈"),
            st.Page("pages/10_Player_Timeline.py", title="Player Timeline", icon="👤"),
        ],
        "Tools": [
            st.Page("pages/11_Simulation.py", title="Simulation", icon="🎮"),
        ],
        "Admin": [
            st.Page("pages/8_Settings.py", title="Settings", icon="⚙️"),
        ],
    }
)
pg.run()
