from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


# Load the project-root .env with an absolute path so Streamlit's working
# directory doesn't affect resolution. auth.py lives at
# apps/dashboard/lib/auth.py → four levels up is the project root.
def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass  # python-dotenv not available; rely on shell env


_load_env()


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "")


def _supabase_anon_key() -> str:
    return os.environ.get("SUPABASE_ANON_KEY", "")


def _get_supabase():
    from supabase import create_client  # noqa: PLC0415
    return create_client(_supabase_url(), _supabase_anon_key())


def require_login() -> None:
    """Gate every page behind auth. Shows login/signup form and calls st.stop() if not logged in."""
    if st.session_state.get("auth_token"):
        _sidebar_user()
        return
    _login_wall()
    st.stop()


def _login_wall() -> None:
    st.title("🎮 GamePulse — Sign In")
    st.caption("Create a free account or sign in to view your game analytics.")

    if not _supabase_url() or not _supabase_anon_key():
        st.error(
            "Supabase credentials not configured. "
            "Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in your `.env` file."
        )
        # Debug hint — shows the resolved path so the user knows where to look.
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        st.caption(f"Looking for `.env` at: `{env_path}`  (exists: {env_path.exists()})")
        return

    tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

    with tab_in:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            login_btn = st.form_submit_button("Sign In", use_container_width=True)
        if login_btn:
            _do_login(email, password)

    with tab_up:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_pw = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
            signup_btn = st.form_submit_button("Create Account", use_container_width=True)
        if signup_btn:
            _do_signup(new_email, new_pw)


def _do_login(email: str, password: str) -> None:
    if not email or not password:
        st.error("Enter your email and password.")
        return
    try:
        sb = _get_supabase()
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["auth_token"] = res.session.access_token
        st.session_state["user_email"] = res.user.email
        st.session_state["user_id"] = str(res.user.id)
        st.rerun()
    except Exception as e:
        st.error(f"Sign in failed: {e}")


def _do_signup(email: str, password: str) -> None:
    if not email or not password:
        st.error("Enter your email and password.")
        return
    try:
        sb = _get_supabase()
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Account created! Check your email to confirm, then sign in.")
    except Exception as e:
        st.error(f"Sign up failed: {e}")


def require_project() -> None:
    """Halt analytics pages when no project is selected. Call after require_login()."""
    if st.session_state.get("active_project"):
        return
    st.info(
        "**No project selected.** "
        "Use the **Projects** page in the sidebar to create or select a project.",
        icon="📁",
    )
    st.stop()


def _sidebar_user() -> None:
    with st.sidebar:
        st.divider()
        email = st.session_state.get("user_email", "")
        proj = st.session_state.get("active_project")
        st.caption(f"👤 {email}")
        if proj:
            st.caption(f"🎮 {proj['name']} (`{proj['slug']}`)")
        if st.button("Logout", key="_auth_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()
