"""Coleta pedidos/vendas Mercado Livre por periodo configuravel.

Objetivo:
Gerar access_token via refresh_token, consultar pedidos reais da conta por
periodo e salvar uma base analitica em CSV.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ORDERS_URL = "https://api.mercadolibre.com/orders/search"
TIMEOUT_SECONDS = 30
PAGE_LIMIT = 50
WINDOW_DAYS = 15

DATA_INICIO = "2026-02-01"
DATA_FIM = date.today().isoformat()
LIMITE_TOTAL_PEDIDOS = None

OUTPUT_PATH = Path("data") / "ml_orders.csv"
BRT = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class QueryConfig:
    start_dt: datetime
    end_dt: datetime
    limit_total: int | None


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


def parse_datetime_config(value: str, *, end_of_day: bool = False) -> datetime:
    """Aceita YYYY-MM-DD ou datetime ISO e devolve datetime com fuso BRT."""

    raw = str(value).strip()
    if not raw:
        raise ValueError("Data vazia na configuracao de periodo.")

    if len(raw) == 10:
        parsed_date = date.fromisoformat(raw)
        parsed_time = time(23, 59, 59, 999000) if end_of_day else time(0, 0, 0, 0)
        return datetime.combine(parsed_date, parsed_time, tzinfo=BRT)

    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BRT)
    return parsed.astimezone(BRT)


def parse_limit(value: object) -> int | None:
    """Converte limite opcional vindo de constante ou variavel de ambiente."""

    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"", "none", "null", "0", "sem_limite"}:
        return None
    parsed = int(text)
    if parsed <= 0:
        return None
    return parsed


def load_query_config() -> QueryConfig:
    """Carrega periodo padrao e permite sobrescrita por variaveis de ambiente."""

    data_inicio = os.getenv("ML_ORDERS_DATA_INICIO", DATA_INICIO)
    data_fim = os.getenv("ML_ORDERS_DATA_FIM", DATA_FIM)
    limite_total = os.getenv("ML_ORDERS_LIMITE_TOTAL")

    start_dt = parse_datetime_config(data_inicio, end_of_day=False)
    end_dt = parse_datetime_config(data_fim, end_of_day=True)
    if start_dt > end_dt:
        raise ValueError("DATA_INICIO deve ser menor ou igual a DATA_FIM.")

    return QueryConfig(
        start_dt=start_dt,
        end_dt=end_dt,
        limit_total=parse_limit(limite_total if limite_total is not None else LIMITE_TOTAL_PEDIDOS),
    )


def ml_datetime(value: datetime) -> str:
    """Formata datetime no padrao ISO aceito pela API do Mercado Livre."""

    return value.isoformat(timespec="milliseconds")


def print_json(title: str, payload: dict[str, Any] | list[Any]) -> None:
    """Imprime JSON formatado no terminal."""

    print(f"\n{'=' * 80}")
    print(title)
    print("=" * 80)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def print_query_config(config: QueryConfig) -> None:
    """Mostra os parametros usados na consulta de pedidos."""

    print(f"\n{'=' * 80}")
    print("PARAMETROS DA CONSULTA")
    print("=" * 80)
    print(f"Periodo consultado: {ml_datetime(config.start_dt)} a {ml_datetime(config.end_dt)}")
    print(f"Limite total de pedidos: {config.limit_total if config.limit_total is not None else 'sem limite'}")
    print(f"Tamanho da pagina: {PAGE_LIMIT}")
    print(f"Tamanho das janelas: {WINDOW_DAYS} dias")


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

    response = requests.post(
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


def iter_windows(start_dt: datetime, end_dt: datetime, window_days: int) -> list[tuple[datetime, datetime]]:
    """Divide periodos longos em janelas menores inclusivas."""

    windows: list[tuple[datetime, datetime]] = []
    current_start = start_dt
    while current_start <= end_dt:
        current_end = min(current_start + timedelta(days=window_days) - timedelta(milliseconds=1), end_dt)
        windows.append((current_start, current_end))
        current_start = current_end + timedelta(milliseconds=1)
    return windows


def fetch_orders_window(
    access_token: str,
    seller_id: str,
    window_start: datetime,
    window_end: datetime,
    remaining_limit: int | None,
    window_number: int,
    total_windows: int,
) -> tuple[list[dict[str, Any]], int]:
    """Busca pedidos de uma janela usando paginacao limit/offset."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }

    window_orders: list[dict[str, Any]] = []
    offset = 0
    total_available = 0

    while remaining_limit is None or len(window_orders) < remaining_limit:
        params = {
            "seller": seller_id,
            "order.date_created.from": ml_datetime(window_start),
            "order.date_created.to": ml_datetime(window_end),
            "sort": "date_desc",
            "limit": PAGE_LIMIT,
            "offset": offset,
        }

        response = requests.get(
            ORDERS_URL,
            headers=headers,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        page_number = (offset // PAGE_LIMIT) + 1
        print(
            "\n"
            f"Janela {window_number}/{total_windows} "
            f"{window_start:%Y-%m-%d} a {window_end:%Y-%m-%d} "
            f"pagina {page_number}: status {response.status_code}"
        )

        try:
            data = response.json()
        except ValueError:
            print(response.text)
            response.raise_for_status()
            break

        response.raise_for_status()

        page_orders = data.get("results", [])
        paging = data.get("paging", {})
        total_available = int(paging.get("total", total_available or len(page_orders)))

        if page_number == 1:
            print(
                f"Total informado pela API na janela: {total_available} | "
                f"primeira pagina: {len(page_orders)} pedidos"
            )

        if not page_orders:
            break

        if remaining_limit is None:
            window_orders.extend(page_orders)
        else:
            remaining = remaining_limit - len(window_orders)
            window_orders.extend(page_orders[:remaining])

        offset += PAGE_LIMIT

        if remaining_limit is not None and len(window_orders) >= remaining_limit:
            break
        if len(window_orders) >= total_available:
            break
        if offset >= total_available:
            break

    return window_orders, total_available


def fetch_orders(access_token: str, seller_id: str, config: QueryConfig) -> tuple[list[dict[str, Any]], int]:
    """Busca pedidos em janelas menores e pagina cada janela ate acabar."""

    all_orders: list[dict[str, Any]] = []
    total_available_sum = 0
    windows = iter_windows(config.start_dt, config.end_dt, WINDOW_DAYS)

    for index, (window_start, window_end) in enumerate(windows, start=1):
        remaining_limit = None
        if config.limit_total is not None:
            remaining_limit = config.limit_total - len(all_orders)
            if remaining_limit <= 0:
                break

        window_orders, total_available = fetch_orders_window(
            access_token=access_token,
            seller_id=seller_id,
            window_start=window_start,
            window_end=window_end,
            remaining_limit=remaining_limit,
            window_number=index,
            total_windows=len(windows),
        )
        total_available_sum += total_available
        all_orders.extend(window_orders)

        if config.limit_total is not None and len(all_orders) >= config.limit_total:
            break

    return all_orders, total_available_sum


def normalize_orders(orders: list[dict[str, Any]]) -> pd.DataFrame:
    """Transforma pedidos Mercado Livre em linhas por item vendido."""

    rows: list[dict[str, Any]] = []

    for order in orders:
        buyer = order.get("buyer") or {}
        order_items = order.get("order_items") or []

        for order_item in order_items:
            item = order_item.get("item") or {}
            sale_fee = order_item.get("sale_fee")
            if sale_fee is None:
                sale_fee = order_item.get("sale_fee_amount")

            rows.append(
                {
                    "order_id": order.get("id"),
                    "date_created": order.get("date_created"),
                    "status": order.get("status"),
                    "total_amount": order.get("total_amount"),
                    "paid_amount": order.get("paid_amount"),
                    "buyer_id": buyer.get("id"),
                    "item_id": item.get("id"),
                    "item_title": item.get("title"),
                    "quantity": order_item.get("quantity"),
                    "unit_price": order_item.get("unit_price"),
                    "full_unit_price": order_item.get("full_unit_price"),
                    "sale_fee": sale_fee,
                    "listing_type_id": item.get("listing_type_id") or order_item.get("listing_type_id"),
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    numeric_columns = [
        "total_amount",
        "paid_amount",
        "quantity",
        "unit_price",
        "full_unit_price",
        "sale_fee",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["order_id", "item_id"], keep="last").reset_index(drop=True)
    removed = before_dedup - len(df)
    if removed:
        print(f"\nDuplicidades removidas por order_id + item_id: {removed}")

    return df


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva DataFrame em CSV dentro da pasta data."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame, raw_orders_count: int, total_api: int, config: QueryConfig) -> None:
    """Exibe resumo executivo do teste no terminal."""

    unique_orders = df["order_id"].nunique() if not df.empty else 0
    total_revenue = float((df["unit_price"] * df["quantity"]).sum()) if not df.empty else 0.0
    items_sold = int(df["quantity"].sum()) if not df.empty else 0
    min_date = df["date_created"].min() if not df.empty else pd.NaT
    max_date = df["date_created"].max() if not df.empty else pd.NaT

    print(f"\n{'=' * 80}")
    print("RESUMO DOS PEDIDOS")
    print("=" * 80)
    print(f"Periodo consultado: {ml_datetime(config.start_dt)} a {ml_datetime(config.end_dt)}")
    print(f"Total informado pela API nas janelas: {total_api}")
    print(f"Total coletado bruto: {raw_orders_count}")
    print(f"Total coletado final: {len(df)} linhas item/pedido")
    print(f"Pedidos unicos: {unique_orders}")
    print(f"Itens vendidos: {items_sold}")
    print(f"Faturamento total: R$ {total_revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"Data minima dos pedidos: {min_date if pd.notna(min_date) else 'N/D'}")
    print(f"Data maxima dos pedidos: {max_date if pd.notna(max_date) else 'N/D'}")
    print(f"Caminho salvo: {OUTPUT_PATH}")

    print("\nPreview do DataFrame:")
    if df.empty:
        print("Nenhum pedido encontrado no periodo.")
    else:
        print(df.head(20).to_string(index=False))


def main() -> None:
    """Executa o teste completo de pedidos por periodo."""

    try:
        config = load_query_config()
        client_id, client_secret, refresh_token, seller_id = load_credentials()
        print_query_config(config)
        access_token = generate_access_token(client_id, client_secret, refresh_token)
        orders, total_api = fetch_orders(access_token, seller_id, config)
        orders_df = normalize_orders(orders)

        save_dataframe(orders_df, OUTPUT_PATH)
        print_summary(orders_df, raw_orders_count=len(orders), total_api=total_api, config=config)

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
