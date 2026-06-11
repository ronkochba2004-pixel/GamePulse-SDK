from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from lib.theme import PALETTE, chart_defaults


def _apply(fig: go.Figure) -> go.Figure:
    fig.update_layout(**chart_defaults())
    return fig


def line(df: pd.DataFrame, x: str, y: str, title: str | None = None,
         color: str | None = None) -> go.Figure:
    fig = px.line(
        df, x=x, y=y, title=title, markers=True,
        color_discrete_sequence=[color or PALETTE[0]],
    )
    return _apply(fig)


def bar(df: pd.DataFrame, x: str, y: str, title: str | None = None,
        color: str | None = None) -> go.Figure:
    fig = px.bar(
        df, x=x, y=y, title=title,
        color_discrete_sequence=[color or PALETTE[0]],
    )
    return _apply(fig)


def multi_bar(df: pd.DataFrame, x: str, ys: list[str],
              title: str | None = None) -> go.Figure:
    fig = go.Figure()
    for i, y in enumerate(ys):
        fig.add_trace(go.Bar(
            name=y, x=df[x], y=df[y],
            marker_color=PALETTE[i % len(PALETTE)],
        ))
    fig.update_layout(barmode="group", title=title, **chart_defaults())
    return fig


def funnel(df: pd.DataFrame, x: str, y: str, title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=df[y].astype(str), x=df[x],
        marker={"color": PALETTE[:len(df)]},
    ))
    if title:
        fig.update_layout(title=title)
    fig.update_layout(**chart_defaults())
    return fig


def pie(df: pd.DataFrame, names: str, values: str,
        title: str | None = None, hole: float = 0.45) -> go.Figure:
    fig = px.pie(
        df, names=names, values=values, title=title, hole=hole,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _apply(fig)


def area(df: pd.DataFrame, x: str, y: str, title: str | None = None) -> go.Figure:
    fig = px.area(
        df, x=x, y=y, title=title,
        color_discrete_sequence=[PALETTE[0]],
    )
    return _apply(fig)


def heatmap(z: list[list[float]], x: list, y: list, title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=z, x=[str(v) for v in x], y=[str(v) for v in y],
        colorscale="Blues",
    ))
    if title:
        fig.update_layout(title=title)
    fig.update_layout(**chart_defaults())
    return fig
