"""Gera a base final do dashboard no modelo hibrido ML + Seconds.

Modelo:
    - Mercado Livre e a base temporal/transacional, uma linha por venda/item/pedido.
    - Seconds enriquece parametros financeiros unitarios por item_id.

Entradas:
    data/ml_orders.csv
    data/ml_shipments.csv
    data/parametros_financeiros_seconds.csv
    data/ml_items_details.csv  (opcional)

Saida:
    data/dashboard_base_final.csv

Pipeline de match (4 etapas — sem alterar calculos financeiros):
    ETAPA 1 — MATCH_EXACT           : merge direto por item_id (comportamento original)
    ETAPA 2 — FUZZY_AUTO            : score >= 85, CMV aplicado
    ETAPA 3 — FUZZY_AUTO_CONTROLLED : score 80-84 + filtros de segurança, CMV aplicado
    ETAPA 4 — MATCH_PROVAVEL        : score 75-79, apenas marcado, CMV nao aplicado
    ETAPA 5 — SEM_MATCH             : sem correspondencia viavel
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Dependencia opcional: rapidfuzz (preferencial) com fallback para difflib
# ---------------------------------------------------------------------------
try:
    from rapidfuzz import fuzz as _fuzz

    def _token_set_ratio(a: str, b: str) -> float:
        return _fuzz.token_set_ratio(a, b)

    def _token_sort_ratio(a: str, b: str) -> float:
        return _fuzz.token_sort_ratio(a, b)

    def _partial_ratio(a: str, b: str) -> float:
        return _fuzz.partial_ratio(a, b)

    FUZZY_ENGINE = "rapidfuzz"
except ImportError:
    import difflib

    def _token_set_ratio(a: str, b: str) -> float:  # type: ignore[misc]
        set_a = set(a.split())
        set_b = set(b.split())
        inter = " ".join(sorted(set_a & set_b))
        t1 = (inter + " " + " ".join(sorted(set_a - set_b))).strip()
        t2 = (inter + " " + " ".join(sorted(set_b - set_a))).strip()
        return max(
            difflib.SequenceMatcher(None, inter, t1).ratio(),
            difflib.SequenceMatcher(None, inter, t2).ratio(),
            difflib.SequenceMatcher(None, t1, t2).ratio(),
        ) * 100

    def _token_sort_ratio(a: str, b: str) -> float:  # type: ignore[misc]
        sa = " ".join(sorted(a.split()))
        sb = " ".join(sorted(b.split()))
        return difflib.SequenceMatcher(None, sa, sb).ratio() * 100

    def _partial_ratio(a: str, b: str) -> float:  # type: ignore[misc]
        return difflib.SequenceMatcher(None, a, b).ratio() * 100

    FUZZY_ENGINE = "difflib (fallback)"

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
FUZZY_AUTO_THRESHOLD = 85           # score >= 85: FUZZY_AUTO — CMV aplicado
FUZZY_CONTROLLED_THRESHOLD = 80     # score 80-84: FUZZY_AUTO_CONTROLLED se passar filtros
FUZZY_PROVAVEL_THRESHOLD = 75       # score 75-79: MATCH_PROVAVEL — apenas marcado
# Diferenca minima entre top1 e top2 para evitar ambiguidade
FUZZY_MIN_GAP_CONTROLLED = 5.0
# Minimo de palavras tecnicas em comum para Camada Controlada
FUZZY_MIN_SHARED_KEYWORDS = 2
# Limite de diferenca de comprimento de nome (fração)
FUZZY_MAX_LENGTH_DIFF = 0.30

# Palavras tecnicas automotivas que validam similaridade semantica real
_TECHNICAL_KEYWORDS = frozenset({
    "pastilha", "pastilhas", "disco", "discos", "tambor", "tambores",
    "freio", "freios", "filtro", "filtros", "amortecedor", "amortecedores",
    "mola", "molas", "junta", "juntas", "pistao", "pistoes", "anel", "aneis",
    "bronzina", "bronzinas", "valvula", "valvulas", "bomba", "bombas",
    "correia", "correias", "tensor", "tensores", "rolamento", "rolamentos",
    "cubo", "cubos", "coxim", "coxins", "barra", "barras", "terminal",
    "terminais", "pivô", "pivo", "pivos", "bandeja", "bandejas",
    "caliper", "calipers", "manga", "mangueira", "mangueiras",
    "radiador", "radiadores", "condensador", "condensadores",
    "compressor", "compressores", "alternador", "alternadores",
    "vela", "velas", "bobina", "bobinas", "modulo", "injetor", "injetores",
    "polia", "polias", "corrente", "kit", "jogo", "par",
    "cabeçote", "cabecote", "carter", "bloco", "biela", "bielas",
    "virabrequim", "comando", "balancim", "balancins",
    "engate", "reboque", "rabicho", "ponteira",
})

# Stop-words removidas na normalizacao
_FUZZY_STOP_WORDS = frozenset({
    "para", "com", "sem", "de", "do", "da", "dos", "das", "e", "em",
    "a", "o", "os", "as", "um", "uma", "no", "na", "por", "ate",
    "original", "novo", "nova", "flex", "gasolina", "diesel",
    "todos", "todas", "modelo", "modelos", "genuino", "genuina",
    "universal", "compativel",
})

# ---------------------------------------------------------------------------
# Paths e constantes
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")
ML_ORDERS_PATH = DATA_DIR / "ml_orders.csv"
ML_SHIPMENTS_PATH = DATA_DIR / "ml_shipments.csv"
PARAMETERS_PATH = DATA_DIR / "parametros_financeiros_seconds.csv"
ML_ITEMS_DETAILS_PATH = DATA_DIR / "ml_items_details.csv"
OUTPUT_PATH = DATA_DIR / "dashboard_base_final.csv"

PARAM_OK = "parametro_seconds_confiavel"
PARAM_MISSING = "sem_parametro_seconds"

# Valores sentinel de match_type
MATCH_TYPE_EXACT = "EXACT"
MATCH_TYPE_FUZZY_AUTO = "FUZZY_AUTO"
MATCH_TYPE_FUZZY_CONTROLLED = "FUZZY_AUTO_CONTROLLED"
MATCH_TYPE_FUZZY_PROVAVEL = "MATCH_PROVAVEL"
MATCH_TYPE_SEM_MATCH = "SEM_MATCH"

# Niveis de confianca
CONFIDENCE_ALTA = "ALTA"
CONFIDENCE_MEDIA = "MEDIA"
CONFIDENCE_BAIXA = "BAIXA"

# CMV eh aplicado para estes tipos de match
_MATCH_TYPES_APPLY_CMV = {MATCH_TYPE_EXACT, MATCH_TYPE_FUZZY_AUTO, MATCH_TYPE_FUZZY_CONTROLLED}

# ---------------------------------------------------------------------------
# Funcoes utilitarias basicas
# ---------------------------------------------------------------------------

def standardize_mlb(value: object) -> str:
    """Padroniza IDs de anuncio no formato MLB123."""
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


def standardize_id(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\.0$", "", str(value).strip())


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text


def coalesce(primary: pd.Series, fallback: pd.Series) -> pd.Series:
    primary_text = primary.astype("string").str.strip()
    return primary.where(primary.notna() & primary_text.ne(""), fallback)


def parse_number(value: object) -> float:
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
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
        return float(text)
    except ValueError:
        return 0.0


def format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Normalizacao de texto para matching fuzzy
# ---------------------------------------------------------------------------

def _normalize_text(value: object) -> str:
    """Normaliza texto: minusculas, sem acento, sem especiais, sem stop-words."""
    if pd.isna(value) or str(value).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [t for t in s.split() if t not in _FUZZY_STOP_WORDS and len(t) > 1]
    return " ".join(tokens)


def _normalize_brand(value: object) -> str:
    """Normaliza marca para comparacao."""
    if pd.isna(value) or str(value).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def _best_fuzzy_score(query: str, candidate: str) -> float:
    """Score maximo entre token_set_ratio e token_sort_ratio."""
    if not query or not candidate:
        return 0.0
    return max(_token_set_ratio(query, candidate), _token_sort_ratio(query, candidate))


# ---------------------------------------------------------------------------
# Filtros de segurança para Camada Controlada (FUZZY_AUTO_CONTROLLED)
# ---------------------------------------------------------------------------

def _shared_technical_keywords(norm_a: str, norm_b: str) -> int:
    """Conta palavras tecnicas em comum entre dois textos normalizados."""
    tokens_a = set(norm_a.split()) & _TECHNICAL_KEYWORDS
    tokens_b = set(norm_b.split()) & _TECHNICAL_KEYWORDS
    return len(tokens_a & tokens_b)


def _length_diff_ratio(a: str, b: str) -> float:
    """Diferenca relativa de comprimento entre dois strings."""
    la, lb = len(a), len(b)
    if la == 0 and lb == 0:
        return 0.0
    return abs(la - lb) / max(la, lb)


def _brands_match(brand_ml: str, brand_sec: str) -> bool:
    """Verifica se as marcas sao compativeis (ambas vazias = inconclusivo, nao bloqueia)."""
    bml = _normalize_brand(brand_ml)
    bsec = _normalize_brand(brand_sec)
    # Se pelo menos uma esta vazia, nao ha conflito confirmado
    if not bml or not bsec:
        return True
    return bml == bsec


def _passes_controlled_filters(
    norm_ml: str,
    norm_sec: str,
    brand_ml: str,
    brand_sec: str,
    score: float,
    gap_to_second: float,
) -> tuple[bool, str]:
    """Avalia se o match passa todos os critérios de segurança para Camada Controlada.

    Retorna (passou, motivo_rejeicao).
    Criterios obrigatorios:
        1. score >= FUZZY_CONTROLLED_THRESHOLD  (ja garantido pelo chamador)
        2. pelo menos FUZZY_MIN_SHARED_KEYWORDS palavras tecnicas em comum
        3. diferenca de comprimento <= FUZZY_MAX_LENGTH_DIFF
        4. marcas compativeis (nao conflitantes)
        5. gap entre top1 e top2 >= FUZZY_MIN_GAP_CONTROLLED
    """
    # Criterio 2: palavras tecnicas em comum
    shared = _shared_technical_keywords(norm_ml, norm_sec)
    if shared < FUZZY_MIN_SHARED_KEYWORDS:
        return False, f"keywords_insuficientes({shared}<{FUZZY_MIN_SHARED_KEYWORDS})"

    # Criterio 3: comprimento similar
    diff = _length_diff_ratio(norm_ml, norm_sec)
    if diff > FUZZY_MAX_LENGTH_DIFF:
        return False, f"comprimento_diferente({diff:.0%}>{FUZZY_MAX_LENGTH_DIFF:.0%})"

    # Criterio 4: marca nao conflitante
    if not _brands_match(brand_ml, brand_sec):
        return False, "marca_conflitante"

    # Criterio 5: gap de ambiguidade
    if gap_to_second < FUZZY_MIN_GAP_CONTROLLED:
        return False, f"gap_insuficiente({gap_to_second:.1f}<{FUZZY_MIN_GAP_CONTROLLED})"

    return True, ""


def _assign_confidence(match_type: str, score: float, passed_brand: bool) -> str:
    """Atribui nivel de confiança ao match."""
    if match_type == MATCH_TYPE_EXACT:
        return CONFIDENCE_ALTA
    if match_type == MATCH_TYPE_FUZZY_AUTO and score >= 92:
        return CONFIDENCE_ALTA
    if match_type == MATCH_TYPE_FUZZY_AUTO:
        return CONFIDENCE_MEDIA
    if match_type == MATCH_TYPE_FUZZY_CONTROLLED and passed_brand:
        return CONFIDENCE_MEDIA
    if match_type == MATCH_TYPE_FUZZY_CONTROLLED:
        return CONFIDENCE_MEDIA
    return CONFIDENCE_BAIXA


# ---------------------------------------------------------------------------
# Pipeline de matching (Etapas 2-5)
# ---------------------------------------------------------------------------

def _build_fuzzy_lookup(
    params: pd.DataFrame,
) -> tuple[list[str], list[str], list[str]]:
    """Pre-computa ids, textos normalizados e marcas normalizadas da base Seconds."""
    ids = params["item_id"].tolist()
    norms = params["produto"].apply(_normalize_text).tolist()
    brands = params["marca"].apply(_normalize_brand).tolist() if "marca" in params.columns else [""] * len(params)
    return ids, norms, brands


def _fuzzy_match_items(
    unmatched_item_ids: list[str],
    item_name_map: dict[str, str],
    item_brand_map: dict[str, str],
    sec_ids: list[str],
    sec_norms: list[str],
    sec_brands: list[str],
    params: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, float], dict[str, str], dict[str, str]]:
    """Para cada item_id sem match, busca o melhor candidato na base Seconds.

    Pipeline por item:
        - Calcula score para todos os candidatos Seconds
        - top1: melhor score; top2: segundo melhor
        - gap = top1_score - top2_score (usado no filtro de ambiguidade)
        - Classifica em FUZZY_AUTO, FUZZY_AUTO_CONTROLLED, MATCH_PROVAVEL ou SEM_MATCH

    Retorna:
        fuzzy_params_map   : {item_id -> dict de params}
        fuzzy_score_map    : {item_id -> float}
        fuzzy_type_map     : {item_id -> str}
        fuzzy_confidence_map: {item_id -> str}
    """
    fuzzy_params_map: dict[str, Any] = {}
    fuzzy_score_map: dict[str, float] = {}
    fuzzy_type_map: dict[str, str] = {}
    fuzzy_confidence_map: dict[str, str] = {}

    params_records = params.set_index("item_id").to_dict("index")
    # Reinjeta item_id como campo dentro de cada registro para facilitar rastreabilidade
    for pid, rec in params_records.items():
        rec["item_id"] = pid
    n_sec = len(sec_norms)

    for item_id in unmatched_item_ids:
        produto_ml = item_name_map.get(item_id, "")
        brand_ml = item_brand_map.get(item_id, "")
        norm_ml = _normalize_text(produto_ml)

        # Calcular scores para todos os candidatos
        scores: list[float] = []
        for norm_sec in sec_norms:
            sc = _best_fuzzy_score(norm_ml, norm_sec)
            scores.append(sc)

        # Identificar top1 e top2
        if not scores:
            fuzzy_params_map[item_id] = {}
            fuzzy_score_map[item_id] = 0.0
            fuzzy_type_map[item_id] = MATCH_TYPE_SEM_MATCH
            fuzzy_confidence_map[item_id] = CONFIDENCE_BAIXA
            continue

        sorted_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        best_idx, best_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
        gap = best_score - second_score

        fuzzy_score_map[item_id] = round(best_score, 2)
        matched_id = sec_ids[best_idx]
        row_params = params_records.get(matched_id, {})
        brand_sec = sec_brands[best_idx] if best_idx < len(sec_brands) else ""
        norm_sec = sec_norms[best_idx]

        # --- Etapa 2: FUZZY_AUTO (score >= 85) ---
        if best_score >= FUZZY_AUTO_THRESHOLD:
            fuzzy_params_map[item_id] = row_params
            fuzzy_type_map[item_id] = MATCH_TYPE_FUZZY_AUTO
            fuzzy_confidence_map[item_id] = _assign_confidence(
                MATCH_TYPE_FUZZY_AUTO, best_score, _brands_match(brand_ml, brand_sec)
            )

        # --- Etapa 3: FUZZY_AUTO_CONTROLLED (score 80-84 + filtros) ---
        elif best_score >= FUZZY_CONTROLLED_THRESHOLD:
            passed, reject_reason = _passes_controlled_filters(
                norm_ml, norm_sec, brand_ml, brand_sec, best_score, gap
            )
            if passed:
                fuzzy_params_map[item_id] = row_params
                fuzzy_type_map[item_id] = MATCH_TYPE_FUZZY_CONTROLLED
                fuzzy_confidence_map[item_id] = _assign_confidence(
                    MATCH_TYPE_FUZZY_CONTROLLED, best_score, _brands_match(brand_ml, brand_sec)
                )
            else:
                # Nao passou filtros: rebaixa para MATCH_PROVAVEL
                fuzzy_params_map[item_id] = row_params
                fuzzy_type_map[item_id] = MATCH_TYPE_FUZZY_PROVAVEL
                fuzzy_confidence_map[item_id] = CONFIDENCE_BAIXA

        # --- Etapa 4: MATCH_PROVAVEL (score 75-79) ---
        elif best_score >= FUZZY_PROVAVEL_THRESHOLD:
            fuzzy_params_map[item_id] = row_params
            fuzzy_type_map[item_id] = MATCH_TYPE_FUZZY_PROVAVEL
            fuzzy_confidence_map[item_id] = CONFIDENCE_BAIXA

        # --- Etapa 5: SEM_MATCH ---
        else:
            fuzzy_params_map[item_id] = {}
            fuzzy_type_map[item_id] = MATCH_TYPE_SEM_MATCH
            fuzzy_confidence_map[item_id] = CONFIDENCE_BAIXA

    return fuzzy_params_map, fuzzy_score_map, fuzzy_type_map, fuzzy_confidence_map


def _apply_fuzzy_params(
    final: pd.DataFrame,
    fuzzy_params_map: dict[str, Any],
    fuzzy_score_map: dict[str, float],
    fuzzy_type_map: dict[str, str],
    fuzzy_confidence_map: dict[str, str],
    param_columns: list[str],
) -> pd.DataFrame:
    """Preenche parametros Seconds nos itens resolvidos por fuzzy.

    Aplica CMV apenas para FUZZY_AUTO e FUZZY_AUTO_CONTROLLED.
    MATCH_PROVAVEL: registra candidato mas NAO aplica CMV.
    SEM_MATCH: sem alteracao.
    NUNCA sobrescreve um match exato existente.
    """
    sem_match_mask = ~final["match_seconds"].fillna(False)
    if not sem_match_mask.any():
        return final

    for col in param_columns + ["match_confidence"]:
        if col not in final.columns:
            final[col] = pd.NA

    sem_match_rows = final.index[sem_match_mask]

    for idx in sem_match_rows:
        item_id = final.at[idx, "item_id"]
        match_type = fuzzy_type_map.get(item_id, MATCH_TYPE_SEM_MATCH)
        score = fuzzy_score_map.get(item_id, 0.0)
        confidence = fuzzy_confidence_map.get(item_id, CONFIDENCE_BAIXA)

        # Colunas de controle — sempre preenchidas
        final.at[idx, "match_type"] = match_type
        final.at[idx, "match_score"] = score
        final.at[idx, "match_confidence"] = confidence
        final.at[idx, "matched_item_seconds"] = ""

        if match_type in _MATCH_TYPES_APPLY_CMV:
            row_params = fuzzy_params_map.get(item_id, {})
            if row_params:
                final.at[idx, "matched_item_seconds"] = row_params.get("item_id", "")
                for col in param_columns:
                    val = row_params.get(col)
                    if val is not None and not (isinstance(val, float) and pd.isna(val)):
                        final.at[idx, col] = val
                # Marca como matched para pipeline de calculo
                final.at[idx, "match_seconds"] = True
                final.at[idx, "parametro_confiavel"] = row_params.get(
                    "parametro_confiavel", False
                )

        elif match_type == MATCH_TYPE_FUZZY_PROVAVEL:
            # Apenas registra candidato — CMV nao aplicado
            row_params = fuzzy_params_map.get(item_id, {})
            if row_params:
                final.at[idx, "matched_item_seconds"] = row_params.get("item_id", "")

    return final


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_csv(path)


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print("=" * 80)
    print("ARQUIVOS DE ENTRADA")
    print("=" * 80)
    print(f"Pedidos Mercado Livre: {ML_ORDERS_PATH}")
    print(f"Shipments ML: {ML_SHIPMENTS_PATH if ML_SHIPMENTS_PATH.exists() else 'nao encontrado'}")
    print(f"Parametros Seconds: {PARAMETERS_PATH}")
    print(f"Detalhes anuncios ML: {ML_ITEMS_DETAILS_PATH if ML_ITEMS_DETAILS_PATH.exists() else 'nao encontrado'}")
    orders = read_csv_required(ML_ORDERS_PATH)
    shipments = read_csv_optional(ML_SHIPMENTS_PATH)
    parameters = read_csv_required(PARAMETERS_PATH)
    items = read_csv_optional(ML_ITEMS_DETAILS_PATH)
    return orders, shipments, parameters, items


# ---------------------------------------------------------------------------
# Normalizadores de fontes
# ---------------------------------------------------------------------------

def normalize_orders(df: pd.DataFrame) -> pd.DataFrame:
    required = ["order_id", "date_created", "item_id", "quantity", "unit_price"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{ML_ORDERS_PATH} sem colunas obrigatorias: {missing}")
    orders = df.copy()
    orders["order_id"] = orders["order_id"].map(standardize_id)
    orders["date_created"] = pd.to_datetime(orders["date_created"], errors="coerce", utc=True)
    orders["item_id"] = orders["item_id"].map(standardize_mlb)
    orders["quantity"] = orders["quantity"].map(parse_number)
    orders["unit_price"] = orders["unit_price"].map(parse_number)
    orders["receita"] = orders["unit_price"] * orders["quantity"]
    orders["sale_fee"] = orders["sale_fee"].map(parse_number) if "sale_fee" in orders.columns else 0.0
    orders["status_pedido"] = orders["status"].map(clean_text) if "status" in orders.columns else ""
    orders["produto_ml_order"] = orders["item_title"].map(clean_text) if "item_title" in orders.columns else ""
    orders["listing_type_id"] = orders["listing_type_id"].map(clean_text) if "listing_type_id" in orders.columns else ""
    keep = [
        "order_id", "date_created", "status_pedido", "item_id",
        "produto_ml_order", "quantity", "unit_price", "receita",
        "sale_fee", "listing_type_id",
    ]
    return orders[orders["item_id"] != ""][keep].copy()


def normalize_shipments(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "order_id", "shipping_status", "shipping_substatus", "shipping_mode",
        "logistic_type", "shipping_option_name", "shipping_option_cost",
        "shipping_option_list_cost", "receiver_cost", "sender_cost",
    ]
    if df.empty or "order_id" not in df.columns:
        return pd.DataFrame(columns=columns)
    shipments = pd.DataFrame(index=df.index)
    shipments["order_id"] = df["order_id"].map(standardize_id)
    shipments["shipping_status"] = df["status"].map(clean_text) if "status" in df.columns else ""
    shipments["shipping_substatus"] = df["substatus"].map(clean_text) if "substatus" in df.columns else ""
    shipments["shipping_mode"] = df["mode"].map(clean_text) if "mode" in df.columns else ""
    shipments["logistic_type"] = df["logistic_type"].map(clean_text) if "logistic_type" in df.columns else ""
    shipments["shipping_option_name"] = df["shipping_option_name"].map(clean_text) if "shipping_option_name" in df.columns else ""
    shipments["shipping_option_cost"] = df["shipping_option_cost"].map(parse_number) if "shipping_option_cost" in df.columns else 0.0
    shipments["shipping_option_list_cost"] = df["shipping_option_list_cost"].map(parse_number) if "shipping_option_list_cost" in df.columns else 0.0
    shipments["receiver_cost"] = df["receiver_cost"].map(parse_number) if "receiver_cost" in df.columns else 0.0
    shipments["sender_cost"] = df["sender_cost"].map(parse_number) if "sender_cost" in df.columns else 0.0
    return shipments[shipments["order_id"] != ""].drop_duplicates(subset=["order_id"], keep="last")[columns]


def normalize_parameters(df: pd.DataFrame) -> pd.DataFrame:
    required = ["item_id", "cmv_unitario_seconds", "parametro_confiavel"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{PARAMETERS_PATH} sem colunas obrigatorias: {missing}")
    params = df.copy()
    params["item_id"] = params["item_id"].map(standardize_mlb)
    text_cols = ["sku", "produto", "marca", "categoria", "full", "flex", "status", "link_anuncio"]
    num_cols = [
        "preco_venda_seconds", "cmv_unitario_seconds", "comissao_unitaria_seconds",
        "frete_unitario_seconds", "custo_fixo_unitario_seconds",
        "imposto_unitario_seconds", "lucro_liquido_unitario_seconds", "margem_seconds",
    ]
    for col in text_cols:
        if col not in params.columns:
            params[col] = ""
        params[col] = params[col].map(clean_text)
    for col in num_cols:
        if col not in params.columns:
            params[col] = 0.0
        params[col] = params[col].map(parse_number)
    params["parametro_confiavel"] = params["parametro_confiavel"].astype(str).str.lower().isin(
        {"true", "1", "sim", "yes"}
    )
    return params[params["item_id"] != ""].drop_duplicates(subset=["item_id"], keep="last")


def normalize_items_details(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "item_id", "seller_custom_field", "produto_ml_details", "marca_ml",
        "categoria_ml", "estoque_atual", "sold_quantity", "vendidos_total",
        "listing_type_details", "logistic_type_details", "shipping_mode_details",
        "status_ml_item", "permalink_ml",
    ]
    if df.empty or "id" not in df.columns:
        return pd.DataFrame(columns=columns)
    items = pd.DataFrame(index=df.index)
    items["item_id"] = df["id"].map(standardize_mlb)
    items["seller_custom_field"] = df["seller_custom_field"].map(clean_text) if "seller_custom_field" in df.columns else ""
    items["produto_ml_details"] = df["title"].map(clean_text) if "title" in df.columns else ""
    items["marca_ml"] = df["brand"].map(clean_text) if "brand" in df.columns else ""
    items["categoria_ml"] = df["category_name"].map(clean_text) if "category_name" in df.columns else ""
    items["estoque_atual"] = df["estoque_atual"].map(parse_number) if "estoque_atual" in df.columns else 0.0
    items["sold_quantity"] = df["sold_quantity"].map(parse_number) if "sold_quantity" in df.columns else 0.0
    items["vendidos_total"] = df["vendidos_total"].map(parse_number) if "vendidos_total" in df.columns else 0.0
    items["listing_type_details"] = df["listing_type_id"].map(clean_text) if "listing_type_id" in df.columns else ""
    items["logistic_type_details"] = df["shipping_logistic_type"].map(clean_text) if "shipping_logistic_type" in df.columns else ""
    items["shipping_mode_details"] = df["shipping_mode"].map(clean_text) if "shipping_mode" in df.columns else ""
    items["status_ml_item"] = df["status"].map(clean_text) if "status" in df.columns else ""
    items["permalink_ml"] = df["permalink"].map(clean_text) if "permalink" in df.columns else ""
    return items[items["item_id"] != ""].drop_duplicates(subset=["item_id"], keep="last")[columns]


# ---------------------------------------------------------------------------
# Build principal
# ---------------------------------------------------------------------------

def build_final_dataframe(
    orders_df: pd.DataFrame,
    shipments_df: pd.DataFrame,
    parameters_df: pd.DataFrame,
    items_df: pd.DataFrame,
) -> pd.DataFrame:
    orders = normalize_orders(orders_df)
    shipments = normalize_shipments(shipments_df)
    params = normalize_parameters(parameters_df)
    items = normalize_items_details(items_df)

    final = orders.merge(shipments, on="order_id", how="left")
    final = final.merge(params, on="item_id", how="left", suffixes=("", "_seconds"))
    final = final.merge(items, on="item_id", how="left")

    final["parametro_confiavel"] = final["parametro_confiavel"].fillna(False).astype(bool)
    final["match_seconds"] = final["cmv_unitario_seconds"].notna()

    # -------------------------------------------------------------------
    # ETAPA 1 — MATCH_EXACT: marca rastreabilidade
    # -------------------------------------------------------------------
    final["match_type"] = MATCH_TYPE_SEM_MATCH
    final["match_score"] = 0.0
    final["match_confidence"] = CONFIDENCE_BAIXA
    final["matched_item_seconds"] = ""
    final.loc[final["match_seconds"], "match_type"] = MATCH_TYPE_EXACT
    final.loc[final["match_seconds"], "match_score"] = 100.0
    final.loc[final["match_seconds"], "match_confidence"] = CONFIDENCE_ALTA
    final.loc[final["match_seconds"], "matched_item_seconds"] = final.loc[
        final["match_seconds"], "item_id"
    ]

    # -------------------------------------------------------------------
    # ETAPAS 2-5 — FUZZY (apenas itens sem match exato)
    # -------------------------------------------------------------------
    sem_match_ids = final.loc[~final["match_seconds"], "item_id"].unique().tolist()
    if sem_match_ids:
        print(f"\n[FUZZY] Engine: {FUZZY_ENGINE}")
        print(f"[FUZZY] Itens sem match exato: {len(sem_match_ids)}")

        # Mapa item_id -> nome e marca do produto
        item_name_map: dict[str, str] = {}
        item_brand_map: dict[str, str] = {}
        for _, row in final[~final["match_seconds"]].drop_duplicates("item_id").iterrows():
            nome = str(row.get("produto_ml_order", "")).strip()
            if not nome or nome.lower() in {"nan", "none", ""}:
                nome = str(row.get("produto_ml_details", "")).strip()
            item_name_map[row["item_id"]] = nome
            # Marca: prioriza marca ja conhecida no ML
            marca = str(row.get("marca_ml", "")).strip()
            if not marca or marca.lower() in {"nan", "none", "n/d", ""}:
                marca = str(row.get("marca", "")).strip()
            item_brand_map[row["item_id"]] = marca

        sec_ids, sec_norms, sec_brands = _build_fuzzy_lookup(params)

        _param_cols = [
            "sku", "produto", "marca", "categoria", "full", "flex", "status",
            "link_anuncio", "preco_venda_seconds",
            "cmv_unitario_seconds", "comissao_unitaria_seconds",
            "frete_unitario_seconds", "custo_fixo_unitario_seconds",
            "imposto_unitario_seconds", "lucro_liquido_unitario_seconds",
            "margem_seconds", "parametro_confiavel",
        ]

        fuzzy_params_map, fuzzy_score_map, fuzzy_type_map, fuzzy_confidence_map = _fuzzy_match_items(
            sem_match_ids, item_name_map, item_brand_map,
            sec_ids, sec_norms, sec_brands, params
        )

        final = _apply_fuzzy_params(
            final, fuzzy_params_map, fuzzy_score_map,
            fuzzy_type_map, fuzzy_confidence_map, _param_cols
        )

        n_auto = sum(1 for v in fuzzy_type_map.values() if v == MATCH_TYPE_FUZZY_AUTO)
        n_ctrl = sum(1 for v in fuzzy_type_map.values() if v == MATCH_TYPE_FUZZY_CONTROLLED)
        n_prov = sum(1 for v in fuzzy_type_map.values() if v == MATCH_TYPE_FUZZY_PROVAVEL)
        n_sem = sum(1 for v in fuzzy_type_map.values() if v == MATCH_TYPE_SEM_MATCH)
        print(f"[FUZZY] FUZZY_AUTO           (score>={FUZZY_AUTO_THRESHOLD}):  {n_auto} itens (CMV aplicado)")
        print(f"[FUZZY] FUZZY_AUTO_CONTROLLED (score {FUZZY_CONTROLLED_THRESHOLD}-{FUZZY_AUTO_THRESHOLD-1}+filtros): {n_ctrl} itens (CMV aplicado)")
        print(f"[FUZZY] MATCH_PROVAVEL        (score {FUZZY_PROVAVEL_THRESHOLD}-{FUZZY_CONTROLLED_THRESHOLD-1} ou filtros reprovados): {n_prov} itens (marcado, sem CMV)")
        print(f"[FUZZY] SEM_MATCH             (score<{FUZZY_PROVAVEL_THRESHOLD}): {n_sem} itens")
    # -------------------------------------------------------------------

    final["status_parametro"] = final["parametro_confiavel"].map(
        {True: PARAM_OK, False: PARAM_MISSING}
    )
    final.loc[~final["match_seconds"], "status_parametro"] = PARAM_MISSING

    for col in [
        "cmv_unitario_seconds", "comissao_unitaria_seconds", "frete_unitario_seconds",
        "custo_fixo_unitario_seconds", "imposto_unitario_seconds",
        "lucro_liquido_unitario_seconds", "margem_seconds",
    ]:
        final[col] = pd.to_numeric(final[col], errors="coerce").fillna(0)

    reliable = final["parametro_confiavel"]
    final["cmv_total"] = final["cmv_unitario_seconds"].where(reliable, 0) * final["quantity"]
    final["frete_total"] = final["frete_unitario_seconds"].where(reliable, 0) * final["quantity"]
    final["imposto_total"] = final["imposto_unitario_seconds"].where(reliable, 0) * final["quantity"]
    final["custo_fixo_total"] = final["custo_fixo_unitario_seconds"].where(reliable, 0) * final["quantity"]
    final["comissao_total"] = final["comissao_unitaria_seconds"].where(reliable, 0) * final["quantity"]

    # Fallback: sem parametro Seconds confiavel, usa comissao transacional do ML
    final.loc[~reliable, "comissao_total"] = final.loc[~reliable, "sale_fee"].fillna(0)

    final["lucro_liquido_estimado"] = (
        final["receita"]
        - final["cmv_total"]
        - final["comissao_total"]
        - final["frete_total"]
        - final["imposto_total"]
        - final["custo_fixo_total"]
    )
    final["margem_liquida_estimada"] = (
        final["lucro_liquido_estimado"] / final["receita"].replace(0, pd.NA) * 100
    ).fillna(0)

    final["sku"] = coalesce(final["sku"], final["seller_custom_field"]).replace("", "N/D")
    final["produto"] = coalesce(final["produto"], final["produto_ml_order"])
    final["produto"] = coalesce(final["produto"], final["produto_ml_details"]).replace("", "N/D")
    final["marca"] = coalesce(final["marca"], final["marca_ml"]).replace("", "N/D")
    final["categoria"] = coalesce(final["categoria"], final["categoria_ml"]).replace("", "N/D")
    final["full"] = final["full"].fillna("").replace("", "N/D")
    final["flex"] = final["flex"].fillna("").replace("", "N/D")
    final["status"] = coalesce(final["status"], final["status_pedido"]).replace("", "N/D")
    final["link_anuncio"] = coalesce(final["link_anuncio"], final["permalink_ml"]).replace("", "N/D")
    final["listing_type_id"] = coalesce(final["listing_type_id"], final["listing_type_details"]).replace("", "N/D")
    final["logistic_type"] = coalesce(final["logistic_type"], final["logistic_type_details"]).replace("", "N/D")
    final["shipping_mode"] = coalesce(final["shipping_mode"], final["shipping_mode_details"]).replace("", "N/D")

    # Aliases historicos usados pelo app.py
    final["SKU"] = final["sku"]
    final["Marca"] = final["marca"]
    final["Nome da Categoria"] = final["categoria"]
    final["FULL"] = final["full"]
    final["Flex"] = final["flex"]
    final["Status"] = final["status"]
    final["LinkAnuncio"] = final["link_anuncio"]
    final["CMV total"] = final["cmv_total"]
    final["custo_frete_final"] = final["frete_total"]
    final["custo_frete"] = final["frete_total"]
    final["imposto"] = final["imposto_total"]
    final["custo_fixo"] = final["custo_fixo_total"]
    final["comissao_ml"] = final["comissao_total"]
    final["lucro_bruto"] = final["receita"] - final["cmv_total"] - final["comissao_total"]
    final["lucro_operacional"] = final["lucro_bruto"] - final["frete_total"]
    final["margem_bruta"] = (final["lucro_bruto"] / final["receita"].replace(0, pd.NA) * 100).fillna(0)
    final["margem_operacional"] = (
        final["lucro_operacional"] / final["receita"].replace(0, pd.NA) * 100
    ).fillna(0)
    final["Lucro Bruto"] = final["lucro_bruto"]
    final["Lucro Liquido Seconds"] = final["lucro_liquido_estimado"]
    final["Margem Seconds"] = final["margem_liquida_estimada"]
    final["margem calculada"] = final["margem_liquida_estimada"]
    final["CMV unitario"] = final["cmv_unitario_seconds"]
    final["CMV unit\ufffdrio"] = final["cmv_unitario_seconds"]
    final["CMV unitÃƒÂ¡rio"] = final["cmv_unitario_seconds"]
    final["cmv_seconds"] = final["cmv_total"]
    final["frete_seconds"] = final["frete_total"]
    final["imposto_seconds"] = final["imposto_total"]
    final["custo_fixo_seconds"] = final["custo_fixo_total"]
    final["lucro_liquido_seconds"] = final["lucro_liquido_estimado"]
    final["faturamento_seconds"] = 0.0
    final["financial_source"] = "ml_orders_seconds_params"
    final["match_ml"] = True

    final["estoque_atual"] = pd.to_numeric(final.get("estoque_atual", 0), errors="coerce").fillna(0)
    final["sold_quantity"] = pd.to_numeric(final.get("sold_quantity", 0), errors="coerce").fillna(0)
    final["vendidos_total"] = pd.to_numeric(final.get("vendidos_total", 0), errors="coerce").fillna(0)

    required_output = [
        "order_id", "date_created", "item_id", "sku", "produto", "marca", "categoria",
        "quantity", "unit_price", "receita", "cmv_total", "frete_total", "imposto_total",
        "custo_fixo_total", "comissao_total", "lucro_liquido_estimado",
        "margem_liquida_estimada", "parametro_confiavel", "status_parametro",
        "full", "flex", "link_anuncio",
    ]
    compatibility_output = [
        "status_pedido", "listing_type_id", "shipping_status", "shipping_substatus",
        "shipping_mode", "logistic_type", "shipping_option_name", "shipping_option_cost",
        "shipping_option_list_cost", "receiver_cost", "sender_cost", "sale_fee",
        "comissao_ml", "cmv_unitario_seconds", "comissao_unitaria_seconds",
        "frete_unitario_seconds", "imposto_unitario_seconds", "custo_fixo_unitario_seconds",
        "lucro_liquido_unitario_seconds", "margem_seconds", "match_seconds",
        "financial_source", "SKU", "Marca", "Nome da Categoria", "FULL", "Flex",
        "Status", "LinkAnuncio", "CMV total", "CMV unitario",
        "CMV unit\ufffdrio", "CMV unitÃƒÂ¡rio",
        "custo_frete", "custo_frete_final", "imposto", "custo_fixo",
        "lucro_bruto", "lucro_operacional", "margem_bruta", "margem_operacional",
        "Lucro Bruto", "Lucro Liquido Seconds", "Margem Seconds", "margem calculada",
        "cmv_seconds", "frete_seconds", "imposto_seconds", "custo_fixo_seconds",
        "lucro_liquido_seconds", "faturamento_seconds", "estoque_atual",
        "sold_quantity", "vendidos_total", "match_ml",
        "match_type", "match_score", "match_confidence", "matched_item_seconds",
    ]

    for col in required_output + compatibility_output:
        if col not in final.columns:
            final[col] = pd.NA

    return final[required_output + compatibility_output].copy()


# ---------------------------------------------------------------------------
# Output e resumo
# ---------------------------------------------------------------------------

def save_output(df: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame) -> None:
    total_linhas = len(df)
    faturamento_total = float(df["receita"].sum()) if total_linhas else 0.0
    reliable = df["parametro_confiavel"].fillna(False).astype(bool)
    item_params = df.groupby("item_id", as_index=False)["parametro_confiavel"].max()
    itens_com_parametro = int(item_params["parametro_confiavel"].sum()) if not item_params.empty else 0
    itens_sem_parametro = int(len(item_params) - itens_com_parametro)
    faturamento_com_parametro = float(df.loc[reliable, "receita"].sum()) if total_linhas else 0.0
    faturamento_sem_parametro = float(df.loc[~reliable, "receita"].sum()) if total_linhas else 0.0
    lucro_liquido_estimado = float(df["lucro_liquido_estimado"].sum()) if total_linhas else 0.0
    margem_media = (lucro_liquido_estimado / faturamento_total * 100) if faturamento_total else 0.0
    unique_items = int(df["item_id"].nunique()) if total_linhas else 0
    matched_items = int(df.loc[df["match_seconds"].fillna(False), "item_id"].nunique()) if total_linhas else 0
    match_rate = (matched_items / unique_items * 100) if unique_items else 0.0

    print("\n" + "=" * 80)
    print("RESUMO MERGE HIBRIDO ML + SECONDS")
    print("=" * 80)
    print(f"Linhas finais                     : {total_linhas}")
    print(f"Faturamento total ML              : {format_brl(faturamento_total)}")
    print(f"Itens com parametro confiavel     : {itens_com_parametro}")
    print(f"Itens sem parametro               : {itens_sem_parametro}")
    print(f"Faturamento com parametro         : {format_brl(faturamento_com_parametro)}")
    print(f"Faturamento sem parametro         : {format_brl(faturamento_sem_parametro)}")
    print(f"Lucro liquido estimado            : {format_brl(lucro_liquido_estimado)}")
    print(f"Margem media                      : {margem_media:.2f}%".replace(".", ","))
    print(f"Match rate por item_id            : {match_rate:.2f}%".replace(".", ","))

    if "match_type" in df.columns:
        print("\n--- Breakdown por tipo de match ---")
        for mtype in [
            MATCH_TYPE_EXACT, MATCH_TYPE_FUZZY_AUTO,
            MATCH_TYPE_FUZZY_CONTROLLED, MATCH_TYPE_FUZZY_PROVAVEL, MATCH_TYPE_SEM_MATCH
        ]:
            mask = df["match_type"].fillna(MATCH_TYPE_SEM_MATCH) == mtype
            n_items = int(df.loc[mask, "item_id"].nunique())
            receita = float(df.loc[mask, "receita"].sum())
            pct = receita / faturamento_total * 100 if faturamento_total else 0.0
            cmv_flag = " [CMV]" if mtype in _MATCH_TYPES_APPLY_CMV else ""
            print(f"  {mtype:<26}{cmv_flag:<7}: {n_items:>4} itens | {format_brl(receita):>16} ({pct:.1f}%)")

    if "match_type" in df.columns:
        exact_r = float(df.loc[df["match_type"] == MATCH_TYPE_EXACT, "receita"].sum())
        fuzzy_r = float(df.loc[df["match_type"].isin(
            [MATCH_TYPE_FUZZY_AUTO, MATCH_TYPE_FUZZY_CONTROLLED]), "receita"
        ].sum())
        cob_antes = exact_r / faturamento_total * 100 if faturamento_total else 0.0
        cob_depois = (exact_r + fuzzy_r) / faturamento_total * 100 if faturamento_total else 0.0
        print(f"\n  Cobertura CMV antes do fuzzy  : {cob_antes:.2f}%")
        print(f"  Cobertura CMV apos fuzzy      : {cob_depois:.2f}%  (+{cob_depois - cob_antes:.2f}pp)")

    if "match_confidence" in df.columns:
        print("\n--- Breakdown por confianca ---")
        for conf in [CONFIDENCE_ALTA, CONFIDENCE_MEDIA, CONFIDENCE_BAIXA]:
            mask = df["match_confidence"].fillna(CONFIDENCE_BAIXA) == conf
            n_items = int(df.loc[mask, "item_id"].nunique())
            receita = float(df.loc[mask, "receita"].sum())
            pct = receita / faturamento_total * 100 if faturamento_total else 0.0
            print(f"  {conf:<8}: {n_items:>4} itens | {format_brl(receita):>16} ({pct:.1f}%)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        orders_df, shipments_df, parameters_df, items_df = load_sources()
        final_df = build_final_dataframe(orders_df, shipments_df, parameters_df, items_df)
        save_output(final_df)
        print_summary(final_df)
        print(f"\nCSV salvo em: {OUTPUT_PATH}")
    except Exception as exc:
        print("\n" + "=" * 80)
        print("ERRO AO GERAR BASE FINAL")
        print("=" * 80)
        print(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
