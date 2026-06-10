"""Teste de acesso a Mercado Ads/Product Ads para descobrir advertiser_id."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ADVERTISERS_URL = "https://api.mercadolibre.com/advertising/advertisers"
TIMEOUT_SECONDS = 30
OUTPUT_PATH = Path("data") / "ml_ads_advertisers.csv"


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


def print_json(title: str, payload: dict[str, Any] | list[Any]) -> None:
    """Imprime JSON formatado no terminal."""

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

    response = requests.post(
        TOKEN_URL,
        data=payload,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )

    print(f"\nStatus token: {response.status_code}")
    try:
        token_data = response.json()
        print_json("RESPOSTA DA GERACAO DO TOKEN", token_data)
    except ValueError:
        print(response.text)
        token_data = {}

    response.raise_for_status()

    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("A resposta do Mercado Livre nao retornou access_token.")

    return access_token


def fetch_advertisers(access_token: str) -> tuple[requests.Response, dict[str, Any] | list[Any]]:
    """Consulta anunciantes com acesso a Product Ads."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Api-Version": "1",
    }
    params = {"product_id": "PADS"}

    response = requests.get(
        ADVERTISERS_URL,
        headers=headers,
        params=params,
        timeout=TIMEOUT_SECONDS,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_text": response.text}

    return response, payload


def explain_ads_error(status_code: int) -> str | None:
    """Retorna explicacao amigavel para erros comuns da API Ads."""

    if status_code == 401:
        return "Token possivelmente invalido ou expirado."
    if status_code in {403, 404}:
        return "Pode faltar permissao para Ads ou Product Ads ainda nao estar habilitado na conta."
    return None


def build_advertisers_dataframe(payload: dict[str, Any] | list[Any]) -> pd.DataFrame:
    """Normaliza anunciantes retornados pela API em DataFrame."""

    if not isinstance(payload, dict):
        return pd.DataFrame(columns=["advertiser_id", "site_id", "advertiser_name", "account_name"])

    advertisers = payload.get("advertisers", [])
    if not isinstance(advertisers, list):
        advertisers = []

    return pd.DataFrame(
        [
            {
                "advertiser_id": advertiser.get("advertiser_id"),
                "site_id": advertiser.get("site_id"),
                "advertiser_name": advertiser.get("advertiser_name"),
                "account_name": advertiser.get("account_name"),
            }
            for advertiser in advertisers
            if isinstance(advertiser, dict)
        ]
    )


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva DataFrame de anunciantes em CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame) -> None:
    """Exibe os principais campos encontrados."""

    print(f"\n{'=' * 80}")
    print("RESUMO DOS ADVERTISERS")
    print("=" * 80)

    if df.empty:
        print("Advertiser_id encontrado: N/D")
        print("site_id: N/D")
        print("advertiser_name: N/D")
        print("account_name: N/D")
        return

    first = df.iloc[0]
    print(f"Advertiser_id encontrado: {first['advertiser_id']}")
    print(f"site_id: {first['site_id']}")
    print(f"advertiser_name: {first['advertiser_name']}")
    print(f"account_name: {first['account_name']}")

    print("\nTodos os advertisers retornados:")
    print(df.to_string(index=False))


def main() -> None:
    """Executa o teste completo de advertisers Product Ads."""

    try:
        client_id, client_secret, refresh_token = load_credentials()
        access_token = generate_access_token(client_id, client_secret, refresh_token)

        response, payload = fetch_advertisers(access_token)
        print(f"\nStatus advertisers: {response.status_code}")
        print_json("RESPOSTA COMPLETA DA API DE ADVERTISERS", payload)

        explanation = explain_ads_error(response.status_code)
        if explanation:
            print(f"\nAviso: {explanation}")

        response.raise_for_status()

        advertisers_df = build_advertisers_dataframe(payload)
        save_dataframe(advertisers_df, OUTPUT_PATH)
        print_summary(advertisers_df)
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
