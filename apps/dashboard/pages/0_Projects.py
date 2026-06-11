import httpx
import streamlit as st
from lib.api_client import API_URL, authed_get, authed_post
from lib.ui import empty_state, page_header, section

page_header("📁 My Projects", "Create and manage your game projects")


def load_projects() -> list:
    try:
        return authed_get("/v1/manage/projects")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            st.error(
                f"**Authentication error:** {e}\n\n"
                "Your session may have expired. Log out and sign in again."
            )
            if st.button("Log out", key="_projects_relogin_btn"):
                st.session_state.clear()
                st.rerun()
        else:
            st.warning(f"Could not load projects: {e}")
        return []
    except Exception as e:
        st.warning(f"Could not load projects: {e}")
        return []


projects = load_projects()
active = st.session_state.get("active_project", {})

# ── Project list ───────────────────────────────────────────────────────────
section("Your projects", "📋")

if not projects:
    empty_state("No projects yet", "Create your first project below")
else:
    for proj in projects:
        is_active = active.get("id") == proj.get("id")
        c1, c2, c3 = st.columns([4, 1, 1])
        label = f"**{proj['name']}** · `{proj['slug']}`"
        if is_active:
            label += "  ✅ active"
        c1.markdown(label)
        if c2.button("Select", key=f"sel_{proj['id']}", disabled=is_active):
            st.session_state["active_project"] = proj
            st.rerun()
        if c3.button("🔑 Rotate", key=f"rot_{proj['id']}"):
            try:
                result = authed_post(f"/v1/manage/projects/{proj['id']}/rotate-key")
                new_key = result["api_key"]
                st.session_state["_rotated_key"] = new_key
                if is_active:
                    st.session_state["active_project"] = {**proj, "api_key": new_key}
                st.rerun()
            except Exception as e:
                st.error(f"Key rotation failed: {e}")

rotated = st.session_state.pop("_rotated_key", None)
if rotated:
    st.warning("**New API key — save this now, it won't be shown again after you navigate away:**", icon="🔑")
    st.code(rotated)

# ── Active project config ──────────────────────────────────────────────────
active_proj = st.session_state.get("active_project")
if active_proj:
    st.divider()
    section("Active project config", "⚙️")
    c1, c2 = st.columns(2)
    c1.metric("Name", active_proj.get("name", "—"))
    c2.metric("Slug", active_proj.get("slug", "—"))
    api_key = active_proj.get("api_key", "")
    st.text_input("API Key", value=api_key, disabled=True,
                  help="Use this key in your SDK calls and simulator")
    st.caption("⚠️ Keep your API key secret. Use **Rotate** to invalidate the current key and generate a new one.")

    st.divider()
    section("SDK quick-start", "🐍")
    slug = active_proj.get("slug", "my-game")
    st.code(
        f"""import gamepulse

gamepulse.init(
    api_key="{api_key}",
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

    section("Run the simulator for this project", "🤖")
    st.code(
        f"GAMEPULSE_API_URL={API_URL} "
        f"GAMEPULSE_API_KEY={api_key} "
        f"GAMEPULSE_PROJECT_SLUG={slug} "
        "python -m simulator --players 25 --duration 60",
        language="bash",
    )

st.divider()

# ── Create new project ─────────────────────────────────────────────────────
section("Create a new project", "➕")
with st.form("create_project_form"):
    name = st.text_input("Project name", placeholder="My Awesome Game")
    slug = st.text_input(
        "Slug",
        placeholder="my-awesome-game",
        help="Lowercase letters, numbers, and hyphens. Must be globally unique.",
    )
    submitted = st.form_submit_button("Create project", use_container_width=True)

if submitted:
    if not name or not slug:
        st.error("Name and slug are required.")
    else:
        try:
            proj = authed_post("/v1/manage/projects", json={"name": name, "slug": slug})
            st.success(f"Project **{proj['name']}** created and set as active!")
            st.info(
                f"API key: `{proj['api_key']}`\n\n"
                "**Save this key.** It's shown in full here and in the config panel above "
                "as long as this project is selected."
            )
            st.session_state["active_project"] = proj
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create project: {e}")
