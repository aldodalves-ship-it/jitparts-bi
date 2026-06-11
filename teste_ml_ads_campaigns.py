"""Teste de campanhas Product Ads da conta Mercado Livre Ads."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
CAMPAIGNS_URL = "https://api.mercadolibre.com/marketplace/advertising/MLB/advertisers/162123/product_ads/campaigns/search"
TIMEOUT_SECONDS = 30
DATE_FROM = "2026-05-01"
DATE_TO = "2026-05-15"
PAGE_LIMIT = 50
PAGE_OFFSET = 0
OUTPUT_PATH = Path("data") / "ml_ads_campaigns.csv"


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


def fetch_campaigns(access_token: str) -> tuple[requests.Response, dict[str, Any] | list[Any]]:
    """Consulta campanhas Product Ads no endpoint solicitado."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Api-Version": "2",
    }
    params = {
        "limit": PAGE_LIMIT,
        "offset": PAGE_OFFSET,
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
    }

    response = requests.get(
        CAMPAIGNS_URL,
        headers=headers,
        params=params,
        timeout=TIMEOUT_SECONDS,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_text": response.text}

    return response, payload


def explain_campaigns_error(status_code: int) -> str | None:
    """Retorna explicacao amigavel para erros comuns da API Ads."""

    if status_code == 401:
        return "Token possivelmente invalido ou expirado."
    if status_code == 403:
        return "Sem permissao para consultar campanhas Product Ads."
    if status_code == 404:
        return "Endpoint ou campanhas indisponiveis para a conta consultada."
    if status_code == 405:
        return "Metodo nao permitido para o endpoint consultado."
    return None


def nested_metric(campaign: dict[str, Any], key: str) -> Any:
    """Busca metricas no topo ou em blocos aninhados comuns."""

    if key in campaign:
        return campaign.get(key)

    for container_key in ("metrics", "summary", "totals"):
        container = campaign.get(container_key)
        if isinstance(container, dict) and key in container:
            return container.get(key)

    return None


def extract_campaign_rows(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    """Extrai campanhas aceitando formatos comuns de resposta."""

    if isinstance(payload, list):
        campaigns = payload
    elif isinstance(payload, dict):
        campaigns = payload.get("results") or payload.get("campaigns") or []
    else:
        campaigns = []

    rows: list[dict[str, Any]] = []
    for campaign in campaigns:
        if not isinstance(campaign, dict):
            continue
        rows.append(
            {
                "campaign_id": campaign.get("campaign_id") or campaign.get("id"),
                "name": campaign.get("name"),
                "status": campaign.get("status"),
                "budget": campaign.get("budget"),
                "acos_target": campaign.get("acos_target"),
                "strategy": campaign.get("strategy"),
                "impressions": nested_metric(campaign, "impressions") or nested_metric(campaign, "prints"),
                "clicks": nested_metric(campaign, "clicks"),
                "cost": nested_metric(campaign, "cost"),
                "revenue": nested_metric(campaign, "revenue") or nested_metric(campaign, "total_amount"),
                "orders": nested_metric(campaign, "orders") or nested_metric(campaign, "units_quantity"),
                "acos": nested_metric(campaign, "acos"),
                "roas": nested_metric(campaign, "roas"),
            }
        )
    return rows


def build_campaigns_dataframe(payload: dict[str, Any] | list[Any]) -> pd.DataFrame:
    """Monta DataFrame pandas com campanhas normalizadas."""

    df = pd.DataFrame(extract_campaign_rows(payload))
    if not df.empty:
        numeric_columns = [
            "budget",
            "acos_target",
            "impressions",
            "clicks",
            "cost",
            "revenue",
            "orders",
            "acos",
            "roas",
        ]
        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva campanhas em CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame) -> None:
    """Exibe resumo das campanhas retornadas."""

    print(f"\n{'=' * 80}")
    print("RESUMO DAS CAMPANHAS PRODUCT ADS")
    print("=" * 80)
    print(f"Quantidade de campanhas: {len(df)}")

    if df.empty:
        print("Nenhuma campanha retornada.")
        return

    display_columns = [
        "campaign_id",
        "name",
        "status",
        "budget",
        "acos_target",
        "strategy",
        "impressions",
        "clicks",
        "cost",
        "revenue",
        "orders",
        "acos",
        "roas",
    ]
    print(df[display_columns].to_string(index=False))


def main() -> None:
    """Executa o teste completo de campanhas Product Ads."""

    try:
        client_id, client_secret, refresh_token = load_credentials()
        access_token = generate_access_token(client_id, client_secret, refresh_token)

        response, payload = fetch_campaigns(access_token)
        print(f"\nStatus campaigns: {response.status_code}")
        print_json("RESPOSTA COMPLETA DA API DE CAMPANHAS", payload)

        explanation = explain_campaigns_error(response.status_code)
        if explanation:
            print(f"\nAviso: {explanation}")

        response.raise_for_status()

        campaigns_df = build_campaigns_dataframe(payload)
        save_dataframe(campaigns_df, OUTPUT_PATH)
        print_summary(campaigns_df)
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
