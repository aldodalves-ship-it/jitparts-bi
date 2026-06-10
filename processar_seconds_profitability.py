"""Processa a exportacao Profitability da Seconds.

Entrada:
    data/seconds/ReportProfitability.xlsx

Saida:
    data/base_seconds_principal.csv
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd


INPUT_PATH = Path("data/seconds/ReportProfitability.xlsx")
OUTPUT_PATH = Path("data/base_seconds_principal.csv")

TEXT_COLUMNS = {
    "item_id",
    "sku",
    "produto",
    "marca",
    "categoria",
    "status",
    "full",
    "flex",
    "link_anuncio",
    "exposicao",
    "catalogo",
}
FLAG_COLUMNS = {"full", "flex", "catalogo"}
NUMERIC_COLUMNS = {
    "preco_venda_seconds",
    "comissao_seconds",
    "frete_seconds",
    "cmv_seconds",
    "custo_fixo_seconds",
    "imposto_seconds",
    "lucro_bruto_seconds",
    "lucro_liquido_seconds",
    "margem_seconds",
    "faturamento_seconds",
    "vendidos",
}
UNIT_FINANCIAL_COLUMNS = {
    "comissao_seconds",
    "frete_seconds",
    "cmv_seconds",
    "custo_fixo_seconds",
    "imposto_seconds",
    "lucro_bruto_seconds",
    "lucro_liquido_seconds",
}

COLUMN_MAP = {
    "item_id": ["Codigo do Anuncio", "Codigo Anuncio", "MLB"],
    "sku": ["SKU"],
    "produto": ["Seu Anuncio", "Anuncio", "Produto"],
    "marca": ["Marca"],
    "categoria": ["Nome da Categoria", "Categoria"],
    "preco_venda_seconds": ["Preco da Venda", "Preco Venda"],
    "comissao_seconds": ["Comissao"],
    "frete_seconds": ["Frete Gratis voce paga os custos", "Frete Gratis"],
    "cmv_seconds": ["Custo da Mercadoria Vendida", "CMV"],
    "custo_fixo_seconds": ["Custo Fixo"],
    "imposto_seconds": ["Imposto"],
    "lucro_bruto_seconds": ["Lucro Bruto"],
    "lucro_liquido_seconds": ["Lucro Liquido"],
    "margem_seconds": ["% Lucratividade", "Lucratividade", "Margem"],
    "faturamento_seconds": ["Total_Faturado", "Total Faturado", "Faturamento"],
    "status": ["Status"],
    "full": ["FULL", "Full"],
    "flex": ["Flex"],
    "link_anuncio": ["LinkAnuncio", "Link Anuncio", "Link do Anuncio"],
    "exposicao": ["Exposicao"],
    "vendidos": ["Vendidos"],
    "catalogo": ["Catalogo"],
}

OUTPUT_COLUMNS = list(COLUMN_MAP)
UNIT_OUTPUT_COLUMNS = [f"{column}_unitario" for column in UNIT_FINANCIAL_COLUMNS]


def normalize_column_name(column: object) -> str:
    """Normaliza nomes de colunas para comparacao tolerante."""

    text = str(column).strip().lower().replace("\ufeff", "").replace("\ufffd", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def to_snake_case(column: object) -> str:
    """Converte uma string para snake_case ASCII."""

    text = normalize_column_name(column)
    return text.replace(" ", "_")


def find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Busca coluna por aliases, com fallback fuzzy para cabecalhos corrompidos."""

    normalized_columns = {
        normalize_column_name(column): str(column)
        for column in df.columns
    }

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)
        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    best_column: str | None = None
    best_score = 0.0
    for alias in aliases:
        normalized_alias = normalize_column_name(alias)
        if len(normalized_alias) < 6:
            continue

        for normalized_column, original_column in normalized_columns.items():
            score = SequenceMatcher(None, normalized_alias, normalized_column).ratio()
            if score > best_score:
                best_score = score
                best_column = original_column

    return best_column if best_score >= 0.86 else None


def get_optional_series(df: pd.DataFrame, aliases: list[str], default: Any = pd.NA) -> pd.Series:
    """Retorna a coluna encontrada ou uma serie default."""

    column = find_column(df, aliases)
    if column is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[column]


def parse_br_number(value: object) -> float:
    """Converte numero brasileiro, moeda ou percentual para float."""

    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    is_negative_parentheses = text.startswith("(") and text.endswith(")")
    text = (
        text.replace("R$", "")
        .replace("%", "")
        .replace("\u00a0", "")
        .replace(" ", "")
    )
    text = re.sub(r"[^0-9,.\-]", "", text)

    if not text or text in {"-", ".", ","}:
        return 0.0

    if "," in text and "." in text and text.rfind(",") > text.rfind("."):
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    elif "," in text and "." in text and text.rfind(".") > text.rfind(","):
        text = text.replace(",", "")

    try:
        number = float(text)
    except ValueError:
        return 0.0

    return -abs(number) if is_negative_parentheses else number


