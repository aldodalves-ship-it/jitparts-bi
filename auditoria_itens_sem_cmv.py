from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dashboard_base_final.csv"
RESULT_DIR = BASE_DIR / "resultado"
REPORT_PATH = BASE_DIR / "AUDITORIA_ITENS_SEM_CMV.md"
TOP_100_PATH = RESULT_DIR / "top_100_sem_cmv.csv"
FULL_PATH = RESULT_DIR / "itens_sem_cmv_completo.csv"


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


def text(df: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="object")
    return df[column].fillna(default).astype(str).str.strip()


def boolean(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    values = df[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "sim", "yes"})


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sem registros._"
    active = df.copy().fillna("")
    headers = [str(column) for column in active.columns]

    def clean_cell(value: object) -> str:
        cell = str(value).replace("\n", " ").replace("|", "\\|").strip()
        return cell if cell else " "

    rows = ["| " + " | ".join(headers) + " |"]
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in active.iterrows():
        rows.append("| " + " | ".join(clean_cell(row[column]) for column in active.columns) + " |")
    return "\n".join(rows)


def classify_missing_cmv(df: pd.DataFrame) -> pd.Series:
    item_id = text(df, "item_id")
    sku = text(df, "sku")
    match_seconds = boolean(df, "match_seconds")
    reliable = boolean(df, "parametro_confiavel")
    cmv_total_raw = pd.to_numeric(df.get("cmv_total", pd.Series(index=df.index)), errors="coerce")
    cmv_unit_raw = pd.to_numeric(df.get("cmv_unitario_seconds", pd.Series(index=df.index)), errors="coerce")

    reason = pd.Series("OUTRO", index=df.index, dtype="object")
    reason.loc[item_id.eq("")] = "ERRO_MERGE"
    reason.loc[item_id.ne("") & ~match_seconds] = "SEM_MATCH_SECONDS"
    reason.loc[item_id.ne("") & match_seconds & sku.isin(["", "N/D", "nan", "None"])] = "SKU_NAO_ENCONTRADO"
    reason.loc[item_id.ne("") & match_seconds & ~reliable] = "PARAMETRO_NAO_CONFIAVEL"
    reason.loc[item_id.ne("") & match_seconds & reliable & cmv_unit_raw.isna()] = "CMV_NULO"
    reason.loc[item_id.ne("") & match_seconds & reliable & cmv_total_raw.isna()] = "CMV_NULO"
    reason.loc[item_id.ne("") & match_seconds & reliable & (cmv_unit_raw.fillna(0) <= 0)] = "CMV_ZERADO"
    reason.loc[item_id.ne("") & match_seconds & reliable & (cmv_total_raw.fillna(0) <= 0)] = "CMV_ZERADO"
    return reason


def valid_cmv_mask(df: pd.DataFrame) -> pd.Series:
    reliable = boolean(df, "parametro_confiavel")
    match_seconds = boolean(df, "match_seconds")
    cmv_total = numeric(df, "cmv_total")
    cmv_unit = numeric(df, "cmv_unitario_seconds")
    return match_seconds & reliable & (cmv_total > 0) & (cmv_unit > 0)


def aggregate_items(df: pd.DataFrame) -> pd.DataFrame:
    active = df.copy()
    active["item_id"] = text(active, "item_id")
    active["sku"] = text(active, "sku").replace("", "N/D")
    active["produto"] = text(active, "produto").replace("", "N/D")
    active["marca"] = text(active, "marca").replace("", "N/D")
    active["categoria"] = text(active, "categoria").replace("", "N/D")
    active["receita"] = numeric(active, "receita")
    active["quantity"] = numeric(active, "quantity")
    active["order_id"] = text(active, "order_id")
    active["motivo_sem_cmv"] = classify_missing_cmv(active)

    grouped = (
        active.groupby(["item_id", "sku", "produto", "marca", "categoria", "motivo_sem_cmv"], dropna=False)
        .agg(
            receita_total=("receita", "sum"),
            pedidos=("order_id", "nunique"),
            unidades=("quantity", "sum"),
        )
        .reset_index()
        .sort_values(["receita_total", "pedidos"], ascending=[False, False])
    )
    return grouped


def grouped_impact(df: pd.DataFrame, by: Iterable[str], missing_mask: pd.Series) -> pd.DataFrame:
    active = df.copy()
    active["receita"] = numeric(active, "receita")
    active["receita_sem_cmv"] = active["receita"].where(missing_mask, 0)
    grouped = (
        active.groupby(list(by), dropna=False)
        .agg(receita_total=("receita", "sum"), receita_sem_cmv=("receita_sem_cmv", "sum"))
        .reset_index()
    )
    grouped["pct_sem_cmv"] = grouped["receita_sem_cmv"] / grouped["receita_total"].replace(0, pd.NA) * 100
    return grouped.sort_values("receita_sem_cmv", ascending=False)


