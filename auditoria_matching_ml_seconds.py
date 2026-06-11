"""AUDITORIA 4 — CORRESPONDÊNCIA ML × SECONDS (MATCHING INTELIGENTE)

Objetivo: Identificar por que os itens classificados como SEM_MATCH_SECONDS não estão
sendo encontrados na Seconds e recuperar automaticamente o máximo possível da cobertura CMV.

IMPORTANTE: Somente leitura e simulação. Não altera app.py, base final, DRE ou regras financeiras.

Saídas:
    resultado/matching_inteligente_seconds.csv
    AUDITORIA_MATCHING_ML_SECONDS.md
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Dependência opcional: rapidfuzz (mais rápida que python-Levenshtein/fuzzywuzzy)
# Fallback para difflib se não estiver instalada.
# ---------------------------------------------------------------------------
try:
    from rapidfuzz import fuzz as _fuzz
    from rapidfuzz import process as _process

    def ratio(a: str, b: str) -> float:
        return _fuzz.ratio(a, b)

    def partial_ratio(a: str, b: str) -> float:
        return _fuzz.partial_ratio(a, b)

    def token_sort_ratio(a: str, b: str) -> float:
        return _fuzz.token_sort_ratio(a, b)

    def token_set_ratio(a: str, b: str) -> float:
        return _fuzz.token_set_ratio(a, b)

    FUZZY_ENGINE = "rapidfuzz"

except ImportError:
    try:
        from fuzzywuzzy import fuzz as _fw_fuzz  # type: ignore

        def ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.ratio(a, b))

        def partial_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.partial_ratio(a, b))

        def token_sort_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.token_sort_ratio(a, b))

        def token_set_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.token_set_ratio(a, b))

        FUZZY_ENGINE = "fuzzywuzzy"

    except ImportError:
        import difflib

        def ratio(a: str, b: str) -> float:
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

        def partial_ratio(a: str, b: str) -> float:
            if len(b) == 0:
                return 0.0
            best = 0.0
            len_a = len(a)
            for start in range(len(b) - len_a + 1):
                sub = b[start : start + len_a]
                s = difflib.SequenceMatcher(None, a, sub).ratio() * 100
                if s > best:
                    best = s
            return best if len_a <= len(b) else ratio(a, b)

        def token_sort_ratio(a: str, b: str) -> float:
            return ratio(" ".join(sorted(a.split())), " ".join(sorted(b.split())))

        def token_set_ratio(a: str, b: str) -> float:
            set_a = set(a.split())
            set_b = set(b.split())
            inter = " ".join(sorted(set_a & set_b))
            only_a = " ".join(sorted(set_a - set_b))
            only_b = " ".join(sorted(set_b - set_a))
            t0 = inter
            t1 = (inter + " " + only_a).strip()
            t2 = (inter + " " + only_b).strip()
            return max(ratio(t0, t1), ratio(t0, t2), ratio(t1, t2))

        FUZZY_ENGINE = "difflib (fallback)"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULT_DIR = BASE_DIR / "resultado"

SEM_CMV_PATH = RESULT_DIR / "itens_sem_cmv_completo.csv"
SECONDS_PATH = DATA_DIR / "base_seconds_principal.csv"
OUTPUT_CSV = RESULT_DIR / "matching_inteligente_seconds.csv"
OUTPUT_MD = BASE_DIR / "AUDITORIA_MATCHING_ML_SECONDS.md"


# ---------------------------------------------------------------------------
# Palavras comuns removidas na normalização (stop words automotivas PT-BR)
# ---------------------------------------------------------------------------
STOP_WORDS = {
    "para", "com", "sem", "de", "do", "da", "dos", "das", "e", "em", "a",
    "o", "os", "as", "um", "uma", "no", "na", "por", "ate", "entre",
    "original", "novo", "nova", "kit", "jogo", "par", "jg", "conjunto",
    "completo", "completa", "todos", "todas", "modelo", "modelos",
    "motor", "dianteiro", "dianteira", "traseiro", "traseira",
    "freio", "freios", "pastilha", "disco", "tambor",
    "flex", "gasolina", "diesel", "turbo", "aspirado",
    "std", "oem", "original", "genuino", "genuina",
    "universal", "compativel", "compativel", "todos",
}


def normalize(text: object) -> str:
    """Normaliza texto para matching: minúsculas, sem acento, sem especiais, sem stop words."""
    if pd.isna(text) or str(text).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(text).strip().lower()
    # remove acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # remove caracteres especiais (mantém letras, números, espaço)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # normaliza espaços múltiplos
    s = re.sub(r"\s+", " ", s).strip()
    # remove stop words
    tokens = [t for t in s.split() if t not in STOP_WORDS and len(t) > 1]
    return " ".join(tokens)


def normalize_sku(sku: object) -> str:
    """Normaliza SKU: maiúsculas, sem espaço, sem hífen/ponto."""
    if pd.isna(sku) or str(sku).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(sku).strip().upper()
    s = re.sub(r"[\s\-\./]", "", s)
    return s


def best_score(query: str, candidate: str) -> float:
    """Score máximo entre 4 métodos de similaridade."""
    if not query or not candidate:
        return 0.0
    scores = [
        ratio(query, candidate),
        partial_ratio(query, candidate),
        token_sort_ratio(query, candidate),
        token_set_ratio(query, candidate),
    ]
    return max(scores)


def classify_match(score: float) -> str:
    if score >= 90:
        return "MATCH_AUTOMATICO"
    if score >= 75:
        return "MATCH_PROVAVEL"
    if score >= 60:
        return "MATCH_DUVIDOSO"
    return "SEM_CORRESPONDENCIA"


def identify_error_pattern(ml_produto: str, sec_produto: str, ml_sku: str, sec_sku: str) -> str:
    """Tenta identificar o padrão de erro entre os dois descritores."""
    patterns = []

    # SKU: diferenças de hífen/espaço/prefixo
    if ml_sku and sec_sku:
        if ml_sku != sec_sku:
            if re.sub(r"[\s\-\./]", "", ml_sku.upper()) == re.sub(r"[\s\-\./]", "", sec_sku.upper()):
                patterns.append("sku_formatacao")
            elif ml_sku.upper().lstrip("0") == sec_sku.upper().lstrip("0"):
                patterns.append("sku_zeros_extras")
            elif ml_sku.upper() in sec_sku.upper() or sec_sku.upper() in ml_sku.upper():
                patterns.append("sku_prefixo_sufixo")
            else:
                patterns.append("sku_divergente")
    elif not ml_sku:
        patterns.append("sku_ausente_ml")
    elif not sec_sku:
        patterns.append("sku_ausente_seconds")

    # Produto: palavras extras / invertidas
    if ml_produto and sec_produto:
        ml_tokens = set(normalize(ml_produto).split())
        sec_tokens = set(normalize(sec_produto).split())
        if ml_tokens == sec_tokens:
            patterns.append("nomenclatura_invertida")
        elif len(ml_tokens - sec_tokens) > 2:
            patterns.append("palavras_extras_ml")
        elif len(sec_tokens - ml_tokens) > 2:
            patterns.append("palavras_extras_seconds")

    return "; ".join(patterns) if patterns else "sem_padrao_claro"


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float) -> str:
    return f"{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sem registros._"
    df2 = df.copy().fillna("").astype(str)
    headers = list(df2.columns)
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df2.iterrows():
        cells = [str(row[h]).replace("|", "\\|").replace("\n", " ").strip() or " " for h in headers]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ====================================================================