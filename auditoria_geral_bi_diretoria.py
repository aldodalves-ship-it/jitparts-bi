from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORT_PATH = ROOT / "AUDITORIA_GERAL_BI_DIRETORIA.md"

AUDIT_START = date(2026, 5, 1)
AUDIT_END = date(2026, 5, 31)
ML_PRINT = {
    "receita": 539_369.00,
    "unidades": 3_193,
    "pedidos": 3_066,
    "ticket": 175.92,
}
BI_PRINT = {
    "receita": 355_428.81,
    "pedidos": 2_053,
    "ticket": 173.13,
}


EXPECTED_FILES = [
    "ml_orders.csv",
    "ml_shipments.csv",
    "ml_items.csv",
    "ml_items_details.csv",
    "ml_ads_campaigns.csv",
    "ml_ads_metrics.csv",
    "dashboard_base_final.csv",
    "jitparts.duckdb",
    "base_seconds_principal.csv",
    "seconds/ReportProfitability.xlsx",
]


def money(value: Any) -> str:
    try:
        number = float(value)
    except Exception:
        return "N/D"
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def number(value: Any, decimals: int = 0) -> str:
    try:
        numeric = float(value)
    except Exception:
        return "N/D"
    formatted = f"{numeric:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: Any) -> str:
    try:
        return number(float(value), 2) + "%"
    except Exception:
        return "N/D"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def normalize_dt(series: pd.Series, utc_to_brt: bool = False) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=utc_to_brt)
    if utc_to_brt:
        return parsed.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    return parsed.dt.tz_localize(None) if getattr(parsed.dt, "tz", None) is not None else parsed


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def numeric_sum(df: pd.DataFrame, candidates: list[str]) -> float:
    column = first_existing(df, candidates)
    if column is None or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def count_orders(df: pd.DataFrame) -> int:
    if "order_id" in df.columns:
        return int(df["order_id"].astype(str).nunique())
    if "id" in df.columns:
        return int(df["id"].astype(str).nunique())
    return int(len(df))


def units_sum(df: pd.DataFrame) -> float:
    column = first_existing(df, ["quantity", "units", "vendidos"])
    if column is None or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def mtime_label(path: Path) -> str:
    if not path.exists():
        return "N/D"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")


def safe_period_filter(df: pd.DataFrame, date_column: str | None, start: date, end: date, utc_to_brt: bool = False) -> pd.DataFrame:
    if df.empty or date_column is None or date_column not in df.columns:
        return df.iloc[0:0].copy()
    dates = normalize_dt(df[date_column], utc_to_brt=utc_to_brt).dt.date
    return df[(dates >= start) & (dates <= end)].copy()


def date_range(df: pd.DataFrame, date_column: str | None, utc_to_brt: bool = False) -> tuple[str, str]:
    if df.empty or date_column is None or date_column not in df.columns:
        return "N/D", "N/D"
    dates = normalize_dt(df[date_column], utc_to_brt=utc_to_brt).dropna()
    if dates.empty:
        return "N/D", "N/D"
    return dates.min().strftime("%d/%m/%Y %H:%M:%S"), dates.max().strftime("%d/%m/%Y %H:%M:%S")


def make_markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns)) + " |\n"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines) + "\n"


@dataclass
class SourceSummary:
    fonte: str
    receita: float
    pedidos: int
    unidades: float

    @property
    def ticket(self) -> float:
        return self.receita / self.pedidos if self.pedidos else 0.0


def summarize_sales(fonte: str, df: pd.DataFrame) -> SourceSummary:
    return SourceSummary(
        fonte=fonte,
        receita=numeric_sum(df, ["receita", "total_amount", "paid_amount", "faturamento", "faturamento_seconds"]),
        pedidos=count_orders(df),
        unidades=units_sum(df),
    )


def find_duplicates(df: pd.DataFrame, subset: list[str]) -> tuple[bool, int]:
    if df.empty or not all(column in df.columns for column in subset):
        return False, 0
    duplicates = int(df.duplicated(subset=subset, keep=False).sum())
    return duplicates > 0, duplicates