def coverage_after_fix(total_orders: int, total_revenue: float, valid_orders: int, valid_revenue: float, items: pd.DataFrame, missing_rows: pd.DataFrame, top_n: int) -> dict[str, float]:
    top_items = set(items.head(top_n)["item_id"].astype(str))
    impacted = missing_rows[missing_rows["item_id"].astype(str).isin(top_items)].copy()
    recovered_orders = int(impacted["order_id"].nunique())
    recovered_revenue = float(numeric(impacted, "receita").sum())
    return {
        "top_n": top_n,
        "recovered_orders": recovered_orders,
        "recovered_revenue": recovered_revenue,
        "coverage_orders_pct": ((valid_orders + recovered_orders) / total_orders * 100) if total_orders else 0.0,
        "coverage_revenue_pct": ((valid_revenue + recovered_revenue) / total_revenue * 100) if total_revenue else 0.0,
        "remaining_unreconciled_revenue": max(total_revenue - valid_revenue - recovered_revenue, 0.0),
    }


def build_outputs() -> dict[str, object]:
    final = pd.read_csv(DATA_PATH, low_memory=False)
    valid_mask = valid_cmv_mask(final)
    missing_mask = ~valid_mask
    missing_rows = final[missing_mask].copy()
    missing_rows["motivo_sem_cmv"] = classify_missing_cmv(missing_rows)

    items = aggregate_items(missing_rows)
    top_100 = items.head(100).copy()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    items.to_csv(FULL_PATH, index=False, encoding="utf-8-sig")
    top_100.to_csv(TOP_100_PATH, index=False, encoding="utf-8-sig")

    total_orders = int(text(final, "order_id")[text(final, "order_id").ne("")].nunique())
    valid_orders = int(text(final, "order_id")[valid_mask & text(final, "order_id").ne("")].nunique())
    missing_orders = total_orders - valid_orders
    total_revenue = float(numeric(final, "receita").sum())
    valid_revenue = float(numeric(final.loc[valid_mask], "receita").sum())
    missing_revenue = float(numeric(missing_rows, "receita").sum())
    coverage_pct = valid_orders / total_orders * 100 if total_orders else 0.0

    reason_summary = (
        missing_rows.assign(receita_num=numeric(missing_rows, "receita"), order_id_clean=text(missing_rows, "order_id"))
        .groupby("motivo_sem_cmv", dropna=False)
        .agg(Pedidos=("order_id_clean", "nunique"), Receita=("receita_num", "sum"))
        .reset_index()
        .rename(columns={"motivo_sem_cmv": "Motivo"})
        .sort_values("Receita", ascending=False)
    )
    reason_summary["Participacao"] = reason_summary["Receita"] / missing_revenue * 100 if missing_revenue else 0.0

    final_for_group = final.copy()
    final_for_group["marca"] = text(final_for_group, "marca").replace("", "N/D")
    final_for_group["categoria"] = text(final_for_group, "categoria").replace("", "N/D")
    brand = grouped_impact(final_for_group, ["marca"], missing_mask).rename(columns={"marca": "Marca"})
    category = grouped_impact(final_for_group, ["categoria"], missing_mask).rename(columns={"categoria": "Categoria"})

    potential = pd.DataFrame(
        [
            coverage_after_fix(total_orders, total_revenue, valid_orders, valid_revenue, items, missing_rows, 20),
            coverage_after_fix(total_orders, total_revenue, valid_orders, valid_revenue, items, missing_rows, 50),
            coverage_after_fix(total_orders, total_revenue, valid_orders, valid_revenue, items, missing_rows, 100),
        ]
    )

    return {
        "final": final,
        "missing_rows": missing_rows,
        "items": items,
        "top_100": top_100,
        "reason_summary": reason_summary,
        "brand": brand,
        "category": category,
        "potential": potential,
        "total_orders": total_orders,
        "valid_orders": valid_orders,
        "missing_orders": missing_orders,
        "total_revenue": total_revenue,
        "valid_revenue": valid_revenue,
        "missing_revenue": missing_revenue,
        "coverage_pct": coverage_pct,
    }


def format_item_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df.copy()
    if "receita_total" in table.columns:
        table["receita_total"] = table["receita_total"].map(money)
    if "unidades" in table.columns:
        table["unidades"] = table["unidades"].map(lambda value: number(value, 0))
    return table


