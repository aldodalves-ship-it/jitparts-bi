"""Audita divergencias entre a base Seconds e o dashboard.

Periodo auditado:
    2026-05-04 a 2026-05-08
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


SECONDS_PATH = Path("data/base_seconds_principal.csv")
DASHBOARD_PATH = Path("data/dashboard_base_final.csv")
PERIOD_START = date(2026, 5, 4)
PERIOD_END = date(2026, 5, 8)

EXPECTED = {
    "faturamento": 106713.71,
    "lucro_liquido": 2316.41,
    "cmv": 55822.92,
    "frete": 10914.95,
    "imposto": 19962.28,
}

SECONDS_TOTAL_COLUMNS = {
    "faturamento": "faturamento_seconds",
    "preco_venda": "preco_venda_seconds",
    "cmv": "cmv_seconds",
    "frete": "frete_seconds",
    "imposto": "imposto_seconds",
    "lucro_liquido": "lucro_liquido_seconds",
}

DASHBOARD_TOTAL_COLUMNS = {
    "faturamento_seconds": "faturamento_seconds",
    "receita": "receita",
    "faturamento": "faturamento",
    "cmv": "CMV total",
    "frete": "custo_frete_final",
    "imposto": "imposto",
    "lucro_liquido": "lucro_liquido_estimado",
    "margem": "margem_liquida_estimada",
}


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_csv(path)


def sum_columns(df: pd.DataFrame, columns: dict[str, str]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for label, column in columns.items():
        totals[label] = float(pd.to_numeric(df.get(column, 0), errors="coerce").fillna(0).sum())
    return totals


def print_totals(title: str, totals: dict[str, float]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    for label, value in totals.items():
        print(f"{label}: {money(value)}")


def print_expected_diff(title: str, totals: dict[str, float]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    mapping = {
        "faturamento": "faturamento",
        "receita": "faturamento",
        "faturamento_seconds": "faturamento",
        "lucro_liquido": "lucro_liquido",
        "cmv": "cmv",
        "frete": "frete",
        "imposto": "imposto",
    }
    for label, expected_key in mapping.items():
        if label not in totals:
            continue
        expected = EXPECTED[expected_key]
        actual = totals[label]
        print(
            f"{label}: atual={money(actual)} esperado={money(expected)} "
            f"dif={money(actual - expected)}"
        )


def dashboard_period_by_date(df: pd.DataFrame) -> pd.DataFrame:
    date_ref = pd.to_datetime(df["date_created"], errors="coerce", utc=True).dt.tz_convert(
        "America/Sao_Paulo"
    ).dt.date
    return df[(date_ref >= PERIOD_START) & (date_ref <= PERIOD_END)].copy()


def dashboard_period_by_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    starts = pd.to_datetime(df.get("seconds_period_start"), errors="coerce").dt.date
    ends = pd.to_datetime(df.get("seconds_period_end"), errors="coerce").dt.date
    source = df.get("financial_source", pd.Series("", index=df.index)).astype(str)
    snapshot_mask = (
        source.eq("seconds_snapshot")
        & starts.notna()
        & ends.notna()
        & (PERIOD_START >= starts)
        & (PERIOD_END <= ends)
    )
    date_filtered = dashboard_period_by_date(df)
    return pd.concat([df[snapshot_mask], date_filtered[~date_filtered.index.isin(df[snapshot_mask].index)]])


def app_totals() -> dict[str, float]:
    import app

    df = app.load_data(str(DASHBOARD_PATH))
    filtered, warning = app.apply_seconds_snapshot_period_guard(
        dashboard_period_by_snapshot(df),
        (PERIOD_START, PERIOD_END),
    )
    if warning:
        print(f"\nAVISO APP: {warning}")
    return sum_columns(filtered, DASHBOARD_TOTAL_COLUMNS)


def top_divergences(seconds_df: pd.DataFrame, dashboard_df: pd.DataFrame) -> pd.DataFrame:
    seconds = seconds_df[
        [
            "item_id",
            "faturamento_seconds",
            "cmv_seconds",
            "frete_seconds",
            "imposto_seconds",
            "lucro_liquido_seconds",
        ]
    ].copy()
    dashboard = dashboard_df[
        [
            "item_id",
            "receita",
            "CMV total",
            "custo_frete_final",
            "imposto",
            "lucro_liquido_estimado",
        ]
    ].copy()

    merged = seconds.merge(dashboard, on="item_id", how="outer", suffixes=("_seconds", "_dashboard"))
    comparisons = [
        ("faturamento", "faturamento_seconds", "receita"),
        ("cmv", "cmv_seconds", "CMV total"),
        ("frete", "frete_seconds", "custo_frete_final"),
        ("imposto", "imposto_seconds", "imposto"),
        ("lucro_liquido", "lucro_liquido_seconds", "lucro_liquido_estimado"),
    ]
    for _, left, right in comparisons:
        merged[left] = pd.to_numeric(merged[left], errors="coerce").fillna(0)
        merged[right] = pd.to_numeric(merged[right], errors="coerce").fillna(0)

    for label, left, right in comparisons:
        merged[f"dif_{label}"] = merged[right] - merged[left]

    diff_columns = [f"dif_{label}" for label, _, _ in comparisons]
    merged["divergencia_abs_total"] = merged[diff_columns].abs().sum(axis=1)
    return merged.sort_values("divergencia_abs_total", ascending=False).head(20)


def main() -> None:
    seconds_df = load_csv(SECONDS_PATH)
    dashboard_df = load_csv(DASHBOARD_PATH)

    seconds_totals = sum_columns(seconds_df, SECONDS_TOTAL_COLUMNS)
    dashboard_totals = sum_columns(dashboard_df, DASHBOARD_TOTAL_COLUMNS)
    dashboard_date_totals = sum_columns(dashboard_period_by_date(dashboard_df), DASHBOARD_TOTAL_COLUMNS)
    dashboard_snapshot_totals = sum_columns(dashboard_period_by_snapshot(dashboard_df), DASHBOARD_TOTAL_COLUMNS)
    calculated_app_totals = app_totals()

    print(f"Periodo auditado: {PERIOD_START:%d/%m/%Y} a {PERIOD_END:%d/%m/%Y}")
    print_totals("TOTAIS data/base_seconds_principal.csv", seconds_totals)
    print_expected_diff("DIFERENCAS BASE SECONDS x ESPERADO", seconds_totals)

    print_totals("TOTAIS data/dashboard_base_final.csv - base completa", dashboard_totals)
    print_totals("TOTAIS dashboard filtrado por date_created", dashboard_date_totals)
    print_expected_diff("DIFERENCAS DASHBOARD POR date_created x ESPERADO", dashboard_date_totals)

    print_totals("TOTAIS dashboard filtrado por snapshot Seconds", dashboard_snapshot_totals)
    print_expected_diff("DIFERENCAS DASHBOARD SNAPSHOT x ESPERADO", dashboard_snapshot_totals)

    print_totals("TOTAIS calculados pelo app", calculated_app_totals)
    print_expected_diff("DIFERENCAS APP x ESPERADO", calculated_app_totals)

    divergences = top_divergences(seconds_df, dashboard_df)
    print("\n" + "=" * 80)
    print("TOP 20 LINHAS COM MAIOR DIVERGENCIA BASE SECONDS x DASHBOARD")
    print("=" * 80)
    if divergences.empty:
        print("Sem divergencias por item_id.")
    else:
        print(divergences.to_string(index=False))


if __name__ == "__main__":
    main()
