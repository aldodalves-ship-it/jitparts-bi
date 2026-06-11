"""Tratamento e modelagem dos dados operacionais em camada analitica."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def generate_demo_sales(seed: int = 42, months: int = 18) -> pd.DataFrame:
    """Gera uma base demonstrativa realista para desenvolvimento do BI."""

    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(months=months)
    dates = pd.date_range(start=start, end=end, freq="D")

    brands = ["Bosch", "Mahle", "Cofap", "Nakata", "Mann", "Axios"]
    categories = ["Freios", "Suspensao", "Motor", "Filtros", "Eletrica", "Transmissao"]
    rows: list[dict[str, Any]] = []

    for current_date in dates:
        weekday_factor = 0.72 if current_date.weekday() >= 5 else 1.0
        month_factor = 1 + ((current_date.month % 6) * 0.035)
        daily_orders = int(rng.poisson(24 * weekday_factor * month_factor) + 6)

        for order_idx in range(daily_orders):
            brand = rng.choice(brands, p=[0.22, 0.18, 0.17, 0.16, 0.15, 0.12])
            category = rng.choice(categories)
            quantity = int(rng.integers(1, 4))
            unit_price = float(rng.lognormal(mean=5.1, sigma=0.45))
            gross_revenue = unit_price * quantity
            fees = gross_revenue * float(rng.uniform(0.105, 0.165))
            ads_cost = gross_revenue * float(rng.uniform(0.015, 0.09))
            shipping_cost = float(rng.uniform(6, 28))
            cmv_rate = float(rng.uniform(0.48, 0.74))
            cmv = gross_revenue * cmv_rate
            net_revenue = gross_revenue - fees - shipping_cost
            gross_profit = net_revenue - cmv
            operating_expense = gross_revenue * float(rng.uniform(0.035, 0.075))
            ebitda = gross_profit - ads_cost - operating_expense
            taxes = max(gross_revenue * 0.025, 0)
            net_profit = ebitda - taxes
            logistic_type = rng.choice(["FULL", "Flex", "ME2"], p=[0.48, 0.32, 0.20])
            status = rng.choice(["paid", "cancelled", "returned"], p=[0.925, 0.045, 0.03])
            cancellation_flag = status == "cancelled"
            return_flag = status == "returned"

            rows.append(
                {
                    "order_id": f"DEMO-{current_date:%Y%m%d}-{order_idx:04d}",
                    "date_created": current_date + pd.Timedelta(minutes=int(rng.integers(0, 1440))),
                    "mlb": f"MLB{int(rng.integers(1000000000, 9999999999))}",
                    "sku": f"JP-{brand[:3].upper()}-{int(rng.integers(1000, 9999))}",
                    "brand": brand,
                    "category": category,
                    "logistic_type": logistic_type,
                    "fulfillment_type": "FULL" if logistic_type == "FULL" else "Seller",
                    "quantity": quantity,
                    "gross_revenue": gross_revenue,
                    "net_revenue": net_revenue,
                    "cmv": cmv,
                    "fees": fees,
                    "ads_cost": ads_cost,
                    "shipping_cost": shipping_cost,
                    "gross_profit": gross_profit,
                    "ebitda": ebitda,
                    "net_profit": net_profit,
                    "status": status,
                    "cancellation_flag": cancellation_flag,
                    "return_flag": return_flag,
                    "stock": int(rng.integers(0, 90)),
                    "source": "demo",
                }
            )

    df = pd.DataFrame(rows)
    return normalize_sales_dataframe(df)


def normalize_orders_from_ml(orders: list[dict[str, Any]]) -> pd.DataFrame:
    """Normaliza pedidos Mercado Livre para o modelo fact_sales.

    Custos, publicidade e margem sao enriquecidos depois pela Seconds e por
    endpoints financeiros especificos.
    """

    rows: list[dict[str, Any]] = []
    for order in orders:
        order_id = str(order.get("id", ""))
        date_created = order.get("date_created") or order.get("date_closed")
        status = order.get("status", "")
        paid_amount = float(order.get("paid_amount") or order.get("total_amount") or 0)
        fees = sum(float(payment.get("marketplace_fee") or 0) for payment in order.get("payments", []))
        shipping = order.get("shipping") or {}
        logistic_type = shipping.get("logistic_type") or shipping.get("mode") or "N/D"

        for item in order.get("order_items", []):
            item_data = item.get("item", {})
            quantity = int(item.get("quantity") or 1)
            unit_price = float(item.get("unit_price") or 0)
            gross_revenue = unit_price * quantity
            allocated_fees = fees * (gross_revenue / paid_amount) if paid_amount else 0
            net_revenue = gross_revenue - allocated_fees

            rows.append(
                {
                    "order_id": order_id,
                    "date_created": date_created,
                    "mlb": item_data.get("id"),
                    "sku": item_data.get("seller_sku") or item_data.get("seller_custom_field"),
                    "brand": _extract_attribute(item_data, "BRAND") or "N/D",
                    "category": item_data.get("category_id") or "N/D",
                    "logistic_type": logistic_type,
                    "fulfillment_type": "FULL" if str(logistic_type).lower() == "fulfillment" else "Seller",
                    "quantity": quantity,
                    "gross_revenue": gross_revenue,
                    "net_revenue": net_revenue,
                    "cmv": 0.0,
                    "fees": allocated_fees,
                    "ads_cost": 0.0,
                    "shipping_cost": 0.0,
                    "gross_profit": net_revenue,
                    "ebitda": net_revenue,
                    "net_profit": net_revenue,
                    "status": status,
                    "cancellation_flag": status == "cancelled",
                    "return_flag": "return" in str(status).lower(),
                    "stock": 0,
                    "source": "mercado_livre",
                }
            )

    return normalize_sales_dataframe(pd.DataFrame(rows))


def _extract_attribute(item_data: dict[str, Any], attribute_id: str) -> str | None:
    for attribute in item_data.get("attributes", []) or []:
        if attribute.get("id") == attribute_id:
            return attribute.get("value_name")
    return None


def normalize_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza tipos, datas e colunas derivadas."""

    if df.empty:
        return df

    df = df.copy()
    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    df = df.dropna(subset=["date_created"])
    df["date"] = df["date_created"].dt.date
    df["month"] = df["date_created"].dt.to_period("M").astype(str)
    df["year"] = df["date_created"].dt.year
    df["week"] = df["date_created"].dt.isocalendar().week.astype(int)
    df["is_full"] = df["logistic_type"].astype(str).str.upper().str.contains("FULL|FULFILLMENT", regex=True)
    df["is_flex"] = df["logistic_type"].astype(str).str.upper().str.contains("FLEX", regex=True)
    df["gross_margin"] = np.where(df["net_revenue"] != 0, df["gross_profit"] / df["net_revenue"], 0)
    df["ebitda_margin"] = np.where(df["net_revenue"] != 0, df["ebitda"] / df["net_revenue"], 0)
    df["net_margin"] = np.where(df["net_revenue"] != 0, df["net_profit"] / df["net_revenue"], 0)
    df["negative_margin"] = df["net_profit"] < 0
    return df


def apply_filters(
    df: pd.DataFrame,
    period: tuple[date, date] | None = None,
    brands: list[str] | None = None,
    categories: list[str] | None = None,
    only_full: bool = False,
    only_flex: bool = False,
    only_negative_margin: bool = False,
    sku_query: str = "",
    mlb_query: str = "",
) -> pd.DataFrame:
    """Aplica filtros globais do dashboard."""

    filtered = df.copy()
    if filtered.empty:
        return filtered

    if period:
        start, end = period
        filtered = filtered[
            (filtered["date_created"].dt.date >= start)
            & (filtered["date_created"].dt.date <= end)
        ]
    if brands:
        filtered = filtered[filtered["brand"].isin(brands)]
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if only_full:
        filtered = filtered[filtered["is_full"]]
    if only_flex:
        filtered = filtered[filtered["is_flex"]]
    if only_negative_margin:
        filtered = filtered[filtered["negative_margin"]]
    if sku_query:
        filtered = filtered[filtered["sku"].astype(str).str.contains(sku_query, case=False, na=False)]
    if mlb_query:
        filtered = filtered[filtered["mlb"].astype(str).str.contains(mlb_query, case=False, na=False)]
    return filtered