def format_money_percent_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df.copy()
    for column in table.columns:
        if "receita" in column.lower() or column == "Receita":
            table[column] = table[column].map(money)
        if "pct" in column.lower() or column == "Participacao":
            table[column] = table[column].map(percent)
    return table


def write_report(outputs: dict[str, object]) -> None:
    items = outputs["items"]
    top_100 = outputs["top_100"]
    reason_summary = outputs["reason_summary"]
    brand = outputs["brand"]
    category = outputs["category"]
    potential = outputs["potential"].copy()

    potential_display = potential.rename(
        columns={
            "top_n": "Cenario",
            "recovered_orders": "Pedidos recuperados",
            "recovered_revenue": "Receita recuperada",
            "coverage_orders_pct": "Cobertura pedidos apos correcao",
            "coverage_revenue_pct": "Cobertura receita apos correcao",
            "remaining_unreconciled_revenue": "Receita sem CMV remanescente",
        }
    )
    potential_display["Cenario"] = potential_display["Cenario"].map(lambda value: f"Corrigir Top {int(value)}")
    potential_display["Receita recuperada"] = potential_display["Receita recuperada"].map(money)
    potential_display["Cobertura pedidos apos correcao"] = potential_display["Cobertura pedidos apos correcao"].map(percent)
    potential_display["Cobertura receita apos correcao"] = potential_display["Cobertura receita apos correcao"].map(percent)
    potential_display["Receita sem CMV remanescente"] = potential_display["Receita sem CMV remanescente"].map(money)

    reason_display = reason_summary.copy()
    reason_display["Receita"] = reason_display["Receita"].map(money)
    reason_display["Participacao"] = reason_display["Participacao"].map(percent)

    top_20_display = format_item_table(items.head(20))
    top_100_display = format_item_table(top_100)
    brand_display = format_money_percent_table(brand.head(30))
    category_display = format_money_percent_table(category.head(30))

    report = f"""# Auditoria 3 - Itens sem CMV confiavel

## 1. Resumo executivo

Base auditada: `{DATA_PATH.relative_to(BASE_DIR)}`.

Pedidos totais: **{number(outputs["total_orders"])}**  
Pedidos com CMV valido: **{number(outputs["valid_orders"])}**  
Pedidos sem CMV valido: **{number(outputs["missing_orders"])}**  
Cobertura CMV atual: **{percent(outputs["coverage_pct"])}**  
Receita sem CMV valido: **{money(outputs["missing_revenue"])}**

Foram identificados **{number(len(items))} itens/item_id** com algum problema de CMV confiavel. A lista operacional foi gravada em:

- `{FULL_PATH.relative_to(BASE_DIR)}`
- `{TOP_100_PATH.relative_to(BASE_DIR)}`

## 2. Top 20 produtos mais criticos

{markdown_table(top_20_display)}

## 3. Top 100 por receita

{markdown_table(top_100_display)}

## 4. Impacto financeiro por motivo

{markdown_table(reason_display)}

## 5. Cobertura por marca

{markdown_table(brand_display)}

## 6. Cobertura por categoria

{markdown_table(category_display)}

## 7. Ganho potencial ao corrigir

{markdown_table(potential_display)}

## 8. Plano recomendado para atingir 99%+

1. Corrigir primeiro os itens do `top_100_sem_cmv.csv`, priorizando a ordem por `receita_total`.
2. Para `SEM_MATCH_SECONDS`, cadastrar ou ajustar o `item_id` MLB na base de parametros da Seconds.
3. Para `PARAMETRO_NAO_CONFIAVEL`, revisar o parametro financeiro e marcar como confiavel apenas apos validar CMV, frete, imposto, comissao e custo fixo.
4. Para `CMV_ZERADO` ou `CMV_NULO`, preencher CMV unitario real e regenerar `parametros_financeiros_seconds.csv`.
5. Rodar novamente a consolidacao e esta auditoria ate a cobertura de pedidos e receita ficar acima de 99%.

## 9. Observacoes de controle

Nenhuma regra financeira, DRE, merge ou calculo foi alterado por esta auditoria. Os arquivos CSV sao listas operacionais para correcao cadastral/parametrica na Seconds.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    outputs = build_outputs()
    write_report(outputs)
    print(f"CSV completo: {FULL_PATH}")
    print(f"CSV top 100: {TOP_100_PATH}")
    print(f"Relatorio: {REPORT_PATH}")
    print(f"Pedidos sem CMV valido: {outputs['missing_orders']}")
    print(f"Receita sem CMV valido: {outputs['missing_revenue']:.2f}")


if __name__ == "__main__":
    main()
