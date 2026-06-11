import os

import streamlit as st
from lib.api_client import API_KEY, API_URL, is_healthy
from lib.ui import page_header, section

page_header("⚙️ Settings & Project Info", "Configuration, SDK snippets, and diagnostics")

# ── API status ─────────────────────────────────────────────────────────────
section("API status", "🔌")
if is_healthy():
    st.success(f"Connected to `{API_URL}`")
else:
    st.error(f"Cannot reach `{API_URL}` — check `GAMEPULSE_DASHBOARD_API_URL`")

# ── Active project ─────────────────────────────────────────────────────────
section("Active project", "🏷️")
active = st.session_state.get("active_project")
if active:
    c1, c2, c3 = st.columns(3)
    c1.metric("Name", active.get("name", "—"))
    c2.metric("Slug", active.get("slug", "—"))
    c3.metric("Created", str(active.get("created_at", "—"))[:10])
    api_key = active.get("api_key", API_KEY)
    st.text_input("API Key", value=api_key, disabled=True)
    st.caption("Go to **Projects** to rotate your key or create a new project.")
else:
    st.info("No project selected. Go to **Projects** to select or create one.")
    api_key = API_KEY
    masked = f"{api_key[:6]}…{api_key[-2:]}" if len(api_key) > 8 else "***"
    st.caption(f"Using env default API key: `{masked}`")

# ── SDK snippet ────────────────────────────────────────────────────────────
section("SDK quick-start", "🐍")
slug = active.get("slug", "my-game") if active else "my-game"
display_key = active.get("api_key", API_KEY) if active else API_KEY
st.code(
    f"""import gamepulse

gamepulse.init(
    api_key="{display_key}",
    project="{slug}",
    player_id="user_123",
    api_url="{API_URL}",
)

with gamepulse.session():
    gamepulse.progression.start(level=1)
    gamepulse.economy.spend(currency="gold", amount=10, item="potion")
    gamepulse.progression.complete(level=1, stars=3)
""",
    language="python",
)

# ── Simulator ─────────────────────────────────────────────────────────────
section("Run the simulator", "🤖")
st.code(
    f"GAMEPULSE_API_URL={API_URL} "
    f"GAMEPULSE_API_KEY={display_key} "
    f"GAMEPULSE_PROJECT_SLUG={slug} "
    "python -m simulator --players 25 --duration 60",
    language="bash",
)

# ── Env inspector ──────────────────────────────────────────────────────────
with st.expander("Environment variables (GAMEPULSE_*)"):
    env = {k: v for k, v in os.environ.items() if k.startswith("GAMEPULSE_")}
    if env:
        st.json(env)
    else:
        st.caption("No GAMEPULSE_* environment variables found.")

section("API docs", "📖")
st.markdown(f"Interactive API docs: [{API_URL}/docs]({API_URL}/docs)")