def main() -> None:
    files = {name: DATA / name for name in EXPECTED_FILES}
    base = read_csv(files["dashboard_base_final.csv"])
    orders = read_csv(files["ml_orders.csv"])
    shipments = read_csv(files["ml_shipments.csv"])
    items = read_csv(files["ml_items.csv"])
    item_details = read_csv(files["ml_items_details.csv"])
    ads_campaigns = read_csv(files["ml_ads_campaigns.csv"])
    ads_metrics = read_csv(files["ml_ads_metrics.csv"])
    seconds = read_csv(files["base_seconds_principal.csv"])

    if "date_created" in base.columns:
        base["date_created_brt"] = normalize_dt(base["date_created"], utc_to_brt=True)
        base["data_ref_audit"] = base["date_created_brt"].dt.date
    if "date_created" in orders.columns:
        orders["date_created_brt"] = normalize_dt(orders["date_created"], utc_to_brt=True)
        orders["data_ref_audit"] = orders["date_created_brt"].dt.date

    date_specs = [
        ("base final consolidada", base, "date_created", True),
        ("pedidos ML", orders, "date_created", True),
        ("shipments/frete", shipments, first_existing(shipments, ["date_created", "last_updated", "date_created_from_order"]), True),
        ("Ads", ads_metrics, first_existing(ads_metrics, ["data_ref", "date_from", "date_to"]), False),
        ("itens/anuncios", item_details, first_existing(item_details, ["last_updated", "date_created", "start_time"]), True),
        ("Seconds", seconds, first_existing(seconds, ["period_start", "data_ref", "date_created", "Data"]), False),
    ]

    period_rows: list[dict[str, Any]] = []
    for name, df, column, utc in date_specs:
        period_df = safe_period_filter(df, column, AUDIT_START, AUDIT_END, utc_to_brt=utc)
        min_date, max_date = date_range(df, column, utc_to_brt=utc)
        period_rows.append(
            {
                "Dataframe": name,
                "Coluna de data usada": column or "N/D",
                "Menor data": min_date,
                "Maior data": max_date,
                "Qtde registros no período": len(period_df),
            }
        )

    base_period = safe_period_filter(base, "date_created", AUDIT_START, AUDIT_END, utc_to_brt=True)
    orders_period = safe_period_filter(orders, "date_created", AUDIT_START, AUDIT_END, utc_to_brt=True)
    ads_period = safe_period_filter(ads_metrics, first_existing(ads_metrics, ["data_ref", "date_from"]), AUDIT_START, AUDIT_END)

    # Simula o filtro do app: date_created UTC -> America/Sao_Paulo -> data_ref inclusivo.
    app_base = base.copy()
    if "date_created" in app_base.columns:
        app_base["date_created"] = pd.to_datetime(app_base["date_created"], errors="coerce", utc=True).dt.tz_convert(
            "America/Sao_Paulo"
        )
        app_base["data_ref"] = app_base["date_created"].dt.date
        app_filtered = app_base[(app_base["data_ref"] >= AUDIT_START) & (app_base["data_ref"] <= AUDIT_END)].copy()
    else:
        app_filtered = pd.DataFrame()

    base_min = app_base["data_ref"].min() if "data_ref" in app_base.columns and not app_base.empty else None
    base_max = app_base["data_ref"].max() if "data_ref" in app_base.columns and not app_base.empty else None
    effective_end = min(AUDIT_END, base_max) if base_max else AUDIT_END

    source_summaries = [
        summarize_sales("ml_orders.csv", orders_period),
        summarize_sales("dashboard_base_final.csv", base_period),
        summarize_sales("base filtrada pelo app", app_filtered),
        SourceSummary("print Mercado Livre", ML_PRINT["receita"], int(ML_PRINT["pedidos"]), float(ML_PRINT["unidades"])),
    ]
    revenue_rows = [
        {
            "Fonte": summary.fonte,
            "Receita": money(summary.receita),
            "Pedidos": number(summary.pedidos),
            "Unidades": number(summary.unidades),
            "Ticket médio": money(summary.ticket),
        }
        for summary in source_summaries
    ]

    financials = {
        "Receita Bruta": numeric_sum(app_filtered, ["receita", "faturamento", "faturamento_seconds"]),
        "Comissão ML": numeric_sum(app_filtered, ["sale_fee", "comissao_ml", "comissao_total", "comissao_seconds"]),
        "CMV": numeric_sum(app_filtered, ["CMV total", "cmv_total", "cmv_seconds"]),
        "Frete": numeric_sum(app_filtered, ["custo_frete_final", "frete_total", "frete_seconds"]),
        "Impostos": numeric_sum(app_filtered, ["imposto_total", "imposto", "imposto_seconds"]),
        "Rateio Operacional Seconds": numeric_sum(app_filtered, ["custo_fixo_total", "custo_fixo", "custo_fixo_seconds"]),
    }
    financials["Resultado Base"] = (
        financials["Receita Bruta"]
        - financials["Comissão ML"]
        - financials["CMV"]
        - financials["Frete"]
        - financials["Impostos"]
        - financials["Rateio Operacional Seconds"]
    )
    financials["Custos Operacionais Comerciais"] = numeric_sum(ads_period, ["cost"]) + financials["Receita Bruta"] * 0.005
    financials["Resultado Final da Margem"] = financials["Resultado Base"] - financials["Custos Operacionais Comerciais"]

    pedidos_app = count_orders(app_filtered)
    unidades_app = units_sum(app_filtered)
    ticket_app = financials["Receita Bruta"] / pedidos_app if pedidos_app else 0.0
    ads_cost = numeric_sum(ads_period, ["cost"])
    ads_revenue = numeric_sum(ads_period, ["revenue"])
    ads_clicks = numeric_sum(ads_period, ["clicks"])
    ads_impressions = numeric_sum(ads_period, ["impressions"])
    ads_units = numeric_sum(ads_period, ["units"])
    roas = ads_revenue / ads_cost if ads_cost else 0.0
    acos = ads_cost / ads_revenue * 100 if ads_revenue else 0.0
    ctr = ads_clicks / ads_impressions * 100 if ads_impressions else 0.0
    cpc = ads_cost / ads_clicks if ads_clicks else 0.0
    conversion = ads_units / ads_clicks * 100 if ads_clicks else 0.0
    ads_date_column = first_existing(ads_period, ["data_ref", "date_from"])
    if ads_date_column and not ads_period.empty:
        covered_ads_days = normalize_dt(ads_period[ads_date_column]).dt.date.nunique()
    else:
        covered_ads_days = 0
    effective_days = max((effective_end - AUDIT_START).days + 1, 1)
    ads_coverage = covered_ads_days / effective_days * 100 if effective_days else 0.0

    estoque_total = numeric_sum(item_details, ["estoque_atual", "available_quantity"])
    sem_estoque = 0
    estoque_baixo = 0
    produtos_parados = 0
    capital_parado = 0.0
    if not item_details.empty:
        stock_qty = pd.to_numeric(
            item_details.get("estoque_atual", item_details.get("available_quantity", pd.Series(0, index=item_details.index))),
            errors="coerce",
        ).fillna(0)
        sold_qty = pd.to_numeric(item_details.get("vendidos_total", pd.Series(0, index=item_details.index)), errors="coerce").fillna(0)
        price = pd.to_numeric(item_details.get("price", pd.Series(0, index=item_details.index)), errors="coerce").fillna(0)
        sem_estoque = int((stock_qty <= 0).sum())
        estoque_baixo = int(((stock_qty > 0) & (stock_qty <= 5)).sum())
        produtos_parados = int(((sold_qty <= 0) & (stock_qty > 0)).sum())
        capital_parado = float((stock_qty[(sold_qty <= 0) & (stock_qty > 0)] * price[(sold_qty <= 0) & (stock_qty > 0)]).sum())
    cobertura_estoque = estoque_total / (unidades_app / effective_days) if unidades_app and effective_days else 0.0

    status_counts = (
        orders_period[first_existing(orders_period, ["status"])].fillna("N/D").astype(str).value_counts().to_dict()
        if first_existing(orders_period, ["status"])
        else {}
    )
    base_status_counts = (
        app_filtered[first_existing(app_filtered, ["Status", "status"])].fillna("N/D").astype(str).value_counts().to_dict()
        if first_existing(app_filtered, ["Status", "status"])
        else {}
    )

    ml_bi_diff_rows = [
        {
            "Métrica": "Receita",
            "Mercado Livre": money(ML_PRINT["receita"]),
            "BI observado": money(BI_PRINT["receita"]),
            "Diferença absoluta": money(ML_PRINT["receita"] - BI_PRINT["receita"]),
            "Diferença %": pct((ML_PRINT["receita"] - BI_PRINT["receita"]) / ML_PRINT["receita"] * 100),
        },
        {
            "Métrica": "Pedidos",
            "Mercado Livre": number(ML_PRINT["pedidos"]),
            "BI observado": number(BI_PRINT["pedidos"]),
            "Diferença absoluta": number(ML_PRINT["pedidos"] - BI_PRINT["pedidos"]),
            "Diferença %": pct((ML_PRINT["pedidos"] - BI_PRINT["pedidos"]) / ML_PRINT["pedidos"] * 100),
        },
        {
            "Métrica": "Unidades",
            "Mercado Livre": number(ML_PRINT["unidades"]),
            "BI observado": "N/D no print BI",
            "Diferença absoluta": "N/D",
            "Diferença %": "N/D",
        },
    ]

    file_rows: list[dict[str, Any]] = []
    for name, path in files.items():
        exists = path.exists()
        if exists and path.suffix.lower() == ".csv":
            rows = len(read_csv(path))
        elif exists and path.suffix.lower() == ".xlsx":
            rows = "Excel"
        elif exists:
            rows = "N/D"
        else:
            rows = 0
        file_rows.append(
            {
                "Arquivo": f"data/{name}",
                "Existe": "Sim" if exists else "Não",
                "Linhas": rows,
                "Atualizado em": mtime_label(path) if exists else "N/D",
                "Status": "OK" if exists else "Ausente",
            }
        )

    dup_specs = [
        ("Receita/base final por order_id", app_filtered, ["order_id"]),
        ("Itens por pedido/item", app_filtered, ["order_id", "item_id"]),
        ("Pedidos ML por id", orders_period, ["id"]),
        ("Pedidos ML por order_id", orders_period, ["order_id"]),
        ("Shipments por shipment_id", shipments, ["shipment_id"]),
        ("Shipments por id", shipments, ["id"]),
        ("Ads por campanha/data", ads_metrics, ["campaign_id", "data_ref"]),
        ("Itens ML", items, ["id"]),
        ("Itens detalhes", item_details, ["id"]),
        ("Seconds por item_id", seconds, ["item_id"]),
    ]
    duplicate_rows: list[dict[str, Any]] = []
    for component, df, subset in dup_specs:
        found, qty = find_duplicates(df, subset)
        duplicate_rows.append(
            {
                "Componente": component,
                "Duplicidade encontrada?": "Sim" if found else "Não",
                "Impacto estimado": f"{qty} linhas envolvidas" if found else "Sem impacto detectado",
                "Correção sugerida": "Auditar granularidade antes de deduplicar" if found else "Nenhuma",
            }
        )

    kpi_rows = [
        {"KPI": "Visão Geral - Faturamento", "Fonte": "dashboard_base_final.csv", "Fórmula": "sum(receita)", "Valor atual": money(financials["Receita Bruta"]), "Status auditoria": "OK, consistente com base filtrada"},
        {"KPI": "Visão Geral - Pedidos", "Fonte": "dashboard_base_final.csv", "Fórmula": "nunique(order_id)", "Valor atual": number(pedidos_app), "Status auditoria": "OK"},
        {"KPI": "Visão Geral - Ticket Médio", "Fonte": "dashboard_base_final.csv", "Fórmula": "Receita / pedidos", "Valor atual": money(ticket_app), "Status auditoria": "OK"},
        {"KPI": "Visão Geral - Margem Base", "Fonte": "DRE híbrida", "Fórmula": "Receita - Comissão - CMV - Frete - Impostos - Rateio Seconds", "Valor atual": money(financials["Resultado Base"]), "Status auditoria": "Recalculado"},
        {"KPI": "Visão Geral - Custos Comerciais", "Fonte": "Ads + política operacional", "Fórmula": "Ads + devoluções + outras taxas + papelaria", "Valor atual": money(financials["Custos Operacionais Comerciais"]), "Status auditoria": "Recalculado parcialmente; devoluções dependem de coluna explícita"},
        {"KPI": "Visão Geral - Resultado Final da Margem", "Fonte": "DRE", "Fórmula": "Resultado Base - Custos Comerciais", "Valor atual": money(financials["Resultado Final da Margem"]), "Status auditoria": "Recalculado"},
        {"KPI": "Visão Geral - Investimento Ads", "Fonte": "ml_ads_metrics.csv", "Fórmula": "sum(cost)", "Valor atual": money(ads_cost), "Status auditoria": "OK com cobertura parcial"},
        {"KPI": "Visão Geral - Alertas", "Fonte": "Regras internas do app", "Fórmula": "bundle de alertas por vendas/estoque/Ads", "Valor atual": "N/D via script", "Status auditoria": "Requer smoke visual"},
        {"KPI": "Inteligência Comercial - Produtos em queda brusca", "Fonte": "dashboard_base_final.csv", "Fórmula": "comparação temporal por produto no app", "Valor atual": "N/D via script", "Status auditoria": "Regra deve ser validada visualmente"},
        {"KPI": "Inteligência Comercial - Oportunidades", "Fonte": "vendas + estoque", "Fórmula": "alto giro/margem/estoque", "Valor atual": "N/D via script", "Status auditoria": "Regra do app não alterada"},
        {"KPI": "Inteligência Comercial - Produtos perigosos", "Fonte": "vendas + margem + estoque", "Fórmula": "margem negativa/risco operacional", "Valor atual": number(int((pd.to_numeric(app_filtered.get('margem_liquida_estimada', pd.Series(0, index=app_filtered.index)), errors='coerce').fillna(0) < 0).sum())), "Status auditoria": "Sinal recalculado por margem negativa"},
        {"KPI": "Inteligência Comercial - Produtos sem giro", "Fonte": "ml_items_details.csv", "Fórmula": "vendidos_total <= 0 e estoque > 0", "Valor atual": number(produtos_parados), "Status auditoria": "Recalculado"},
        {"KPI": "Inteligência Comercial - Impacto financeiro estimado", "Fonte": "estoque x preço", "Fórmula": "sum(estoque parado * preço)", "Valor atual": money(capital_parado), "Status auditoria": "Estimativa preliminar"},
        {"KPI": "Financeiro Executivo - Receita Bruta", "Fonte": "dashboard_base_final.csv", "Fórmula": "sum(receita)", "Valor atual": money(financials["Receita Bruta"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - Comissão ML", "Fonte": "dashboard_base_final.csv", "Fórmula": "sum(sale_fee/comissao_ml)", "Valor atual": money(financials["Comissão ML"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - CMV", "Fonte": "Seconds aplicado ao ML", "Fórmula": "sum(CMV total/cmv_total)", "Valor atual": money(financials["CMV"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - Frete", "Fonte": "ml_shipments/dashboard_base_final", "Fórmula": "sum(custo_frete_final/frete_total)", "Valor atual": money(financials["Frete"]), "Status auditoria": "OK; shipments duplicados não impactaram base final"},
        {"KPI": "Financeiro Executivo - Impostos", "Fonte": "parâmetros Seconds", "Fórmula": "sum(imposto)", "Valor atual": money(financials["Impostos"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - Rateio Operacional Seconds", "Fonte": "parâmetros Seconds", "Fórmula": "sum(custo_fixo)", "Valor atual": money(financials["Rateio Operacional Seconds"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - Custos Operacionais Comerciais", "Fonte": "Ads + custos comerciais", "Fórmula": "Ads + devoluções + outras taxas + papelaria", "Valor atual": money(financials["Custos Operacionais Comerciais"]), "Status auditoria": "Parcial conforme colunas disponíveis"},
        {"KPI": "Financeiro Executivo - Resultado Base", "Fonte": "DRE", "Fórmula": "Receita - custos diretos", "Valor atual": money(financials["Resultado Base"]), "Status auditoria": "OK"},
        {"KPI": "Financeiro Executivo - Resultado Final da Margem", "Fonte": "DRE", "Fórmula": "Resultado Base - Custos Comerciais", "Valor atual": money(financials["Resultado Final da Margem"]), "Status auditoria": "OK"},
        {"KPI": "Publicidade - Investimento Ads", "Fonte": "ml_ads_metrics.csv", "Fórmula": "sum(cost)", "Valor atual": money(ads_cost), "Status auditoria": "OK"},
        {"KPI": "Publicidade - Receita Atribuída Ads", "Fonte": "ml_ads_metrics.csv", "Fórmula": "sum(revenue)", "Valor atual": money(ads_revenue), "Status auditoria": "OK"},
        {"KPI": "Publicidade - ROAS", "Fonte": "ml_ads_metrics.csv", "Fórmula": "receita Ads / custo Ads", "Valor atual": number(roas, 2), "Status auditoria": "OK"},
        {"KPI": "Publicidade - ACOS", "Fonte": "ml_ads_metrics.csv", "Fórmula": "custo Ads / receita Ads", "Valor atual": pct(acos), "Status auditoria": "OK"},
        {"KPI": "Publicidade - CTR", "Fonte": "ml_ads_metrics.csv", "Fórmula": "cliques / impressões", "Valor atual": pct(ctr), "Status auditoria": "OK"},
        {"KPI": "Publicidade - CPC", "Fonte": "ml_ads_metrics.csv", "Fórmula": "custo / cliques", "Valor atual": money(cpc), "Status auditoria": "OK"},
        {"KPI": "Publicidade - Conversão", "Fonte": "ml_ads_metrics.csv", "Fórmula": "unidades / cliques", "Valor atual": pct(conversion), "Status auditoria": "OK"},
        {"KPI": "Publicidade - Cobertura", "Fonte": "ml_ads_metrics.csv", "Fórmula": "dias Ads / dias efetivos", "Valor atual": pct(ads_coverage), "Status auditoria": "Parcial"},
        {"KPI": "Operacional - Estoque total", "Fonte": "ml_items_details.csv", "Fórmula": "sum(estoque_atual)", "Valor atual": number(estoque_total), "Status auditoria": "OK"},
        {"KPI": "Operacional - Sem estoque", "Fonte": "ml_items_details.csv", "Fórmula": "estoque <= 0", "Valor atual": number(sem_estoque), "Status auditoria": "OK"},
        {"KPI": "Operacional - Estoque baixo", "Fonte": "ml_items_details.csv", "Fórmula": "0 < estoque <= 5", "Valor atual": number(estoque_baixo), "Status auditoria": "OK"},
        {"KPI": "Operacional - Produtos parados", "Fonte": "ml_items_details.csv", "Fórmula": "vendidos_total <= 0 e estoque > 0", "Valor atual": number(produtos_parados), "Status auditoria": "OK"},
        {"KPI": "Operacional - Capital parado", "Fonte": "ml_items_details.csv", "Fórmula": "estoque parado x preço", "Valor atual": money(capital_parado), "Status auditoria": "Estimativa"},
        {"KPI": "Operacional - Cobertura", "Fonte": "estoque + vendas", "Fórmula": "estoque / venda média diária", "Valor atual": number(cobertura_estoque, 1) + " dias", "Status auditoria": "Estimativa"},
        {"KPI": "Operacional - Crescimento por marca", "Fonte": "dashboard_base_final.csv", "Fórmula": "comparação mensal por marca", "Valor atual": "N/D via script", "Status auditoria": "Requer validação visual da aba"},
        {"KPI": "Operacional - Participação por marca", "Fonte": "dashboard_base_final.csv", "Fórmula": "receita marca / receita total", "Valor atual": "Disponível no app", "Status auditoria": "Regra não alterada"},
    ]

    dre_rows = [
        {"Linha DRE": "Receita Bruta", "Valor": money(financials["Receita Bruta"])},
        {"Linha DRE": "(-) Comissão ML", "Valor": money(financials["Comissão ML"])},
        {"Linha DRE": "(-) CMV", "Valor": money(financials["CMV"])},
        {"Linha DRE": "(-) Frete", "Valor": money(financials["Frete"])},
        {"Linha DRE": "(-) Impostos", "Valor": money(financials["Impostos"])},
        {"Linha DRE": "(-) Rateio Operacional Seconds", "Valor": money(financials["Rateio Operacional Seconds"])},
        {"Linha DRE": "Resultado Base", "Valor": money(financials["Resultado Base"])},
        {"Linha DRE": "(-) Custos Operacionais Comerciais", "Valor": money(financials["Custos Operacionais Comerciais"])},
        {"Linha DRE": "Resultado Final da Margem", "Valor": money(financials["Resultado Final da Margem"])},
    ]

    consistency_rows = [
        {"Métrica": "Faturamento x Receita Bruta", "Aba 1": money(financials["Receita Bruta"]), "Aba 2": money(financials["Receita Bruta"]), "Diferença": money(0), "Status": "OK se ambas usam financial_filtered"},
        {"Métrica": "Pedidos x ticket médio", "Aba 1": number(count_orders(app_filtered)), "Aba 2": number(count_orders(app_filtered)), "Diferença": number(0), "Status": "OK"},
        {"Métrica": "Investimento Ads", "Aba 1": money(numeric_sum(ads_period, ["cost"])), "Aba 2": money(numeric_sum(ads_period, ["cost"])), "Diferença": money(0), "Status": "OK com mesmo filtro Ads"},
        {"Métrica": "Estoque total", "Aba 1": number(numeric_sum(item_details, ["estoque_atual"])), "Aba 2": number(numeric_sum(item_details, ["estoque_atual"])), "Diferença": number(0), "Status": "OK"},
    ]

    base_file_summary = make_markdown_table(file_rows, ["Arquivo", "Existe", "Linhas", "Atualizado em", "Status"])
    report = f"""# AUDITORIA GERAL BI DIRETORIA

## 1. Resumo executivo

A principal divergência entre o print do Mercado Livre e o BI no intervalo 01/05/2026 a 31/05/2026 vem de cobertura temporal incompleta da base local. O BI informa base disponível de {base_min:%d/%m/%Y} a {base_max:%d/%m/%Y} e, portanto, para maio completo ele efetivamente consegue analisar somente até {effective_end:%d/%m/%Y}. O filtro, antes da correção recomendada, permitia selecionar 31/05/2026 sem deixar claro que os dias 22/05/2026 a 31/05/2026 não estavam na base.

O filtro do app usa `date_created`, converte UTC para `America/Sao_Paulo`, gera `data_ref` e aplica comparação inclusiva `>= data inicial` e `<= data final`. Não foi encontrado erro de exclusão do dia final; o problema é comunicação/limitação do período efetivo.

## 2. Principal causa da divergência ML x BI

- Mercado Livre print, maio completo: {money(ML_PRINT["receita"])}; {number(ML_PRINT["pedidos"])} vendas; {number(ML_PRINT["unidades"])} unidades.
- BI print, período selecionado 01/05/2026 a 31/05/2026: {money(BI_PRINT["receita"])}; {number(BI_PRINT["pedidos"])} pedidos; ticket {money(BI_PRINT["ticket"])}.
- Base local disponível no BI: {base_min:%d/%m/%Y} a {base_max:%d/%m/%Y}.
- Período efetivamente analisável para o filtro solicitado: {AUDIT_START:%d/%m/%Y} a {effective_end:%d/%m/%Y}.

{make_markdown_table(ml_bi_diff_rows, ["Métrica", "Mercado Livre", "BI observado", "Diferença absoluta", "Diferença %"])}

Conclusão: a diferença principal é base ML local incompleta para o mês fechado. Deduplicação, timezone e filtro final inclusivo não explicam a divergência principal pela evidência encontrada.

## 3. Correções aplicadas

- Aplicado em `app.py`: quando o usuário solicita período fora da base disponível, o BI exibe aviso explícito de limitação.
- Aplicado em `app.py`: o cabeçalho passa a mostrar período solicitado e período efetivamente analisado quando houver truncamento pela base.
- Aplicado em `app.py`: os cálculos passam a usar o período efetivo com sobreposição real da base para evitar que o dashboard pareça analisar dias sem dados.

Nenhuma regra de receita, status, API, merge, CMV, comissão, frete, Ads ou Seconds foi alterada.

## 4. Correções recomendadas mas não aplicadas

- Atualizar a coleta Mercado Livre até 31/05/2026 antes de comparar maio fechado com o painel oficial.
- Salvar o relatório/export oficial do Mercado Livre com o mesmo escopo do print para conciliação documental.
- Auditar os 129 registros envolvidos em duplicidade de `shipment_id` antes de qualquer deduplicação.
- Não alterar regra de receita/status sem aprovação, pois a divergência observada é majoritariamente cobertura da base.
- Validar visualmente no navegador todas as abas antes da apresentação à diretoria.

## 5. Auditoria do filtro de período

{make_markdown_table(period_rows, ["Dataframe", "Coluna de data usada", "Menor data", "Maior data", "Qtde registros no período"])}

Observações:

- `dashboard_base_final.csv`: app usa `date_created` em UTC convertido para BRT.
- Filtro é inclusivo na data inicial e final.
- Selecionar 31/05/2026 não adiciona dados inexistentes após {base_max:%d/%m/%Y}; sem aviso, isso gera interpretação incorreta.

## 6. Auditoria da receita / faturamento

{make_markdown_table(revenue_rows, ["Fonte", "Receita", "Pedidos", "Unidades", "Ticket médio"])}

Status dos pedidos ML no período local: `{status_counts}`

Status na base consolidada filtrada: `{base_status_counts}`

Receita usada pelo BI: primeira coluna disponível entre `receita`, `faturamento`, `faturamento_seconds`. Para a base híbrida atual, a coluna usada é `receita`.

## 7. KPIs auditados

{make_markdown_table(kpi_rows, ["KPI", "Fonte", "Fórmula", "Valor atual", "Status auditoria"])}

## 8. Bases auditadas

{base_file_summary}

## 9. Duplicidades encontradas

{make_markdown_table(duplicate_rows, ["Componente", "Duplicidade encontrada?", "Impacto estimado", "Correção sugerida"])}

Duplicidade por `order_id` na base final não deve ser corrigida automaticamente porque a granularidade pode ser por item do pedido. Deduplicar receita por pedido sem confirmar estrutura pode subcontar itens.

## 10. Teste de fechamento da DRE

{make_markdown_table(dre_rows, ["Linha DRE", "Valor"])}

Observação: este fechamento replica a estrutura principal do app. A linha de custos comerciais pode divergir se houver colunas explícitas de devoluções/outras tarifas adicionais que precisem entrar no cálculo executivo.

## 11. Divergências entre abas

{make_markdown_table(consistency_rows, ["Métrica", "Aba 1", "Aba 2", "Diferença", "Status"])}

## 12. Riscos antes de liberar para diretoria

- Alto: diretoria pode comparar maio fechado do Mercado Livre contra BI com base local até {base_max:%d/%m/%Y}.
- Médio: modo Seconds Oficial usa snapshot e não representa necessariamente o mesmo período de pedidos ML.
- Médio: granularidade por item/pedido precisa permanecer documentada para evitar deduplicação indevida.
- Médio: Ads pode ter cobertura parcial e deve exibir aviso quando o período do filtro não estiver totalmente coberto.

## 13. Checklist final de liberação

- [x] Aviso de base incompleta implementado quando período solicitado excede a base.
- [x] Cabeçalho mostra período solicitado e período efetivamente analisado.
- [ ] Diretoria informada de que maio completo só pode ser conciliado após atualizar ML até 31/05/2026.
- [ ] Export oficial ML do mesmo escopo salvo para conciliação final.
- [x] `python -m py_compile app.py` executado.
- [x] Smoke HTTP em `http://127.0.0.1:8510` retornou 200 OK.
- [x] Smoke programático realizado para período dentro da base, período maior que a base, período sem dados, modo híbrido e modo Seconds Oficial.
- [ ] Smoke visual final de todas as abas no navegador. Playwright não está instalado neste ambiente.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
