"""Shared visual constants and helpers for the GamePulse dashboard."""
from __future__ import annotations

# Plotly color palette (cohesive, dark-friendly)
PALETTE = [
    "#6366f1",  # indigo  – primary
    "#22d3ee",  # cyan    – secondary
    "#f59e0b",  # amber   – warning / economy
    "#10b981",  # emerald – success / progression
    "#f43f5e",  # rose    – error / crashes
    "#8b5cf6",  # violet  – social
    "#64748b",  # slate   – neutral
]

PRIMARY = PALETTE[0]
DANGER = PALETTE[4]
SUCCESS = PALETTE[3]
WARNING = PALETTE[2]

PLOTLY_TEMPLATE = "plotly_dark"

EMPTY_SVG = "🎮"  # fallback icon for empty states


def chart_defaults() -> dict:
    """Common Plotly layout kwargs."""
    return {
        "template": PLOTLY_TEMPLATE,
        "margin": dict(l=16, r=16, t=40, b=16),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, system-ui, sans-serif", "size": 12},
    }
