"""Cria parametros financeiros unitarios por item_id a partir da base Seconds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/base_seconds_principal.csv")
OUTPUT_PATH = Path("data/parametros_financeiros_seconds.csv")

TEXT_COLUMNS = [
    "item_id",
    "sku",
    "produto",
    "marca",
    "categoria",
    "full",
    "flex",
    "status",
    "link_anuncio",
]

NUMERIC_COLUMNS = [
    "preco_venda_seconds",
    "cmv_seconds",
    "comissao_seconds",
    "frete_seconds",
    "custo_fixo_seconds",
    "imposto_seconds",
    "lucro_liquido_seconds",
    "margem_seconds",
    "vendidos",
    "cmv_seconds_unitario",
    "comissao_seconds_unitario",
    "frete_seconds_unitario",
    "custo_fixo_seconds_unitario",
    "imposto_seconds_unitario",
    "lucro_liquido_seconds_unitario",
]

OUTPUT_COLUMNS = [
    "item_id",
    "sku",
    "produto",
    "marca",
    "categoria",
    "preco_venda_seconds",
    "cmv_unitario_seconds",
    "comissao_unitaria_seconds",
    "frete_unitario_seconds",
    "custo_fixo_unitario_seconds",
    "imposto_unitario_seconds",
    "lucro_liquido_unitario_seconds",
    "margem_seconds",
    "full",
    "flex",
    "status",
    "link_anuncio",
    "parametro_confiavel",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text


def first_non_empty(values: pd.Series) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def last_non_empty(values: pd.Series) -> str:
    for value in reversed(values.tolist()):
        text = clean_text(value)
        if text:
            return text
    return ""


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce").fillna(0)
    numerator = pd.to_numeric(numerator, errors="coerce").fillna(0)
    return numerator.div(denominator.where(denominator > 0)).fillna(0)


def unit_from_total_or_fallback(df: pd.DataFrame, total_column: str, fallback_column: str) -> pd.Series:
    calculated = safe_divide(df[total_column], df["vendidos"])
    fallback = pd.to_numeric(df.get(fallback_column, 0), errors="coerce").fillna(0)
    return calculated.where(df["vendidos"] > 0, fallback)


def read_seconds_base(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_csv(path)


def normalize_base(df: pd.DataFrame) -> pd.DataFrame:
    required = ["item_id", "vendidos", "cmv_seconds"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{INPUT_PATH} sem colunas obrigatorias: {missing}")

    normalized = df.copy()
    for column in TEXT_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""
        normalized[column] = normalized[column].map(clean_text)

    for column in NUMERIC_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = 0
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").fillna(0)

    normalized = normalized[normalized["item_id"] != ""].copy()
    return normalized


def build_parameters(df: pd.DataFrame) -> pd.DataFrame:
    base = normalize_base(df)

    aggregations = {
        "sku": first_non_empty,
        "produto": first_non_empty,
        "marca": first_non_empty,
        "categoria": first_non_empty,
        "preco_venda_seconds": "last",
        "cmv_seconds": "sum",
        "comissao_seconds": "sum",
        "frete_seconds": "sum",
        "custo_fixo_seconds": "sum",
        "imposto_seconds": "sum",
        "lucro_liquido_seconds": "sum",
        "margem_seconds": "mean",
        "vendidos": "sum",
        "cmv_seconds_unitario": "last",
        "comissao_seconds_unitario": "last",
        "frete_seconds_unitario": "last",
        "custo_fixo_seconds_unitario": "last",
        "imposto_seconds_unitario": "last",
        "lucro_liquido_seconds_unitario": "last",
        "full": last_non_empty,
        "flex": last_non_empty,
        "status": last_non_empty,
        "link_anuncio": last_non_empty,
    }
    grouped = base.groupby("item_id", as_index=False).agg(aggregations)

    params = pd.DataFrame(index=grouped.index)
    params["item_id"] = grouped["item_id"]
    params["sku"] = grouped["sku"]
    params["produto"] = grouped["produto"]
    params["marca"] = grouped["marca"]
    params["categoria"] = grouped["categoria"]
    params["preco_venda_seconds"] = grouped["preco_venda_seconds"]
    params["cmv_unitario_seconds"] = unit_from_total_or_fallback(
        grouped,
        "cmv_seconds",
        "cmv_seconds_unitario",
    )
    params["comissao_unitaria_seconds"] = unit_from_total_or_fallback(
        grouped,
        "comissao_seconds",
        "comissao_seconds_unitario",
    )
    params["frete_unitario_seconds"] = unit_from_total_or_fallback(
        grouped,
        "frete_seconds",
        "frete_seconds_unitario",
    )
    params["custo_fixo_unitario_seconds"] = unit_from_total_or_fallback(
        grouped,
        "custo_fixo_seconds",
        "custo_fixo_seconds_unitario",
    )
    params["imposto_unitario_seconds"] = unit_from_total_or_fallback(
        grouped,
        "imposto_seconds",
        "imposto_seconds_unitario",
    )
    params["lucro_liquido_unitario_seconds"] = unit_from_total_or_fallback(
        grouped,
        "lucro_liquido_seconds",
        "lucro_liquido_seconds_unitario",
    )
    params["margem_seconds"] = grouped["margem_seconds"]
    params["full"] = grouped["full"]
    params["flex"] = grouped["flex"]
    params["status"] = grouped["status"]
    params["link_anuncio"] = grouped["link_anuncio"]
    params["parametro_confiavel"] = (
        (grouped["vendidos"] > 0)
        & (params["cmv_unitario_seconds"] > 0)
    )

    return params[OUTPUT_COLUMNS].drop_duplicates(subset=["item_id"], keep="last")


def format_percent(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def print_summary(df: pd.DataFrame) -> None:
    total_itens = len(df)
    confiaveis = int(df["parametro_confiavel"].sum()) if total_itens else 0
    sem_confiavel = total_itens - confiaveis
    margem_media = float(df["margem_seconds"].mean()) if total_itens else 0.0
    marcas = int(df.loc[df["marca"] != "", "marca"].nunique()) if total_itens else 0
    categorias = int(df.loc[df["categoria"] != "", "categoria"].nunique()) if total_itens else 0

    print("=" * 80)
    print("RESUMO PARAMETROS FINANCEIROS SECONDS")
    print("=" * 80)
    print(f"Total itens: {total_itens}")
    print(f"Itens com parametro confiavel: {confiaveis}")
    print(f"Itens sem parametro confiavel: {sem_confiavel}")
    print(f"Margem media: {format_percent(margem_media)}")
    print(f"Marcas: {marcas}")
    print(f"Categorias: {categorias}")


def save_output(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    source = read_seconds_base(INPUT_PATH)
    parameters = build_parameters(source)
    save_output(parameters, OUTPUT_PATH)
    print_summary(parameters)
    print(f"\nCSV salvo em: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
