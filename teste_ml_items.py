"""Teste de busca de anuncios Mercado Livre.

Objetivo:
Buscar os anuncios da conta autenticada usando refresh_token e seller_id,
salvar os MLBs encontrados em um DataFrame pandas e exibir um preview.
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
TIMEOUT_SECONDS = 30
PAGE_LIMIT = 50
MAX_OFFSET = 1000
OUTPUT_PATH = Path("data") / "ml_items.csv"


def load_credentials() -> tuple[str, str, str, str]:
    """Carrega credenciais e seller_id do arquivo .env."""

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
    """Imprime respostas JSON de forma legivel."""

    print(f"\n{'=' * 80}")
    print(title)
    print("=" * 80)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def generate_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Gera access_token usando o refresh_token."""

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


def fetch_seller_items(access_token: str, seller_id: str) -> tuple[list[str], int]:
    """Busca anuncios do seller em paginas limit/offset."""

    endpoint = f"{API_BASE_URL}/users/{seller_id}/items/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }

    all_item_ids: list[str] = []
    total_items = 0
    offset = 0

    while True:
        if offset >= MAX_OFFSET:
            print("\nLimite de offset da API atingido. Coleta parcial salva.")
            break

        params = {
            "limit": PAGE_LIMIT,
            "offset": offset,
        }

        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        page_number = (offset // PAGE_LIMIT) + 1
        print(f"\nStatus items/search pagina {page_number}: {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            print(response.text)
            response.raise_for_status()
            break

        response.raise_for_status()

        if page_number == 1:
            print_json("RESPOSTA DA PRIMEIRA PAGINA DE ANUNCIOS", data)

        paging = data.get("paging", {})
        total_items = int(paging.get("total", 0))
        page_items = data.get("results", [])

        if not page_items:
            break

        all_item_ids.extend(page_items)
        offset += PAGE_LIMIT

        # Para evitar chamadas desnecessarias, para quando todos os itens retornados ja foram coletados.
        if len(all_item_ids) >= total_items:
            break

    return all_item_ids, total_items


def build_items_dataframe(item_ids: list[str]) -> pd.DataFrame:
    """Cria DataFrame com os MLBs encontrados."""

    return pd.DataFrame(
        {
            "mlb": item_ids,
            "ordem": range(1, len(item_ids) + 1),
        }
    )


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva os MLBs encontrados em CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def main() -> None:
    """Executa o teste completo de autenticacao e busca de anuncios."""

    try:
        client_id, client_secret, refresh_token, seller_id = load_credentials()
        access_token = generate_access_token(client_id, client_secret, refresh_token)
        item_ids, total_items = fetch_seller_items(access_token, seller_id)
        items_df = build_items_dataframe(item_ids)
        save_dataframe(items_df, OUTPUT_PATH)

        print(f"\n{'=' * 80}")
        print("RESUMO DOS ANUNCIOS")
        print("=" * 80)
        print(f"Total de anuncios informado pela API: {total_items}")
        print(f"Total coletado: {len(item_ids)}")
        print(f"CSV salvo em: {OUTPUT_PATH}")
        print(f"Primeiros MLBs encontrados: {item_ids[:20]}")
        print(f"Ultimos MLBs encontrados: {item_ids[-20:]}")

        print("\nPreview do DataFrame:")
        print(items_df.head(20).to_string(index=False))

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
