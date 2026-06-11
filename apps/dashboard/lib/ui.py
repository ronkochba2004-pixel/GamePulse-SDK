"""Reusable Streamlit UI components for GamePulse dashboard."""
from __future__ import annotations

import streamlit as st

from lib.theme import DANGER, PRIMARY


def metric_row(metrics: list[tuple[str, str | int | float, str | None]]) -> None:
    """Render a row of metric cards.

    Each tuple: (label, value, delta_or_none).
    """
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics, strict=True):
        with col:
            st.metric(label, value, delta=delta)


def kpi_card(label: str, value: str | int | float,
             delta: str | None = None, color: str = PRIMARY) -> None:
    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.05);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 8px;
        ">
            <div style="font-size:0.78rem;color:#94a3b8;text-transform:uppercase;
                        letter-spacing:.08em;">{label}</div>
            <div style="font-size:1.9rem;font-weight:700;color:#f8fafc;
                        line-height:1.1;">{value}</div>
            {"<div style='font-size:0.82rem;color:#64748b;margin-top:4px;'>"
             + str(delta) + "</div>" if delta else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, icon: str = "") -> None:
    st.markdown(
        f"<h3 style='margin-top:1.5rem;margin-bottom:.5rem;'>{icon} {title}</h3>",
        unsafe_allow_html=True,
    )


def empty_state(message: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div style="text-align:center;padding:48px 0;color:#64748b;">
            <div style="font-size:2.5rem;">🎮</div>
            <div style="font-size:1rem;margin-top:12px;color:#94a3b8;">{message}</div>
            {"<div style='font-size:0.85rem;margin-top:6px;'>" + hint + "</div>" if hint else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def error_state(message: str) -> None:
    st.markdown(
        f"""
        <div style="background:rgba(244,63,94,.1);border:1px solid {DANGER};
                    border-radius:8px;padding:16px;color:{DANGER};">
            ⚠️ {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = PRIMARY) -> str:
    """Return an HTML badge string."""
    return (
        f"<span style='background:{color}22;color:{color};padding:2px 8px;"
        f"border-radius:12px;font-size:0.78rem;'>{text}</span>"
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<h1 style='margin-bottom:.25rem;'>{title}</h1>"
        + (f"<p style='color:#64748b;margin-top:0;'>{subtitle}</p>" if subtitle else ""),
        unsafe_allow_html=True,
    )
    st.divider()


def api_error(e: Exception) -> None:
    error_state(f"API error — {e}. Is the API running? Check `GAMEPULSE_DASHBOARD_API_URL`.")
    st.stop()


def with_spinner(label: str = "Loading…"):
    return st.spinner(label)


def download_csv(df, filename: str, label: str = "⬇ Download CSV", key: str | None = None) -> None:
    """Render a download button that exports a DataFrame as CSV."""
    if df is None or getattr(df, "empty", True):
        return
    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )
