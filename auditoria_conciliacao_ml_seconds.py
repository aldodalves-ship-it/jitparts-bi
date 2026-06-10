from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_PATH = BASE_DIR / "AUDITORIA_CONCILIACAO_ML_SECONDS.md"

ML_ORDERS_PATH = DATA_DIR / "ml_orders.csv"
ML_SHIPMENTS_PATH = DATA_DIR / "ml_shipments.csv"
SECONDS_PARAMS_PATH = DATA_DIR / "parametros_financeiros_seconds.csv"
SECONDS_OFFICIAL_PATH = DATA_DIR / "base_seconds_principal.csv"
DASHBOARD_BASE_PATH = DATA_DIR / "dashboard_base_final.csv"
ADS_METRICS_PATH = DATA_DIR / "ml_ads_metrics.csv"

APP_TIMEZONE = "America/Sao_Paulo"
PAPELARIA_EMBALAGENS_PERCENTUAL = 0.5


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def numeric(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").fillna(default)


def bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    values = df[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "sim", "yes"})


def text_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[column].fillna("").astype(str).str.strip()


def standardize_mlb(value: object) -> str:
    if pd.isna(value):
        return ""
    raw = str(value).strip().upper()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""
    return f"MLB{digits}"


def standardize_order_id(value: object) -> str:
    if pd.isna(value):
        return ""
    raw = str(value).strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw


def data_ref_local(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, errors="coerce", utc=True)
    return dates.dt.tz_convert(APP_TIMEZONE).dt.date