def standardize_mlb(value: object) -> str:
    """Padroniza item_id no formato MLB123."""

    if pd.isna(value):
        return ""

    text = str(value).strip().upper()
    if not text:
        return ""

    text = re.sub(r"\.0$", "", text)
    match = re.search(r"MLB\s*-?\s*(\d+)", text)
    if match:
        return f"MLB{match.group(1)}"

    digits = re.sub(r"\D", "", text)
    if digits:
        return f"MLB{digits}"

    return text


def clean_text(value: object) -> str:
    """Limpa textos e trata valores vazios."""

    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text


def clean_flag(value: object) -> str:
    """Padroniza indicadores textuais de sim/nao."""

    text = clean_text(value)
    normalized = normalize_column_name(text)
    if normalized in {"sim", "s", "yes", "y", "true", "1"}:
        return "SIM"
    if normalized in {"nao", "n", "no", "false", "0"}:
        return "NAO"
    return text


def read_profitability(path: Path) -> pd.DataFrame:
    """Le a planilha usando openpyxl."""

    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_excel(path, engine="openpyxl")


def build_clean_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia, normaliza e reduz a planilha Seconds."""

    clean_df = pd.DataFrame(index=raw_df.index)

    missing_required: list[str] = []
    for output_column, aliases in COLUMN_MAP.items():
        source_column = find_column(raw_df, aliases)
        if source_column is None and output_column == "item_id":
            missing_required.append(output_column)

        clean_df[output_column] = get_optional_series(raw_df, aliases)

    if missing_required:
        raise ValueError(
            "Colunas obrigatorias nao encontradas: "
            f"{missing_required}. Colunas da planilha: {list(raw_df.columns)}"
        )

    clean_df["item_id"] = clean_df["item_id"].map(standardize_mlb)

    for column in TEXT_COLUMNS - {"item_id"}:
        clean_df[column] = clean_df[column].map(clean_text)

    for column in FLAG_COLUMNS:
        clean_df[column] = clean_df[column].map(clean_flag)

    for column in NUMERIC_COLUMNS:
        clean_df[column] = clean_df[column].map(parse_br_number)

    vendidos = clean_df["vendidos"].fillna(0)
    total_faturado = clean_df["faturamento_seconds"].fillna(0)
    preco_venda = clean_df["preco_venda_seconds"].fillna(0)

    clean_df["faturamento_seconds"] = total_faturado.where(
        total_faturado > 0,
        preco_venda * vendidos,
    )

    for column in UNIT_FINANCIAL_COLUMNS:
        clean_df[f"{column}_unitario"] = clean_df[column]
        clean_df[column] = clean_df[column].fillna(0) * vendidos

    clean_df["margem_seconds"] = clean_df.apply(
        lambda row: (
            (row["lucro_liquido_seconds"] / row["faturamento_seconds"]) * 100
            if row["faturamento_seconds"]
            else 0.0
        ),
        axis=1,
    )

    clean_df = clean_df[clean_df["item_id"] != ""].copy()
    clean_df.columns = [to_snake_case(column) for column in clean_df.columns]
    return clean_df[OUTPUT_COLUMNS + UNIT_OUTPUT_COLUMNS].reset_index(drop=True)


def format_brl(value: float) -> str:
    """Formata float como moeda brasileira para o resumo."""

    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def print_summary(df: pd.DataFrame) -> None:
    """Exibe resumo da base processada."""

    total_linhas = len(df)
    anuncios_unicos = int(df["item_id"].nunique()) if total_linhas else 0
    faturamento_total = float(df["faturamento_seconds"].sum()) if total_linhas else 0.0
    lucro_liquido_total = float(df["lucro_liquido_seconds"].sum()) if total_linhas else 0.0
    cmv_total = float(df["cmv_seconds"].sum()) if total_linhas else 0.0
    frete_total = float(df["frete_seconds"].sum()) if total_linhas else 0.0
    imposto_total = float(df["imposto_seconds"].sum()) if total_linhas else 0.0
    margem_media = (lucro_liquido_total / faturamento_total * 100) if faturamento_total else 0.0
    total_marcas = int(df.loc[df["marca"] != "", "marca"].nunique()) if total_linhas else 0
    total_categorias = int(df.loc[df["categoria"] != "", "categoria"].nunique()) if total_linhas else 0

    print("=" * 80)
    print("RESUMO BASE SECONDS PROFITABILITY")
    print("=" * 80)
    print(f"Total linhas: {total_linhas}")
    print(f"Anuncios unicos: {anuncios_unicos}")
    print(f"Faturamento total: {format_brl(faturamento_total)}")
    print(f"CMV total: {format_brl(cmv_total)}")
    print(f"Frete total: {format_brl(frete_total)}")
    print(f"Imposto total: {format_brl(imposto_total)}")
    print(f"Lucro liquido total: {format_brl(lucro_liquido_total)}")
    print(f"Margem media: {margem_media:.2f}%".replace(".", ","))
    print(f"Total marcas: {total_marcas}")
    print(f"Total categorias: {total_categorias}")


def save_output(df: pd.DataFrame, path: Path) -> None:
    """Salva a base limpa em CSV utf-8-sig."""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    """Executa o processamento completo."""

    raw_df = read_profitability(INPUT_PATH)
    clean_df = build_clean_dataframe(raw_df)
    save_output(clean_df, OUTPUT_PATH)
    print_summary(clean_df)
    print(f"\nCSV salvo em: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
