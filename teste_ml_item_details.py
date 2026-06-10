"""Coleta detalhes completos dos anuncios Mercado Livre para analise de estoque.

Fluxo:
1. Gera access_token via refresh_token.
2. Le todos os MLBs de data/ml_items.csv.
3. Consulta /items/{MLB} com retries e pausa curta entre chamadas.
4. Enriquece categoria, atributos e campos de estoque.
5. Salva data/ml_items_details.csv.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_BASE_URL = "https://api.mercadolibre.com"
TIMEOUT_SECONDS = 30
REQUEST_DELAY_SECONDS = 0.15
BATCH_SIZE = 25
BATCH_DELAY_SECONDS = 1.0
MAX_RETRIES = 4
BACKOFF_FACTOR = 1.2
ITEMS_INPUT_PATH = Path("data") / "ml_items.csv"
OUTPUT_PATH = Path("data") / "ml_items_details.csv"

LOW_STOCK_THRESHOLD = 3
EXCESS_STOCK_THRESHOLD = 30


def load_credentials() -> tuple[str, str, str, str]:
    """Carrega credenciais Mercado Livre do arquivo .env."""

    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    client_id = os.getenv("ML_CLIENT_ID", "").strip()
    client_secret = os.getenv("ML_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("ML_REFRESH_TOKEN", "").strip()
    seller_id = os.getenv("ML_SELLER_ID", "").strip()

    missing = [
        name
        for name, value in {
            "ML_CLIENT_ID": client_id,
            "ML_CLIENT_SECRET": client_secret,
            "ML_REFRESH_TOKEN": refresh_token,
            "ML_SELLER_ID": seller_id,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Variaveis ausentes no .env: {', '.join(missing)}")

    return client_id, client_secret, refresh_token, seller_id


def print_json(title: str, payload: dict[str, Any] | list[Any]) -> None:
    """Imprime JSON formatado para facilitar auditoria no terminal."""

    print(f"\n{'=' * 80}")
    print(title)
    print("=" * 80)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_session() -> requests.Session:
    """Cria sessao HTTP com retry automatico para erros transitivos."""

    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def generate_access_token(
    session: requests.Session,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    """Gera novo access_token usando refresh_token."""

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
    }

    response = session.post(
        TOKEN_URL,
        data=payload,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )

    print(f"\nStatus token: {response.status_code}")
    try:
        token_data = response.json()
        safe_token_data = dict(token_data)
        for secret_key in ["access_token", "refresh_token"]:
            if secret_key in safe_token_data:
                safe_token_data[secret_key] = "***"
        print_json("RESPOSTA DA GERACAO DO TOKEN", safe_token_data)
    except ValueError:
        print(response.text)
        token_data = {}

    response.raise_for_status()

    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("A resposta do Mercado Livre nao retornou access_token.")

    return access_token


def load_item_ids(path: Path) -> list[str]:
    """Le MLBs de data/ml_items.csv preservando a ordem e removendo duplicados."""

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {path}. "
            "Gere primeiro a lista de anuncios em data/ml_items.csv."
        )

    df = pd.read_csv(path)
    candidate_columns = ["mlb", "MLB", "item_id", "id"]
    id_column = next((column for column in candidate_columns if column in df.columns), None)
    if id_column is None:
        raise ValueError(
            "data/ml_items.csv precisa conter uma coluna de MLB "
            f"entre {candidate_columns}. Colunas encontradas: {list(df.columns)}"
        )

    item_ids = (
        df[id_column]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )
    item_ids = item_ids[item_ids.str.startswith("MLB")]
    return list(dict.fromkeys(item_ids.tolist()))


def get_json(
    session: requests.Session,
    access_token: str,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Executa GET autenticado e retorna JSON."""

    url = endpoint if endpoint.startswith("http") else f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }
    response = session.get(
        url,
        headers=headers,
        params=params,
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def fetch_item_detail(
    session: requests.Session,
    access_token: str,
    mlb: str,
) -> dict[str, Any] | None:
    """Consulta detalhes completos de um anuncio pelo endpoint /items/{MLB}."""

    try:
        data = get_json(
            session,
            access_token,
            f"/items/{mlb}",
            params={"include_attributes": "all"},
        )
        if not isinstance(data, dict):
            print(f"Resposta inesperada para {mlb}; item ignorado.")
            return None
        return data
    except requests.exceptions.HTTPError as exc:
        print(f"Erro HTTP ao consultar {mlb}: {exc}")
    except requests.exceptions.Timeout:
        print(f"Erro: timeout ao consultar {mlb} apos {TIMEOUT_SECONDS} segundos.")
    except requests.exceptions.RequestException as exc:
        print(f"Erro de requisicao ao consultar {mlb}: {exc}")
    except ValueError as exc:
        print(f"Erro ao ler JSON de {mlb}: {exc}")
    return None


def fetch_category_name(
    session: requests.Session,
    access_token: str,
    category_id: str | None,
    cache: dict[str, str | None],
) -> str | None:
    """Busca nome da categoria uma unica vez por category_id."""

    if not category_id:
        return None
    if category_id in cache:
        return cache[category_id]

    try:
        data = get_json(session, access_token, f"/categories/{category_id}")
        name = data.get("name") if isinstance(data, dict) else None
    except requests.exceptions.RequestException as exc:
        print(f"Aviso: nao foi possivel buscar categoria {category_id}: {exc}")
        name = None

    cache[category_id] = name
    return name


def attribute_value(attributes: list[dict[str, Any]], attribute_id: str) -> str | None:
    """Retorna value_name de um atributo especifico quando existir."""

    for attribute in attributes:
        if attribute.get("id") == attribute_id:
            return attribute.get("value_name")
    return None


def warranty_value(item: dict[str, Any]) -> str | None:
    """Tenta obter garantia direta ou a partir de sale_terms."""

    direct = item.get("warranty")
    if direct:
        return str(direct)

    sale_terms = item.get("sale_terms") or []
    warranty_terms = [
        str(term.get("value_name"))
        for term in sale_terms
        if term.get("id") in {"WARRANTY_TYPE", "WARRANTY_TIME"} and term.get("value_name")
    ]
    return " | ".join(warranty_terms) if warranty_terms else None


def classify_stock(current_stock: float) -> str:
    """Classifica o estoque com uma regra simples inicial."""

    if current_stock <= 0:
        return "estoque zerado"
    if current_stock <= LOW_STOCK_THRESHOLD:
        return "estoque baixo"
    if current_stock >= EXCESS_STOCK_THRESHOLD:
        return "excesso estoque"
    return "estoque normal"


def normalize_item(item: dict[str, Any], category_name: str | None) -> dict[str, Any]:
    """Extrai campos relevantes e calcula indicadores iniciais de estoque."""

    shipping = item.get("shipping") or {}
    attributes = item.get("attributes") or []
    current_stock = float(item.get("available_quantity") or 0)
    sold_total = float(item.get("sold_quantity") or 0)
    stock_base = current_stock if current_stock > 0 else pd.NA
    estimated_turnover = (sold_total / stock_base) if pd.notna(stock_base) else pd.NA

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "category_id": item.get("category_id"),
        "category_name": category_name,
        "price": item.get("price"),
        "base_price": item.get("base_price"),
        "available_quantity": item.get("available_quantity"),
        "sold_quantity": item.get("sold_quantity"),
        "status": item.get("status"),
        "condition": item.get("condition"),
        "permalink": item.get("permalink"),
        "catalog_listing": item.get("catalog_listing"),
        "listing_type_id": item.get("listing_type_id"),
        "shipping_mode": shipping.get("mode"),
        "shipping_logistic_type": shipping.get("logistic_type"),
        "seller_custom_field": item.get("seller_custom_field"),
        "warranty": warranty_value(item),
        "brand": attribute_value(attributes, "BRAND"),
        "gtin": attribute_value(attributes, "GTIN"),
        "attributes": json.dumps(attributes, ensure_ascii=False),
        "health": item.get("health"),
        "date_created": item.get("date_created"),
        "last_updated": item.get("last_updated"),
        "estoque_atual": current_stock,
        "vendidos_total": sold_total,
        "giro_estimado": estimated_turnover,
        "status_estoque": classify_stock(current_stock),
    }


