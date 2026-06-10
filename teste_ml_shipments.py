"""Teste de consulta de shipments Mercado Livre.

Objetivo:
Ler os pedidos em data/ml_orders.csv, obter o shipment_id de cada pedido e
consultar o endpoint /shipments/{shipment_id}, salvando custo/logistica em
data/ml_shipments.csv.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_BASE_URL = "https://api.mercadolibre.com"
ORDERS_PATH = Path("data") / "ml_orders.csv"
OUTPUT_PATH = Path("data") / "ml_shipments.csv"
TIMEOUT_SECONDS = 10
PROGRESS_INTERVAL = 25
SAVE_INTERVAL = 25
MAX_NOVOS_SHIPMENTS = None

SHIPMENT_COLUMNS = [
    "order_id",
    "shipment_id",
    "status",
    "substatus",
    "mode",
    "logistic_type",
    "shipping_option_id",
    "shipping_option_name",
    "shipping_option_cost",
    "shipping_option_list_cost",
    "receiver_cost",
    "sender_cost",
    "date_created",
    "last_updated",
    "tracking_number",
    "tracking_method",
    "service_id",
    "site_id",
]


def load_credentials() -> tuple[str, str, str]:
    """Carrega credenciais Mercado Livre do arquivo .env."""

    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    client_id = os.getenv("ML_CLIENT_ID", "").strip()
    client_secret = os.getenv("ML_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("ML_REFRESH_TOKEN", "").strip()

    missing = [
        name
        for name, value in {
            "ML_CLIENT_ID": client_id,
            "ML_CLIENT_SECRET": client_secret,
            "ML_REFRESH_TOKEN": refresh_token,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Variaveis ausentes no .env: {', '.join(missing)}")

    return client_id, client_secret, refresh_token


def get_max_novos_shipments() -> int | None:
    """Le o limite opcional de novos shipments para modo rapido."""

    env_value = os.getenv("ML_SHIPMENTS_MAX_NOVOS", "").strip()
    configured_value = env_value if env_value else MAX_NOVOS_SHIPMENTS

    if configured_value in (None, ""):
        return None

    try:
        max_novos = int(configured_value)
    except (TypeError, ValueError):
        print(f"ML_SHIPMENTS_MAX_NOVOS invalido: {configured_value!r}. Ignorando limite.")
        return None

    if max_novos < 0:
        print(f"ML_SHIPMENTS_MAX_NOVOS negativo: {max_novos}. Ignorando limite.")
        return None

    return max_novos


def print_json(title: str, payload: dict[str, Any] | list[Any]) -> None:
    """Imprime JSON organizado para auditoria no terminal."""

    print(f"\n{'=' * 80}")
    print(title)
    print("=" * 80)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def generate_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Gera access_token usando refresh_token."""

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

    response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    print(f"Status token: {response.status_code}")

    try:
        token_data = response.json()
    except ValueError:
        print(response.text)
        token_data = {}

    response.raise_for_status()
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("A resposta do Mercado Livre nao retornou access_token.")

    return access_token


def request_ml(access_token: str, endpoint: str) -> dict[str, Any]:
    """Executa GET autenticado na API Mercado Livre."""

    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    try:
        data = response.json()
    except ValueError:
        data = {"raw_response": response.text}

    if not response.ok:
        print_json(f"ERRO EM {endpoint} - HTTP {response.status_code}", data)
        response.raise_for_status()

    return data


def request_error_message(exc: requests.exceptions.RequestException) -> str:
    """Resume erros de rede de forma estavel para log e CSV."""

    response = getattr(exc, "response", None)
    if response is not None:
        return f"HTTP {response.status_code}: {exc}"
    return str(exc)


def load_orders(path: Path) -> pd.DataFrame:
    """Carrega data/ml_orders.csv e valida a presenca de order_id."""

    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    df = pd.read_csv(path)
    if "order_id" not in df.columns:
        raise ValueError("data/ml_orders.csv precisa conter a coluna order_id.")

    df["order_id"] = df["order_id"].map(normalize_id)
    return df


def normalize_id(value: object) -> str:
    """Padroniza IDs vindos de CSVs."""

    if pd.isna(value):
        return ""
    return str(value).strip().removesuffix(".0")


def load_existing_shipments(path: Path) -> pd.DataFrame:
    """Carrega o cache existente de shipments, se houver."""

    if not path.exists():
        return pd.DataFrame(columns=SHIPMENT_COLUMNS)

    df = pd.read_csv(path)
    if "order_id" not in df.columns:
        raise ValueError("data/ml_shipments.csv precisa conter a coluna order_id.")

    df["order_id"] = df["order_id"].map(normalize_id)
    return df


def get_unique_order_ids(df: pd.DataFrame) -> list[str]:
    """Retorna pedidos unicos e validos em ordem."""

    return sorted(order_id for order_id in df["order_id"].dropna().astype(str).unique() if order_id)