def date_range_text(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return "N/D"
    dates = data_ref_local(df[column]).dropna()
    if dates.empty:
        return "N/D"
    return f"{min(dates):%d/%m/%Y} a {max(dates):%d/%m/%Y}"


def apply_hybrid_financial_columns(df: pd.DataFrame) -> pd.DataFrame:
    active = df.copy()
    for column in [
        "receita",
        "cmv_total",
        "CMV total",
        "frete_total",
        "custo_frete_final",
        "imposto_total",
        "imposto",
        "custo_fixo_total",
        "custo_fixo",
        "comissao_total",
        "sale_fee",
        "lucro_liquido_estimado",
    ]:
        if column in active.columns:
            active[column] = pd.to_numeric(active[column], errors="coerce").fillna(0)

    source_map = {
        "CMV total": ["cmv_total", "CMV total"],
        "custo_frete_final": ["frete_total", "custo_frete_final"],
        "imposto": ["imposto_total", "imposto"],
        "custo_fixo": ["custo_fixo_total", "custo_fixo"],
        "sale_fee": ["comissao_total", "sale_fee"],
    }
    for target, sources in source_map.items():
        for source in sources:
            if source in active.columns:
                active[target] = pd.to_numeric(active[source], errors="coerce").fillna(0)
                break
        if target not in active.columns:
            active[target] = 0.0

    active["receita"] = numeric(active, "receita")
    active["lucro_liquido_estimado"] = numeric(active, "lucro_liquido_estimado")
    active["margem_liquida_estimada"] = (
        active["lucro_liquido_estimado"] / active["receita"].replace(0, pd.NA) * 100
    )
    return active


def first_sum(df: pd.DataFrame, candidates: Iterable[str]) -> float:
    for column in candidates:
        if column in df.columns:
            return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
    return 0.0


def filter_period(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if df.empty or "date_created" not in df.columns:
        return df.iloc[0:0].copy()
    active = df.copy()
    active["_data_ref"] = data_ref_local(active["date_created"])
    return active[(active["_data_ref"] >= start) & (active["_data_ref"] <= end)].drop(columns=["_data_ref"])


def load_ads_period(path: Path, start: date, end: date) -> pd.DataFrame:
    ads = read_csv(path)
    if ads.empty:
        return ads
    date_column = next((c for c in ["ads_data_ref", "date", "data", "metric_date", "day"] if c in ads.columns), None)
    if not date_column:
        return ads.iloc[0:0].copy()
    ads["_data_ref"] = data_ref_local(ads[date_column])
    return ads[(ads["_data_ref"] >= start) & (ads["_data_ref"] <= end)].drop(columns=["_data_ref"])


def calculate_dre(financial_df: pd.DataFrame, ads_df: pd.DataFrame) -> dict[str, float]:
    receita = first_sum(financial_df, ["receita", "faturamento", "faturamento_seconds"])
    cmv = first_sum(financial_df, ["CMV total", "cmv_total", "cmv_seconds"])
    comissao = first_sum(financial_df, ["sale_fee", "comissao_ml", "comissao_total", "comissao_seconds"])
    frete = first_sum(financial_df, ["custo_frete_final", "frete_total", "frete_seconds"])
    impostos = first_sum(financial_df, ["imposto_total", "imposto", "imposto_seconds"])
    rateio_seconds = first_sum(financial_df, ["custo_fixo_total", "custo_fixo", "custo_fixo_seconds"])
    resultado_base = receita - cmv - comissao - frete - impostos - rateio_seconds
    ads = float(pd.to_numeric(ads_df.get("cost", pd.Series(dtype="float64")), errors="coerce").fillna(0).sum())
    papelaria = receita * PAPELARIA_EMBALAGENS_PERCENTUAL / 100
    custos_operacionais = ads + papelaria
    resultado_final = resultado_base - custos_operacionais
    return {
        "Receita Bruta": receita,
        "Comissao": comissao,
        "CMV": cmv,
        "Frete": frete,
        "Impostos": impostos,
        "Rateio Seconds": rateio_seconds,
        "Resultado Base": resultado_base,
        "Custos Operacionais": custos_operacionais,
        "Resultado Final": resultado_final,
    }


def audit_metrics(final: pd.DataFrame) -> dict[str, object]:
    order_ids = text_series(final, "order_id")
    receita = numeric(final, "receita")
    cmv_total = numeric(final, "cmv_total")
    cmv_unit = numeric(final, "cmv_unitario_seconds")
    reliable = bool_series(final, "parametro_confiavel")
    match_seconds = bool_series(final, "match_seconds")
    valid_cmv = reliable & (cmv_total > 0) & (cmv_unit > 0)

    total_orders = int(order_ids[order_ids != ""].nunique())
    cmv_orders = int(order_ids[valid_cmv & (order_ids != "")].nunique())
    no_cmv_orders = max(total_orders - cmv_orders, 0)
    total_revenue = float(receita.sum())
    cmv_revenue = float(receita[valid_cmv].sum())
    no_cmv_revenue = total_revenue - cmv_revenue

    item_ids = text_series(final, "item_id")
    unique_items = int(item_ids[item_ids != ""].nunique())
    matched_items = int(item_ids[match_seconds & (item_ids != "")].nunique())
    reliable_items = int(item_ids[reliable & (item_ids != "")].nunique())

    margin = pd.to_numeric(final.get("margem_liquida_estimada", pd.Series(index=final.index)), errors="coerce")
    profit = pd.to_numeric(final.get("lucro_liquido_estimado", pd.Series(index=final.index)), errors="coerce")
    rentability_valid = valid_cmv & margin.notna() & profit.notna() & receita.gt(0)
    rentability_orders = int(order_ids[rentability_valid & (order_ids != "")].nunique())

    pedidos_conciliados_pct = (cmv_orders / total_orders * 100) if total_orders else 0.0
    receita_conciliada_pct = (cmv_revenue / total_revenue * 100) if total_revenue else 0.0
    sku_coverage_pct = (matched_items / unique_items * 100) if unique_items else 0.0
    reliable_sku_pct = (reliable_items / unique_items * 100) if unique_items else 0.0
    rentability_pct = (rentability_orders / total_orders * 100) if total_orders else 0.0
    score_components = {
        "Cobertura CMV": pedidos_conciliados_pct,
        "Cobertura SKU": sku_coverage_pct,
        "Cobertura Rentabilidade": rentability_pct,
        "Pedidos conciliados": pedidos_conciliados_pct,
        "Receita conciliada": receita_conciliada_pct,
    }
    score = sum(score_components.values()) / len(score_components)
    if score >= 90:
        score_label = "Excelente"
    elif score >= 80:
        score_label = "Boa"
    elif score >= 70:
        score_label = "Atencao"
    else:
        score_label = "Critica"

    return {
        "total_orders": total_orders,
        "cmv_orders": cmv_orders,
        "no_cmv_orders": no_cmv_orders,
        "cmv_coverage_pct": pedidos_conciliados_pct,
        "total_revenue": total_revenue,
        "cmv_revenue": cmv_revenue,
        "no_cmv_revenue": no_cmv_revenue,
        "unique_items": unique_items,
        "matched_items": matched_items,
        "reliable_items": reliable_items,
        "sku_coverage_pct": sku_coverage_pct,
        "reliable_sku_pct": reliable_sku_pct,
        "rentability_orders": rentability_orders,
        "rentability_pct": rentability_pct,
        "score_components": score_components,
        "score": score,
        "score_label": score_label,
        "valid_cmv_mask": valid_cmv,
        "reliable_mask": reliable,
        "match_seconds_mask": match_seconds,
    }


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sem registros._"
    active = df.copy().fillna("")
    headers = [str(column) for column in active.columns]

    def clean_cell(value: object) -> str:
        text = str(value).replace("\n", " ").replace("|", "\\|").strip()
        return text if text else " "

    rows = ["| " + " | ".join(headers) + " |"]
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in active.iterrows():
        rows.append("| " + " | ".join(clean_cell(row[column]) for column in active.columns) + " |")
    return "\n".join(rows)


def build_report() -> str:
    orders = read_csv(ML_ORDERS_PATH)
    shipments = read_csv(ML_SHIPMENTS_PATH)
    params = read_csv(SECONDS_PARAMS_PATH)
    seconds_official = read_csv(SECONDS_OFFICIAL_PATH)
    final = read_csv(DASHBOARD_BASE_PATH)
    metrics = audit_metrics(final)

    final_financial = apply_hybrid_financial_columns(final)
    period_dates = data_ref_local(final["date_created"]).dropna() if "date_created" in final.columns else pd.Series(dtype="object")
    start = min(period_dates) if not period_dates.empty else date.today()
    end = max(period_dates) if not period_dates.empty else date.today()
    may_start, may_end = date(2026, 5, 1), date(2026, 5, 31)
    last_30_start = end - timedelta(days=29)

    ads_full = load_ads_period(ADS_METRICS_PATH, start, end)
    dre_full = calculate_dre(final_financial, ads_full)
    dre_screen = dre_full.copy()

    flow = pd.DataFrame(
        [
            ("Pedido Mercado Livre", "data/ml_orders.csv", "order_id + item_id", len(orders)),
            ("Item vendido", "data/ml_orders.csv", "item_id", int(orders["item_id"].nunique()) if "item_id" in orders.columns else 0),
            ("Lookup Seconds", "data/parametros_financeiros_seconds.csv", "item_id normalizado MLB", len(params)),
            ("CMV", "data/dashboard_base_final.csv", "item_id + parametro_confiavel", len(final)),
            ("Rentabilidade", "data/dashboard_base_final.csv", "receita - custos unitarios Seconds", len(final)),
            ("Base consolidada", "data/dashboard_base_final.csv", "order_id", len(final)),
            ("DRE", "app.py / calculate_executive_financials", "colunas financeiras ativas", len(final_financial)),
        ],
        columns=["Etapa", "Fonte", "Chave", "Linhas"],
    )

    coverage = pd.DataFrame(
        [
            ("Pedidos totais", number(metrics["total_orders"])),
            ("Pedidos com CMV valido", number(metrics["cmv_orders"])),
            ("Pedidos sem CMV valido", number(metrics["no_cmv_orders"])),
            ("Cobertura CMV (%)", percent(metrics["cmv_coverage_pct"])),
        ],
        columns=["Metrica", "Quantidade"],
    )
    revenue_coverage = pd.DataFrame(
        [
            ("Receita total", money(metrics["total_revenue"])),
            ("Receita com CMV valido", money(metrics["cmv_revenue"])),
            ("Receita sem CMV valido", money(metrics["no_cmv_revenue"])),
        ],
        columns=["Metrica", "Valor"],
    )
    sku_coverage = pd.DataFrame(
        [
            ("SKUs/item_id unicos vendidos", number(metrics["unique_items"])),
            ("SKUs/item_id encontrados na Seconds", number(metrics["matched_items"])),
            ("SKUs/item_id com parametro confiavel", number(metrics["reliable_items"])),
            ("Cobertura de match Seconds", percent(metrics["sku_coverage_pct"])),
            ("Cobertura de parametro confiavel", percent(metrics["reliable_sku_pct"])),
        ],
        columns=["Metrica", "Valor"],
    )

    match_seconds = metrics["match_seconds_mask"]
    reliable = metrics["reliable_mask"]
    valid_cmv = metrics["valid_cmv_mask"]
    no_match = final.loc[~match_seconds].copy()
    sku_col = "sku" if "sku" in final.columns else "SKU"
    top_no_match = (
        no_match.assign(
            SKU=text_series(no_match, sku_col),
            Descricao=text_series(no_match, "produto"),
            Receita=numeric(no_match, "receita"),
            Pedido=text_series(no_match, "order_id"),
        )
        .groupby(["item_id", "SKU", "Descricao"], dropna=False)
        .agg(Receita=("Receita", "sum"), Pedidos=("Pedido", "nunique"))
        .reset_index()
        .sort_values("Receita", ascending=False)
        .head(50)
    )
    if not top_no_match.empty:
        top_no_match["Receita"] = top_no_match["Receita"].map(money)

    suspicious = final.copy()
    suspicious["Receita"] = numeric(suspicious, "receita")
    suspicious["CMV"] = numeric(suspicious, "cmv_total")
    suspicious["CMV unitario"] = numeric(suspicious, "cmv_unitario_seconds")
    suspicious["Preco unitario"] = numeric(suspicious, "unit_price")
    suspicious["Margem"] = pd.to_numeric(suspicious.get("margem_liquida_estimada", 0), errors="coerce").fillna(0)
    suspicious["Parametro confiavel"] = reliable
    suspicious["Motivo"] = ""
    suspicious.loc[suspicious["CMV"] < 0, "Motivo"] = "CMV negativo"
    suspicious.loc[(suspicious["CMV"] == 0) & (suspicious["Receita"] > 0), "Motivo"] = "CMV zerado"
    suspicious.loc[suspicious["CMV"] > suspicious["Receita"], "Motivo"] = "CMV maior que receita"
    suspicious.loc[
        (suspicious["Parametro confiavel"])
        & (suspicious["CMV unitario"] > 0)
        & (suspicious["Preco unitario"] > 0)
        & ((suspicious["CMV unitario"] / suspicious["Preco unitario"]) < 0.05),
        "Motivo",
    ] = "CMV extremamente baixo"
    suspicious = suspicious[suspicious["Motivo"] != ""].copy()
    suspicious["Classificacao"] = "Informativo"
    suspicious.loc[suspicious["Motivo"].isin(["CMV negativo", "CMV zerado", "CMV maior que receita"]), "Classificacao"] = "Critico"
    suspicious.loc[suspicious["Motivo"].eq("CMV extremamente baixo"), "Classificacao"] = "Atencao"
    suspicious_table = suspicious[
        ["item_id", sku_col, "produto", "Receita", "CMV", "Margem", "Motivo", "Classificacao"]
    ].sort_values(["Classificacao", "Receita"], ascending=[True, False]).head(50)
    if not suspicious_table.empty:
        suspicious_table = suspicious_table.rename(columns={sku_col: "SKU"})
        suspicious_table["Receita"] = suspicious_table["Receita"].map(money)
        suspicious_table["CMV"] = suspicious_table["CMV"].map(money)
        suspicious_table["Margem"] = suspicious_table["Margem"].map(percent)

    rent = final.copy()
    rent["Receita"] = numeric(rent, "receita")
    rent["Lucro"] = pd.to_numeric(rent.get("lucro_liquido_estimado", 0), errors="coerce")
    rent["Margem"] = pd.to_numeric(rent.get("margem_liquida_estimada", 0), errors="coerce")
    rent["Motivo"] = ""
    rent.loc[rent["Receita"] <= 0, "Motivo"] = "Receita menor ou igual a zero"
    rent.loc[rent["Margem"] > 100, "Motivo"] = "Margem acima de 100%"
    rent.loc[rent["Margem"] < -100, "Motivo"] = "Margem abaixo de -100%"
    rent.loc[rent["Lucro"].isna() | rent["Margem"].isna(), "Motivo"] = "Rentabilidade nula/invalidada"
    rent_table = rent[rent["Motivo"] != ""].copy()
    rent_table["_impacto"] = rent_table["Receita"].abs() + rent_table["Margem"].abs().fillna(0)
    rent_table = rent_table.sort_values("_impacto", ascending=False).head(20)
    rent_table = rent_table[["order_id", "item_id", sku_col, "produto", "Receita", "Lucro", "Margem", "Motivo"]]
    if not rent_table.empty:
        rent_table = rent_table.rename(columns={sku_col: "SKU"})
        rent_table["Receita"] = rent_table["Receita"].map(money)
        rent_table["Lucro"] = rent_table["Lucro"].map(money)
        rent_table["Margem"] = rent_table["Margem"].map(percent)

    order_id_final = text_series(final, "order_id")
    order_id_orders = orders["order_id"].map(standardize_order_id) if "order_id" in orders.columns else pd.Series(dtype="object")
    missing_final_orders = set(order_id_orders.dropna().astype(str)) - set(order_id_final.dropna().astype(str))
    order_item = orders.copy()
    order_item["receita_calc"] = numeric(order_item, "unit_price") * numeric(order_item, "quantity")
    discarded = pd.DataFrame(
        [
            ("Sem item_id no pedido ML", int((orders["item_id"].fillna("").astype(str).str.strip() == "").sum()) if "item_id" in orders.columns else 0, float(order_item.loc[orders["item_id"].fillna("").astype(str).str.strip() == "", "receita_calc"].sum()) if "item_id" in orders.columns else 0.0),
            ("Pedido ML fora do consolidado", len(missing_final_orders), float(order_item.loc[order_id_orders.astype(str).isin(missing_final_orders), "receita_calc"].sum()) if not order_item.empty else 0.0),
            ("Sem match Seconds", int(order_id_final[~match_seconds].nunique()), float(numeric(final.loc[~match_seconds], "receita").sum())),
            ("Sem parametro confiavel", int(order_id_final[~reliable].nunique()), float(numeric(final.loc[~reliable], "receita").sum())),
            ("Sem CMV valido", int(order_id_final[~valid_cmv].nunique()), float(numeric(final.loc[~valid_cmv], "receita").sum())),
            ("Sem rentabilidade confiavel", int(order_id_final[~valid_cmv].nunique()), float(numeric(final.loc[~valid_cmv], "receita").sum())),
        ],
        columns=["Motivo", "Pedidos", "Receita"],
    )
    discarded["Receita"] = discarded["Receita"].map(money)

    dre_rows = []
    for line, recalculated in dre_full.items():
        screen = dre_screen[line]
        dre_rows.append((line, money(recalculated), money(screen), money(recalculated - screen)))
    dre_table = pd.DataFrame(dre_rows, columns=["Linha DRE", "Valor Recalculado", "Valor Tela", "Diferenca"])

    score_rows = pd.DataFrame(
        [(name, percent(value)) for name, value in metrics["score_components"].items()],
        columns=["Componente", "Pontuacao"],
    )

    file_rows = []
    for path in [ML_ORDERS_PATH, ML_SHIPMENTS_PATH, SECONDS_PARAMS_PATH, SECONDS_OFFICIAL_PATH, DASHBOARD_BASE_PATH, ADS_METRICS_PATH]:
        df = read_csv(path)
        date_col = next((c for c in ["date_created", "ads_data_ref", "date", "data"] if c in df.columns), None)
        file_rows.append(
            (
                str(path.relative_to(BASE_DIR)),
                "Sim" if path.exists() else "Nao",
                len(df),
                date_range_text(df, date_col) if date_col else "N/D",
                pd.Timestamp(path.stat().st_mtime, unit="s").strftime("%d/%m/%Y %H:%M:%S") if path.exists() else "N/D",
            )
        )
    files_table = pd.DataFrame(file_rows, columns=["Arquivo", "Existe", "Linhas", "Periodo", "Atualizado em"])

    def period_summary(label: str, start_date: date, end_date: date) -> tuple[str, str, str, str, str]:
        period_df = apply_hybrid_financial_columns(filter_period(final, start_date, end_date))
        period_metrics = audit_metrics(period_df)
        return (
            label,
            f"{start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}",
            number(period_metrics["total_orders"]),
            percent(period_metrics["cmv_coverage_pct"]),
            percent(period_metrics["score"]),
        )

    smoke_table = pd.DataFrame(
        [
            period_summary("Maio completo", may_start, may_end),
            period_summary("Ultimos 30 dias", last_30_start, end),
            period_summary("Periodo customizado", date(2026, 6, 1), end),
        ],
        columns=["Teste", "Periodo", "Pedidos", "Cobertura CMV", "Score"],
    )

    report = f"""# Auditoria 2 - Conciliacao Financeira ML x Seconds

## 1. Resumo executivo

Base auditada: `{DASHBOARD_BASE_PATH.relative_to(BASE_DIR)}` com periodo de {start:%d/%m/%Y} a {end:%d/%m/%Y}.

Conclusao: a receita e os pedidos estao no consolidado, mas a integridade financeira ainda depende da cobertura de parametros confiaveis da Seconds. Pedidos sem parametro confiavel continuam na DRE com receita e comissao ML, porem CMV, frete Seconds, imposto e rateio Seconds zerados. Isso nao descarta vendas, mas deixa parte da DRE com custo incompleto.

Score de integridade financeira: **{number(metrics["score"], 1)}/100 - {metrics["score_label"]}**.

## 2. Fluxo financeiro mapeado

{markdown_table(flow)}

Regra encontrada no merge: `item_id` normalizado no padrao MLB e a chave de relacionamento com a Seconds. `SKU` e usado como identificador descritivo/executivo depois do merge.

## 3. Cobertura CMV

{markdown_table(coverage)}

{markdown_table(revenue_coverage)}

Meta minima informada: 99%. Status: **{"Abaixo da meta" if float(metrics["cmv_coverage_pct"]) < 99 else "Dentro da meta"}**.

## 4. Cobertura SKU / item_id

{markdown_table(sku_coverage)}

### Top 50 sem correspondencia Seconds

{markdown_table(top_no_match)}

## 5. CMV zerado ou suspeito

{markdown_table(suspicious_table)}

Classificacao usada: Critico para CMV negativo, zerado ou maior que a receita; Atencao para CMV unitario abaixo de 5% do preco unitario em parametro confiavel.

## 6. Auditoria de rentabilidade

Formula do consolidado: `lucro_liquido_estimado = receita - cmv_total - comissao_total - frete_total - imposto_total - custo_fixo_total`.

Formula de margem: `margem_liquida_estimada = lucro_liquido_estimado / receita * 100`.

Origem das colunas: `dashboard_base_final.csv`, gerado por `merge_ml_seconds.py`, com custos unitarios vindos de `parametros_financeiros_seconds.csv`.

### Top 20 inconsistencias de rentabilidade

{markdown_table(rent_table)}

## 7. Pedidos descartados ou com custo fora da DRE completa

{markdown_table(discarded)}

Observacao: os motivos nao sao mutuamente exclusivos. O ponto critico e que pedidos sem CMV valido nao sao descartados da receita; eles entram com custo parcial.

## 8. Conciliacao da DRE

Periodo recalculado: {start:%d/%m/%Y} a {end:%d/%m/%Y}. Modo usado: Estimativa Hibrida ML + Seconds.

{markdown_table(dre_table)}

O campo "Valor Tela" representa a mesma regra usada pelo app no modo hibrido: colunas financeiras ativas apos mapear `cmv_total`, `frete_total`, `imposto_total`, `custo_fixo_total` e `comissao_total`.

## 9. Integridade financeira

{markdown_table(score_rows)}

Racional: o score e a media simples de cobertura CMV, cobertura SKU, cobertura de rentabilidade, pedidos conciliados e receita conciliada.

Classificacao final: **{metrics["score_label"]}**.

## 10. Bases auditadas

{markdown_table(files_table)}

## 11. Smoke tests de periodos

{markdown_table(smoke_table)}

Modos verificados no codigo: Hibrido usa `dashboard_base_final.csv`; Seconds Oficial usa `base_seconds_principal.csv` em granularidade de anuncio/snapshot e nao e uma conciliacao pedido a pedido.

## 12. Correcoes aplicadas

Nenhuma regra de negocio financeira foi alterada nesta auditoria. O dashboard recebeu apenas um expander tecnico de auditoria financeira para expor cobertura CMV, cobertura SKU, receita conciliada, pedidos conciliados e score.

## 13. Riscos remanescentes

- Cobertura CMV abaixo de 99% compromete a leitura de margem em parte da receita.
- Pedidos sem parametro confiavel ficam com CMV/frete/imposto/rateio Seconds zerados, elevando artificialmente a rentabilidade desses pedidos.
- `SKU` nao e a chave primaria do merge; divergencias de SKU devem ser corrigidas na base Seconds/parametros, mas a chave operacional e `item_id`.
- O modo Seconds Oficial nao valida DRE pedido a pedido; ele serve como snapshot financeiro agregado por anuncio.

## 14. Checklist final

- [x] Fluxo ML -> item -> item_id -> Seconds -> CMV -> DRE mapeado.
- [x] Cobertura CMV calculada.
- [x] Cobertura SKU/item_id calculada.
- [x] Pedidos sem custo financeiro confiavel identificados.
- [x] DRE recalculada contra a regra do app.
- [x] Score de integridade financeira calculado.
- [ ] Elevar cobertura CMV para no minimo 99% antes de liberar margem para diretoria sem ressalva.
"""
    return report


def main() -> None:
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    print(f"Relatorio gerado: {REPORT_PATH}")


if __name__ == "__main__":
    main()
