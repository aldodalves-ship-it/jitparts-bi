"""Analisa colunas numericas do arquivo data/ml_shipments.csv.

Objetivo:
Descobrir quais colunas possuem valores de frete/custo logistico diferentes de
zero e gerar um relatorio textual para orientar o merge financeiro.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data") / "ml_shipments.csv"
OUTPUT_PATH = Path("data") / "relatorio_shipments_colunas.txt"

COST_KEYWORDS = [
    "cost",
    "custo",
    "frete",
    "shipping",
    "sender",
    "receiver",
    "list",
    "option",
]


def parse_possible_number(value: object) -> float | None:
    """Converte valores numericos ou textos monetarios para float."""

    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = (
        text.replace("R$", "")
        .replace("%", "")
        .replace("\u00a0", "")
        .replace(" ", "")
    )
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None

    if "," in text and "." in text and text.rfind(",") > text.rfind("."):
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    elif "," in text and "." in text and text.rfind(".") > text.rfind(","):
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def as_numeric_series(series: pd.Series) -> pd.Series:
    """Converte uma coluna para numerico, tolerando texto."""

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    converted = series.map(parse_possible_number)
    numeric = pd.to_numeric(converted, errors="coerce")

    # Evita classificar IDs puros como metricas quando quase tudo e texto/ID.
    return numeric


def is_candidate_cost_column(column: str) -> bool:
    """Marca nomes provaveis de custo/frete."""

    normalized = column.lower().replace("_", " ")
    return any(keyword in normalized for keyword in COST_KEYWORDS)


def analyze_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Gera estatisticas por coluna numerica/conversivel."""

    rows = []
    examples: dict[str, pd.DataFrame] = {}

    for column in df.columns:
        numeric = as_numeric_series(df[column])
        non_null_count = int(numeric.notna().sum())
        positive_count = int((numeric > 0).sum())

        if non_null_count == 0:
            continue

        rows.append(
            {
                "coluna": column,
                "soma": float(numeric.sum(skipna=True)),
                "media": float(numeric.mean(skipna=True)),
                "nao_nulos": non_null_count,
                "maiores_que_zero": positive_count,
                "candidata_custo": is_candidate_cost_column(column),
            }
        )

        if positive_count > 0:
            example_df = df.loc[numeric > 0].copy().head(8)
            example_df.insert(0, f"{column}_valor_numerico", numeric.loc[numeric > 0].head(8).values)
            examples[column] = example_df

    summary = pd.DataFrame(rows).sort_values(
        ["candidata_custo", "maiores_que_zero", "soma"],
        ascending=[False, False, False],
    )
    return summary, examples


def build_report(df: pd.DataFrame, summary: pd.DataFrame, examples: dict[str, pd.DataFrame]) -> str:
    """Monta o relatorio em texto."""

    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("RELATORIO DE COLUNAS - ML SHIPMENTS")
    lines.append("=" * 100)
    lines.append(f"Arquivo analisado: {INPUT_PATH}")
    lines.append(f"Total de linhas: {len(df)}")
    lines.append(f"Total de colunas: {len(df.columns)}")
    lines.append("")
    lines.append("COLUNAS ENCONTRADAS")
    lines.append("-" * 100)
    for column in df.columns:
        lines.append(f"- {column}")

    lines.append("")
    lines.append("RESUMO NUMERICO / CONVERSIVEL")
    lines.append("-" * 100)
    if summary.empty:
        lines.append("Nenhuma coluna numerica/conversivel encontrada.")
    else:
        lines.append(summary.to_string(index=False))

    candidates = summary[
        (summary["candidata_custo"])
        & (summary["maiores_que_zero"] > 0)
    ] if not summary.empty else pd.DataFrame()

    lines.append("")
    lines.append("POSSIVEIS COLUNAS CANDIDATAS A CUSTO DE FRETE")
    lines.append("-" * 100)
    if candidates.empty:
        lines.append("Nenhuma candidata de custo/frete com valor maior que zero foi encontrada.")
    else:
        lines.append(candidates.to_string(index=False))

    lines.append("")
    lines.append("EXEMPLOS DE LINHAS COM VALORES MAIORES QUE ZERO")
    lines.append("-" * 100)
    for column, example_df in examples.items():
        if column not in summary["coluna"].values:
            continue
        row = summary[summary["coluna"] == column].iloc[0]
        if not bool(row["candidata_custo"]) and row["maiores_que_zero"] == 0:
            continue
        lines.append("")
        lines.append(f"COLUNA: {column}")
        lines.append(example_df.to_string(index=False))

    return "\n".join(lines)


def main() -> None:
    """Executa a analise e salva o relatorio."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    summary, examples = analyze_columns(df)
    report = build_report(df, summary, examples)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nRelatorio salvo em: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