def get_shipment_id_from_order(access_token: str, order_id: str) -> str | None:
    """Busca shipment_id no detalhe do pedido."""

    order = request_ml(access_token, f"/orders/{order_id}")
    shipping = order.get("shipping") or {}
    shipment_id = shipping.get("id")

    if shipment_id is None:
        return None

    return str(shipment_id).removesuffix(".0")


def get_shipment_detail(access_token: str, shipment_id: str) -> dict[str, Any]:
    """Consulta /shipments/{shipment_id}."""

    return request_ml(access_token, f"/shipments/{shipment_id}")


def extract_shipping_cost(shipment: dict[str, Any]) -> dict[str, float | None]:
    """Extrai custos mais comuns retornados pelo shipment."""

    shipping_option = shipment.get("shipping_option") or {}
    receiver_cost = shipment.get("receiver_cost")
    sender_cost = shipment.get("sender_cost")

    return {
        "shipping_option_cost": shipping_option.get("cost"),
        "shipping_option_list_cost": shipping_option.get("list_cost"),
        "receiver_cost": receiver_cost,
        "sender_cost": sender_cost,
    }


def normalize_shipment(order_id: str, shipment_id: str, shipment: dict[str, Any]) -> dict[str, Any]:
    """Normaliza os campos logisticos/custos para DataFrame."""

    shipping_option = shipment.get("shipping_option") or {}
    costs = extract_shipping_cost(shipment)

    return {
        "order_id": order_id,
        "shipment_id": shipment_id,
        "status": shipment.get("status"),
        "substatus": shipment.get("substatus"),
        "mode": shipment.get("mode"),
        "logistic_type": shipment.get("logistic_type"),
        "shipping_option_id": shipping_option.get("id"),
        "shipping_option_name": shipping_option.get("name"),
        "shipping_option_cost": costs["shipping_option_cost"],
        "shipping_option_list_cost": costs["shipping_option_list_cost"],
        "receiver_cost": costs["receiver_cost"],
        "sender_cost": costs["sender_cost"],
        "date_created": shipment.get("date_created"),
        "last_updated": shipment.get("last_updated"),
        "tracking_number": shipment.get("tracking_number"),
        "tracking_method": shipment.get("tracking_method"),
        "service_id": shipment.get("service_id"),
        "site_id": shipment.get("site_id"),
    }


