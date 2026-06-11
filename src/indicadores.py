"""Calculo dos indicadores executivos e financeiros."""

from __future__ import annotations

import pandas as pd


def safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def calculate_executive_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Calcula KPIs centrais para diretoria."""

    if df.empty:
        return {
            "net_revenue": 0,
            "gross_revenue": 0,
            "ebitda": 0,
            "net_profit": 0,
            "gross_margin": 0,
            "ebitda_margin": 0,
            "net_margin": 0,
            "cmv": 0,
            "average_ticket": 0,
            "orders": 0,
            "products_sold": 0,
            "tacos": 0,
            "acos": 0,
            "roas": 0,
            "cash_generation": 0,
            "capital_tied": 0,
            "inventory_turnover": 0,
            "stock_coverage_days": 0,
            "roic_ecommerce": 0,
        }

    net_revenue = float(df["net_revenue"].sum())
    gross_revenue = float(df["gross_revenue"].sum())
    ebitda = float(df["ebitda"].sum())
    net_profit = float(df["net_profit"].sum())
    cmv = float(df["cmv"].sum())
    orders = int(df["order_id"].nunique())
    quantity = int(df["quantity"].sum())
    ads_cost = float(df["ads_cost"].sum())
    gross_profit = float(df["gross_profit"].sum())
    capital_tied = float((df["stock"].clip(lower=0) * (df["cmv"] / df["quantity"].clip(lower=1))).sum())

    daily_cmv = df.groupby("date")["cmv"].sum().mean()
    stock_coverage_days = safe_divide(capital_tied, daily_cmv)
    inventory_turnover = safe_divide(cmv, capital_tied)
    cash_generation = ebitda - max(capital_tied * 0.015, 0)
    roic_ecommerce = safe_divide(net_profit, capital_tied) * 100

    return {
        "net_revenue": net_revenue,
        "gross_revenue": gross_revenue,
        "ebitda": ebitda,
        "net_profit": net_profit,
        "gross_margin": safe_divide(gross_profit, net_revenue) * 100,
        "ebitda_margin": safe_divide(ebitda, net_revenue) * 100,
        "net_margin": safe_divide(net_profit, net_revenue) * 100,
        "cmv": cmv,
        "average_ticket": safe_divide(gross_revenue, orders),
        "orders": orders,
        "products_sold": quantity,
        "tacos": safe_divide(ads_cost, gross_revenue) * 100,
        "acos": safe_divide(ads_cost, gross_revenue) * 100,
        "roas": safe_divide(gross_revenue, ads_cost),
        "cash_generation": cash_generation,
        "capital_tied": capital_tied,
        "inventory_turnover": inventory_turnover,
        "stock_coverage_days": stock_coverage_days,
        "roic_ecommerce": roic_ecommerce,
    }


def calculate_period_delta(df: pd.DataFrame, metric: str) -> float:
    """Compara o ultimo mes fechado/parcial contra o mes anterior."""

    if df.empty or metric not in df.columns:
        return 0.0

    monthly = df.groupby("month", as_index=False)[metric].sum().sort_values("month")
    if len(monthly) < 2:
        return 0.0

    current = float(monthly.iloc[-1][metric])
    previous = float(monthly.iloc[-2][metric])
    return safe_divide(current - previous, previous) * 100


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    summary = (
        df.groupby("month", as_index=False)
        .agg(
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            ebitda=("ebitda", "sum"),
            net_profit=("net_profit", "sum"),
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum"),
            ads_cost=("ads_cost", "sum"),
            cmv=("cmv", "sum"),
        )
        .sort_values("month")
    )
    summary["growth"] = summary["gross_revenue"].pct_change().fillna(0) * 100
    summary["gross_margin"] = summary.apply(
        lambda row: safe_divide(row["net_revenue"] - row["cmv"], row["net_revenue"]) * 100,
        axis=1,
    )
    return summary


def dimension_ranking(df: pd.DataFrame, dimension: str, top_n: int = 12) -> pd.DataFrame:
    if df.empty or dimension not in df.columns:
        return pd.DataFrame()
    ranking = (
        df.groupby(dimension, as_index=False)
        .agg(
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
            net_profit=("net_profit", "sum"),
            ads_cost=("ads_cost", "sum"),
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum"),
            stock=("stock", "sum"),
        )
        .sort_values("gross_revenue", ascending=False)
        .head(top_n)
    )
    ranking["net_margin"] = ranking.apply(
        lambda row: safe_divide(row["net_profit"], row["net_revenue"]) * 100,
        axis=1,
    )
    ranking["tacos"] = ranking.apply(
        lambda row: safe_divide(row["ads_cost"], row["gross_revenue"]) * 100,
        axis=1,
    )
    return ranking


def negative_margin_products(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (
        df[df["negative_margin"]]
        .groupby(["mlb", "sku", "brand", "category"], as_index=False)
        .agg(net_revenue=("net_revenue", "sum"), net_profit=("net_profit", "sum"), quantity=("quantity", "sum"))
        .sort_values("net_profit")
        .head(top_n)
    )
