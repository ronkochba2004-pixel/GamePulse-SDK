from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_URL = os.environ.get("GAMEPULSE_DASHBOARD_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("GAMEPULSE_API_KEY", "demo-key-please-rotate")


def _active_api_key() -> str:
    """Return the active project API key from session state, or the env default."""
    try:
        proj = st.session_state.get("active_project")
        if proj and proj.get("api_key"):
            return proj["api_key"]
    except Exception:
        pass
    return API_KEY


def get(path: str, **params: Any) -> Any:
    """GET the given path with the active project API key, raising on HTTP error."""
    params = {k: v for k, v in params.items() if v is not None}
    with httpx.Client(
        base_url=API_URL,
        headers={"X-GamePulse-Key": _active_api_key()},
        timeout=20.0,
    ) as c:
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()


@st.cache_data(ttl=60, show_spinner=False)
def get_cached(path: str, **params: Any) -> Any:
    """Cached variant — use for heavy analytical queries (funnel, retention, economy)."""
    return get(path, **params)


def _raise_for_status(r: httpx.Response) -> None:
    """Raise HTTPStatusError with the API response body included in the message."""
    if r.is_success:
        return
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        detail = r.text
    raise httpx.HTTPStatusError(
        f"HTTP {r.status_code}: {detail}",
        request=r.request,
        response=r,
    )


def authed_get(path: str, *, timeout: float = 20.0, **params: Any) -> Any:
    """GET with JWT bearer auth for management endpoints."""
    params = {k: v for k, v in params.items() if v is not None}
    token = st.session_state.get("auth_token", "")
    with httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    ) as c:
        r = c.get(path, params=params)
        _raise_for_status(r)
        return r.json()


def authed_post(path: str, json: dict[str, Any] | None = None, *, timeout: float = 20.0) -> Any:
    """POST with JWT bearer auth for management endpoints."""
    token = st.session_state.get("auth_token", "")
    with httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    ) as c:
        r = c.post(path, json=json)
        _raise_for_status(r)
        return r.json()


def is_healthy() -> bool:
    try:
        r = httpx.get(f"{API_URL}/healthz", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False