def combine_shipments(existing_df: pd.DataFrame, new_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Combina cache existente com novas linhas preservando as colunas atuais."""

    new_df = pd.DataFrame(new_rows)
    if new_df.empty:
        combined = existing_df.copy()
    else:
        combined = pd.concat([existing_df, new_df], ignore_index=True, sort=False)

    ordered_columns = [
        *SHIPMENT_COLUMNS,
        *[column for column in combined.columns if column not in SHIPMENT_COLUMNS],
    ]
    return combined.reindex(columns=ordered_columns)


def build_shipments_dataframe(
    access_token: str,
    orders_df: pd.DataFrame,
    existing_df: pd.DataFrame,
    new_order_ids: list[str],
    total_orders: int,
    cached_orders: int,
) -> tuple[pd.DataFrame, int]:
    """Busca shipment_id e detalhes logisticos apenas para pedidos novos."""

    existing_shipment_by_order: dict[str, str] = {}

    if "shipment_id" in orders_df.columns:
        shipment_rows = orders_df[["order_id", "shipment_id"]].dropna().drop_duplicates()
        existing_shipment_by_order = {
            str(row["order_id"]): str(row["shipment_id"]).removesuffix(".0")
            for _, row in shipment_rows.iterrows()
        }

    rows: list[dict[str, Any]] = []
    cache_by_shipment_id: dict[str, dict[str, Any]] = {}
    errors = 0

    print(f"Pedidos novos para consultar: {len(new_order_ids)}")
    print(
        f"Cache carregado: {cached_orders}/{total_orders} pedidos ja existem em {OUTPUT_PATH}."
    )

    for index, order_id in enumerate(new_order_ids, start=1):
        try:
            shipment_id = existing_shipment_by_order.get(order_id)
            if not shipment_id:
                shipment_id = get_shipment_id_from_order(access_token, order_id)

            if not shipment_id:
                print(f"[{index}/{len(new_order_ids)}] Pedido {order_id}: sem shipment_id.")
                rows.append({"order_id": order_id, "shipment_id": None, "erro": "sem shipment_id"})
                errors += 1
            else:
                if shipment_id not in cache_by_shipment_id:
                    cache_by_shipment_id[shipment_id] = get_shipment_detail(access_token, shipment_id)

                shipment = cache_by_shipment_id[shipment_id]
                rows.append(normalize_shipment(order_id, shipment_id, shipment))
                print(f"[{index}/{len(new_order_ids)}] Pedido {order_id}: shipment {shipment_id} OK.")

        except requests.exceptions.Timeout as exc:
            message = request_error_message(exc)
            print(
                f"[{index}/{len(new_order_ids)}] Pedido {order_id}: "
                f"timeout apos {TIMEOUT_SECONDS}s - {message}"
            )
            rows.append({"order_id": order_id, "shipment_id": None, "erro": message})
            errors += 1
        except requests.exceptions.HTTPError as exc:
            message = request_error_message(exc)
            print(f"[{index}/{len(new_order_ids)}] Pedido {order_id}: erro HTTP - {message}")
            rows.append({"order_id": order_id, "shipment_id": None, "erro": message})
            errors += 1
        except requests.exceptions.RequestException as exc:
            message = request_error_message(exc)
            print(f"[{index}/{len(new_order_ids)}] Pedido {order_id}: erro requisicao - {message}")
            rows.append({"order_id": order_id, "shipment_id": None, "erro": message})
            errors += 1

        if index % PROGRESS_INTERVAL == 0 or index == len(new_order_ids):
            print(
                f"Progresso: {cached_orders + index}/{total_orders} pedidos; "
                f"novos consultados: {index}; "
                f"ja em cache: {cached_orders}; "
                f"erros: {errors}."
            )

        if index % SAVE_INTERVAL == 0:
            save_dataframe(combine_shipments(existing_df, rows), OUTPUT_PATH)
            print(f"Salvamento incremental concluido apos {index} pedidos novos em {OUTPUT_PATH}.")

    if rows and len(rows) % SAVE_INTERVAL != 0:
        save_dataframe(combine_shipments(existing_df, rows), OUTPUT_PATH)
        print(f"Salvamento final do lote concluido com {len(rows)} pedidos novos em {OUTPUT_PATH}.")

    return combine_shipments(existing_df, rows), errors


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Salva a base de shipments em CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def print_summary(
    df: pd.DataFrame,
    total_orders: int,
    cached_orders: int,
    new_processed: int,
    errors: int,
    total_new_available: int,
    max_new: int | None,
) -> None:
    """Exibe resumo do teste e da coleta incremental."""

    print("\n" + "=" * 80)
    print("RESUMO SHIPMENTS")
    print("=" * 80)
    print(f"Total pedidos em ml_orders.csv: {total_orders}")
    print(f"Ja existentes no cache: {cached_orders}")
    print(f"Novos processados: {new_processed}")
    if max_new is not None:
        print(f"Modo rapido ML_SHIPMENTS_MAX_NOVOS: {max_new}")
        print(f"Novos ainda pendentes pelo limite: {max(total_new_available - new_processed, 0)}")
    print(f"Erros: {errors}")
    print(f"Total final salvo: {len(df)}")
    print(f"Caminho do CSV: {OUTPUT_PATH}")

    if "shipment_id" in df.columns:
        print(f"Shipments encontrados: {df['shipment_id'].notna().sum()}")
        print(f"Shipments unicos: {df['shipment_id'].dropna().nunique()}")

    cost_columns = [
        "shipping_option_cost",
        "shipping_option_list_cost",
        "receiver_cost",
        "sender_cost",
    ]
    for column in cost_columns:
        if column in df.columns:
            value = pd.to_numeric(df[column], errors="coerce").sum()
            print(f"{column}: R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    print("\nPreview:")
    print(df.head(20).to_string(index=False) if not df.empty else "Nenhum dado gerado.")


def main() -> None:
    """Executa o teste completo de shipments."""

    try:
        orders_df = load_orders(ORDERS_PATH)
        existing_shipments_df = load_existing_shipments(OUTPUT_PATH)

        order_ids = get_unique_order_ids(orders_df)
        existing_order_ids = set(get_unique_order_ids(existing_shipments_df))
        cached_orders = len(existing_order_ids.intersection(order_ids))
        all_new_order_ids = [order_id for order_id in order_ids if order_id not in existing_order_ids]
        max_new = get_max_novos_shipments()
        new_order_ids = all_new_order_ids[:max_new] if max_new is not None else all_new_order_ids

        print(f"Total pedidos em ml_orders.csv: {len(order_ids)}")
        print(f"Ja existentes no cache: {cached_orders}")
        print(f"Novos pendentes no cache: {len(all_new_order_ids)}")
        if max_new is not None:
            print(f"Modo rapido ativo: processando no maximo {max_new} novos pedidos.")

        if new_order_ids:
            client_id, client_secret, refresh_token = load_credentials()
            access_token = generate_access_token(client_id, client_secret, refresh_token)
            shipments_df, errors = build_shipments_dataframe(
                access_token,
                orders_df,
                existing_shipments_df,
                new_order_ids,
                total_orders=len(order_ids),
                cached_orders=cached_orders,
            )
        else:
            print("Nenhum pedido novo para consultar. Reaproveitando cache existente.")
            shipments_df = combine_shipments(existing_shipments_df, [])
            errors = 0

        save_dataframe(shipments_df, OUTPUT_PATH)
        print_summary(
            shipments_df,
            total_orders=len(order_ids),
            cached_orders=cached_orders,
            new_processed=len(new_order_ids),
            errors=errors,
            total_new_available=len(all_new_order_ids),
            max_new=max_new,
        )

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