def build_items_dataframe(
    session: requests.Session,
    access_token: str,
    item_ids: list[str],
) -> pd.DataFrame:
    """Consulta todos os itens e monta DataFrame normalizado."""

    rows: list[dict[str, Any]] = []
    category_cache: dict[str, str | None] = {}
    total = len(item_ids)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = item_ids[batch_start : batch_start + BATCH_SIZE]
        batch_number = (batch_start // BATCH_SIZE) + 1
        batch_total = ((total - 1) // BATCH_SIZE) + 1 if total else 0
        print(f"\nLote {batch_number}/{batch_total} - {len(batch)} anuncios")

        for batch_offset, mlb in enumerate(batch, start=1):
            index = batch_start + batch_offset
            print(f"[{index}/{total}] Consultando {mlb}")
            item = fetch_item_detail(session, access_token, mlb)
            if item:
                category_name = fetch_category_name(
                    session,
                    access_token,
                    item.get("category_id"),
                    category_cache,
                )
                rows.append(normalize_item(item, category_name))
            time.sleep(REQUEST_DELAY_SECONDS)

        if batch_start + BATCH_SIZE < total:
            time.sleep(BATCH_DELAY_SECONDS)

    df = pd.DataFrame(rows)
    if not df.empty:
        numeric_columns = [
            "price",
            "base_price",
            "available_quantity",
            "sold_quantity",
            "health",
            "estoque_atual",
            "vendidos_total",
            "giro_estimado",
        ]
        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
        df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")

    return df


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva o DataFrame em CSV dentro da pasta data."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame) -> None:
    """Exibe resumo executivo da coleta e do estoque."""

    total_processed = len(df)
    total_stock = int(df["estoque_atual"].fillna(0).sum()) if not df.empty else 0
    no_stock = int((df["status_estoque"] == "estoque zerado").sum()) if not df.empty else 0
    low_stock = int((df["status_estoque"] == "estoque baixo").sum()) if not df.empty else 0
    full_items = (
        int(df["shipping_logistic_type"].fillna("").str.lower().eq("fulfillment").sum())
        if not df.empty
        else 0
    )
    flex_items = (
        int(df["shipping_logistic_type"].fillna("").str.lower().eq("self_service").sum())
        if not df.empty
        else 0
    )
    top_sold = (
        df.sort_values("vendidos_total", ascending=False)
        .loc[:, ["id", "title", "vendidos_total", "estoque_atual", "status_estoque"]]
        .head(10)
        if not df.empty
        else pd.DataFrame()
    )

    print(f"\n{'=' * 80}")
    print("RESUMO DOS DETALHES DE ANUNCIOS")
    print("=" * 80)
    print(f"Total anuncios processados: {total_processed}")
    print(f"Total estoque: {total_stock}")
    print(f"Anuncios sem estoque: {no_stock}")
    print(f"Anuncios com estoque baixo: {low_stock}")
    print(f"Anuncios FULL: {full_items}")
    print(f"Anuncios Flex: {flex_items}")

    print("\nTop produtos vendidos:")
    if top_sold.empty:
        print("N/D")
    else:
        print(top_sold.to_string(index=False))

    print("\nPreview do DataFrame:")
    if df.empty:
        print("Nenhum item retornado.")
    else:
        print(df.head(20).to_string(index=False))


def main() -> None:
    """Executa a coleta completa de detalhes dos anuncios."""

    try:
        client_id, client_secret, refresh_token, _seller_id = load_credentials()
        item_ids = load_item_ids(ITEMS_INPUT_PATH)
        print(f"Total MLBs encontrados em {ITEMS_INPUT_PATH}: {len(item_ids)}")

        session = build_session()
        access_token = generate_access_token(session, client_id, client_secret, refresh_token)
        items_df = build_items_dataframe(session, access_token, item_ids)

        save_dataframe(items_df, OUTPUT_PATH)
        print_summary(items_df)
        print(f"\nCSV salvo em: {OUTPUT_PATH}")

    except requests.exceptions.Timeout:
        print(f"\nErro: timeout apos {TIMEOUT_SECONDS} segundos.")
    except requests.exceptions.HTTPError as exc:
        print(f"\nErro HTTP: {exc}")
    except requests.exceptions.RequestException as exc:
        print(f"\nErro de requisicao: {exc}")
    except Exception as exc:
        print(f"\nErro inesperado: {exc}")


if __name__ == "__main__":
    main()
