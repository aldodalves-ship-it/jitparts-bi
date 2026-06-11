"""Graficos Plotly com identidade visual executiva."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLORWAY = ["#00A884", "#2563EB", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2", "#111827"]


def apply_layout(fig: go.Figure, title: str | None = None, height: int = 360) -> go.Figure:
    """Aplica layout corporativo padrao aos graficos."""

    fig.update_layout(
        title=title,
        height=height,
        colorway=COLORWAY,
        margin=dict(l=18, r=18, t=52 if title else 22, b=18),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, Segoe UI, Arial", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


def revenue_evolution(monthly_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if monthly_df.empty:
        return apply_layout(fig, "Evolucao temporal")

    fig.add_trace(
        go.Bar(
            x=monthly_df["month"],
            y=monthly_df["gross_revenue"],
            name="Faturamento",
            marker_color="#2563EB",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly_df["month"],
            y=monthly_df["net_profit"],
            name="Lucro liquido",
            mode="lines+markers",
            line=dict(color="#00A884", width=3),
        )
    )
    return apply_layout(fig, "Faturamento x lucro liquido", 390)


def monthly_growth(monthly_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        monthly_df,
        x="month",
        y="growth",
        color="growth",
        color_continuous_scale=["#DC2626", "#F59E0B", "#00A884"],
    )
    fig.update_traces(hovertemplate="%{x}<br>Crescimento: %{y:.1f}%<extra></extra>")
    fig.update_layout(coloraxis_showscale=False)
    return apply_layout(fig, "Crescimento mensal", 330)


def margin_combo(monthly_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if monthly_df.empty:
        return apply_layout(fig, "Margem bruta")

    fig.add_trace(
        go.Scatter(
            x=monthly_df["month"],
            y=monthly_df["gross_margin"],
            name="Margem bruta",
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#00A884", width=3),
        )
    )
    fig.add_hline(y=20, line_dash="dash", line_color="rgba(128,128,128,0.65)")
    return apply_layout(fig, "Margem bruta mensal", 330)


def dimension_bar(df: pd.DataFrame, dimension: str, metric: str, title: str) -> go.Figure:
    if df.empty:
        return apply_layout(go.Figure(), title)
    fig = px.bar(
        df.sort_values(metric),
        x=metric,
        y=dimension,
        orientation="h",
        text_auto=".2s",
        color=metric,
        color_continuous_scale=["#CBD5E1", "#2563EB", "#00A884"],
    )
    fig.update_layout(coloraxis_showscale=False)
    return apply_layout(fig, title, 390)


def heatmap_growth(df: pd.DataFrame, dimension: str) -> go.Figure:
    if df.empty:
        return apply_layout(go.Figure(), "Heatmap de crescimento")

    pivot_source = (
        df.groupby([dimension, "month"], as_index=False)["gross_revenue"]
        .sum()
        .sort_values([dimension, "month"])
    )
    pivot_source["growth"] = pivot_source.groupby(dimension)["gross_revenue"].pct_change().fillna(0) * 100
    pivot = pivot_source.pivot(index=dimension, columns="month", values="growth").fillna(0)

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=["#DC2626", "#F8FAFC", "#00A884"],
        labels=dict(color="Crescimento %"),
    )
    return apply_layout(fig, f"Heatmap de crescimento por {dimension}", 390)


def ads_profit_scatter(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return apply_layout(go.Figure(), "Publicidade x lucro")
    grouped = (
        df.groupby("brand", as_index=False)
        .agg(ads_cost=("ads_cost", "sum"), net_profit=("net_profit", "sum"), gross_revenue=("gross_revenue", "sum"))
    )
    fig = px.scatter(
        grouped,
        x="ads_cost",
        y="net_profit",
        size="gross_revenue",
        color="brand",
        hover_name="brand",
    )
    return apply_layout(fig, "Publicidade x lucro por marca", 390)


def stock_critical_bar(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return apply_layout(go.Figure(), "Produtos criticos")
    critical = (
        df.groupby(["sku", "mlb"], as_index=False)
        .agg(stock=("stock", "min"), gross_revenue=("gross_revenue", "sum"))
        .sort_values(["stock", "gross_revenue"], ascending=[True, False])
        .head(15)
    )
    fig = px.bar(critical, x="stock", y="sku", orientation="h", color="gross_revenue")
    return apply_layout(fig, "Produtos criticos por estoque", 420)


def operational_status(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return apply_layout(go.Figure(), "Status operacional")
    status = df.groupby("status", as_index=False).agg(orders=("order_id", "nunique"))
    fig = px.pie(status, names="status", values="orders", hole=0.58)
    return apply_layout(fig, "Pedidos por status", 330)
