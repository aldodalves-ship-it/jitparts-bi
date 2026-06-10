"""Coleta metricas de campanhas Mercado Ads/Product Ads."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
CAMPAIGNS_INPUT_PATH = Path("data") / "ml_ads_campaigns.csv"
OUTPUT_PATH = Path("data") / "ml_ads_metrics.csv"

ADVERTISER_ID = 162123
SITE_ID = "MLB"
DATA_INICIO = "2026-05-01"
DATA_FIM = date.today().isoformat()
APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
TIMEOUT_SECONDS = 30
PAGE_LIMIT = 50
PAGE_OFFSET = 0

METRICS = [
    "clicks",
    "prints",
    "ctr",
    "cost",
    "cpc",
    "acos",
    "cvr",
    "roas",
    "units_quantity",
    "total_amount",
]

OUTPUT_COLUMNS = [
    "campaign_id",
    "campaign_name",
    "impressions",
    "clicks",
    "cost",
    "cpc",
    "ctr",
    "revenue",
    "orders",
    "units",
    "acos",
    "roas",
    "conversion_rate",
    "date_from",
    "date_to",
    "periodo_inicio",
    "periodo_fim",
    "data_ref",
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


def load_campaigns(path: Path) -> pd.DataFrame:
    """Le campanhas que servem de entrada para a coleta de metricas."""

    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    df = pd.read_csv(path)
    if "campaign_id" not in df.columns:
        raise ValueError("data/ml_ads_campaigns.csv precisa conter a coluna campaign_id.")

    df["campaign_id"] = pd.to_numeric(df["campaign_id"], errors="coerce")
    df = df.dropna(subset=["campaign_id"]).copy()
    df["campaign_id"] = df["campaign_id"].astype("int64")
    if "name" not in df.columns:
        df["name"] = pd.NA
    return df.drop_duplicates(subset=["campaign_id"], keep="last")


def ads_headers(access_token: str) -> dict[str, str]:
    """Monta headers padrao de Product Ads."""

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Api-Version": "2",
    }


def build_url(url: str, params: dict[str, Any]) -> str:
    """Monta URL completa para logs de erro."""

    return f"{url}?{urlencode(params)}"


def request_json(
    access_token: str,
    url: str,
    params: dict[str, Any],
) -> tuple[requests.Response, dict[str, Any] | list[Any]]:
    """Executa GET e retorna resposta + JSON."""

    response = requests.get(
        url,
        headers=ads_headers(access_token),
        params=params,
        timeout=TIMEOUT_SECONDS,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_text": response.text}
    return response, payload


def explain_ads_error(status_code: int) -> str | None:
    """Retorna explicacao amigavel para erros comuns."""

    if status_code == 401:
        return "Token possivelmente invalido ou expirado."
    if status_code == 403:
        return "Sem permissao para consultar metricas Product Ads."
    if status_code == 404:
        return "Endpoint ou recurso de metricas indisponivel."
    if status_code == 405:
        return "Metodo nao permitido para o endpoint consultado."
    return None


def iter_days(start_date: date, end_date: date) -> list[date]:
    """Retorna todos os dias do intervalo, inclusive."""

    if start_date > end_date:
        raise ValueError("DATA_INICIO deve ser menor ou igual a DATA_FIM.")

    total_days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(total_days + 1)]


def to_local_datetime(day: date) -> datetime:
    """Converte um dia em datetime com timezone America/Sao_Paulo."""

    return datetime.combine(day, time.min, tzinfo=APP_TIMEZONE)


def detail_endpoint(campaign_id: int, day: date) -> tuple[str, dict[str, Any]]:
    """Endpoint oficial de detalhe de campanha com metricas."""

    url = f"https://api.mercadolibre.com/advertising/{SITE_ID}/product_ads/campaigns/{campaign_id}"
    day_text = day.isoformat()
    params = {
        "date_from": day_text,
        "date_to": day_text,
        "metrics": ",".join(METRICS),
    }
    return url, params


def summary_endpoint(day: date) -> tuple[str, dict[str, Any]]:
    """Endpoint oficial de busca com metricas sumarizadas."""

    url = (
        f"https://api.mercadolibre.com/advertising/{SITE_ID}/advertisers/"
        f"{ADVERTISER_ID}/product_ads/campaigns/search"
    )
    day_text = day.isoformat()
    params = {
        "limit": PAGE_LIMIT,
        "offset": PAGE_OFFSET,
        "date_from": day_text,
        "date_to": day_text,
        "metrics": ",".join(METRICS),
        "metrics_summary": "true",
    }
    return url, params


def nested_metric(payload: dict[str, Any], key: str) -> Any:
    """Busca metricas em blocos comuns da resposta."""

    if key in payload:
        return payload.get(key)

    for container_key in ("metrics", "summary", "totals"):
        container = payload.get(container_key)
        if isinstance(container, dict) and key in container:
            return container.get(key)

    return None


def extract_daily_metric_date(payload: dict[str, Any]) -> Any:
    """Busca uma data diaria quando a API a fornecer junto da metrica."""

    candidate_keys = ["data_ref", "metric_date", "date", "day", "data"]
    for key in candidate_keys:
        value = payload.get(key)
        if value:
            return value

    for container_key in ("metrics", "summary", "totals"):
        container = payload.get(container_key)
        if not isinstance(container, dict):
            continue
        for key in candidate_keys:
            value = container.get(key)
            if value:
                return value

    return None


def normalize_metrics_row(
    campaign_id: int,
    campaign_name: str | None,
    payload: dict[str, Any],
    day: date,
) -> dict[str, Any]:
    """Normaliza a resposta de metricas em uma unica linha."""

    prints = nested_metric(payload, "prints")
    total_amount = nested_metric(payload, "total_amount")
    units_quantity = nested_metric(payload, "units_quantity")
    metric_date = pd.to_datetime(extract_daily_metric_date(payload), errors="coerce")
    data_ref = (
        metric_date.tz_localize(APP_TIMEZONE)
        if not pd.isna(metric_date) and metric_date.tzinfo is None
        else metric_date.tz_convert(APP_TIMEZONE)
        if not pd.isna(metric_date)
        else to_local_datetime(day)
    )
    day_start = to_local_datetime(day)

    return {
        "campaign_id": campaign_id,
        "campaign_name": payload.get("name") or campaign_name,
        "impressions": nested_metric(payload, "impressions") or prints,
        "clicks": nested_metric(payload, "clicks"),
        "cost": nested_metric(payload, "cost"),
        "cpc": nested_metric(payload, "cpc"),
        "ctr": nested_metric(payload, "ctr"),
        "revenue": nested_metric(payload, "revenue") or total_amount,
        "orders": nested_metric(payload, "orders"),
        "units": nested_metric(payload, "units") or units_quantity,
        "acos": nested_metric(payload, "acos"),
        "roas": nested_metric(payload, "roas"),
        "conversion_rate": nested_metric(payload, "conversion_rate") or nested_metric(payload, "cvr"),
        "date_from": day_start,
        "date_to": day_start,
        "periodo_inicio": day_start,
        "periodo_fim": day_start,
        "data_ref": data_ref,
    }


def extract_summary_map(payload: dict[str, Any] | list[Any]) -> dict[int, dict[str, Any]]:
    """Indexa metricas sumarizadas por campaign_id."""

    if isinstance(payload, dict):
        campaigns = payload.get("results") or payload.get("campaigns") or []
    elif isinstance(payload, list):
        campaigns = payload
    else:
        campaigns = []

    result: dict[int, dict[str, Any]] = {}
    for campaign in campaigns:
        if not isinstance(campaign, dict):
            continue
        campaign_id = campaign.get("campaign_id") or campaign.get("id")
        if campaign_id is None:
            continue
        try:
            result[int(campaign_id)] = campaign
        except (TypeError, ValueError):
            continue
    return result


def fetch_summary_fallback(access_token: str, day: date) -> dict[int, dict[str, Any]]:
    """Busca metricas resumidas do dia para fallback por campanha."""

    url, params = summary_endpoint(day)
    response, payload = request_json(access_token, url, params)
    print(f"\nStatus summary {day.isoformat()}: {response.status_code}")
    if response.status_code >= 400:
        print(f"URL testada: {build_url(url, params)}")
        explanation = explain_ads_error(response.status_code)
        if explanation:
            print(f"Aviso: {explanation}")
    else:
        print_json("RESPOSTA COMPLETA DO SUMMARY DE CAMPANHAS", payload)

    if response.ok:
        return extract_summary_map(payload)
    return {}


def fetch_campaign_metrics(
    access_token: str,
    campaign_id: int,
    campaign_name: str | None,
    summary_map: dict[int, dict[str, Any]],
    day: date,
) -> dict[str, Any] | None:
    """Tenta detalhe individual; usa summary quando necessario."""

    url, params = detail_endpoint(campaign_id, day)
    response, payload = request_json(access_token, url, params)
    print(f"\nStatus campaign {campaign_id} em {day.isoformat()}: {response.status_code}")

    if response.ok and isinstance(payload, dict):
        return normalize_metrics_row(campaign_id, campaign_name, payload, day)

    print(f"URL testada: {build_url(url, params)}")
    explanation = explain_ads_error(response.status_code)
    if explanation:
        print(f"Aviso: {explanation}")

    summary_payload = summary_map.get(campaign_id)
    if summary_payload:
        print(f"Usando fallback summary para campaign_id={campaign_id} em {day.isoformat()}")
        return normalize_metrics_row(campaign_id, campaign_name, summary_payload, day)

    return None


def build_metrics_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Monta DataFrame final de metricas."""

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    numeric_columns = [
        "impressions",
        "clicks",
        "cost",
        "cpc",
        "ctr",
        "revenue",
        "orders",
        "units",
        "acos",
        "roas",
        "conversion_rate",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in ["periodo_inicio", "periodo_fim", "data_ref"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True).dt.tz_convert(APP_TIMEZONE)

    for column in ["date_from", "date_to"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True).dt.tz_convert(APP_TIMEZONE)

    return df.reindex(columns=OUTPUT_COLUMNS)


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Salva metricas em CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def print_summary(df: pd.DataFrame, total_days: int, days_with_data: int) -> None:
    """Exibe resumo executivo de Ads."""

    cost_total = float(df["cost"].sum()) if not df.empty and "cost" in df.columns else 0.0
    revenue_total = float(df["revenue"].sum()) if not df.empty and "revenue" in df.columns else 0.0
    clicks_total = int(df["clicks"].sum()) if not df.empty and "clicks" in df.columns else 0
    impressions_total = int(df["impressions"].sum()) if not df.empty and "impressions" in df.columns else 0
    roas = (revenue_total / cost_total) if cost_total else 0.0
    acos = (cost_total / revenue_total * 100) if revenue_total else 0.0
    campaigns_with_data = int(df["campaign_id"].nunique()) if not df.empty else 0

    print(f"\n{'=' * 80}")
    print("RESUMO DE METRICAS PRODUCT ADS")
    print("=" * 80)
    print(
        f"Periodo Ads consultado: "
        f"{pd.to_datetime(DATA_INICIO).strftime('%d/%m/%Y')} a {pd.to_datetime(DATA_FIM).strftime('%d/%m/%Y')}"
    )
    print(f"Dias coletados: {total_days}")
    print(f"Dias com dados: {days_with_data}")
    print(f"Custo total: R$ {cost_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"Receita Ads: R$ {revenue_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"ROAS: {roas:.2f}".replace(".", ","))
    print(f"ACOS: {acos:.2f}%".replace(".", ","))
    print(f"Cliques: {clicks_total}")
    print(f"Impressoes: {impressions_total}")
    print(f"Campanhas com dados: {campaigns_with_data}")

    print("\nPreview do DataFrame:")
    if df.empty:
        print("Nenhuma metrica retornada.")
    else:
        print(df.head(20).to_string(index=False))


def main() -> None:
    """Executa a coleta completa de metricas Product Ads."""

    try:
        client_id, client_secret, refresh_token = load_credentials()
        campaigns_df = load_campaigns(CAMPAIGNS_INPUT_PATH)
        access_token = generate_access_token(client_id, client_secret, refresh_token)

        start_date = date.fromisoformat(DATA_INICIO)
        end_date = date.fromisoformat(DATA_FIM)
        days = iter_days(start_date, end_date)
        rows: list[dict[str, Any]] = []
        days_with_data = 0

        for day in days:
            print(f"\n{'-' * 80}")
            print(f"Coletando Ads do dia {day:%d/%m/%Y}")
            print("-" * 80)

            try:
                summary_map = fetch_summary_fallback(access_token, day)
                day_rows: list[dict[str, Any]] = []
                for campaign in campaigns_df.itertuples(index=False):
                    row = fetch_campaign_metrics(
                        access_token,
                        int(campaign.campaign_id),
                        getattr(campaign, "name", None),
                        summary_map,
                        day,
                    )
                    if row:
                        day_rows.append(row)

                if day_rows:
                    rows.extend(day_rows)
                    days_with_data += 1
                    print(f"Dia {day:%d/%m/%Y}: {len(day_rows)} campanhas com dados.")
                else:
                    print(f"Dia {day:%d/%m/%Y}: sem dados retornados.")
            except requests.exceptions.RequestException as exc:
                print(f"Dia {day:%d/%m/%Y}: erro de requisicao - {exc}")

        metrics_df = build_metrics_dataframe(rows)
        save_dataframe(metrics_df, OUTPUT_PATH)
        print_summary(metrics_df, total_days=len(days), days_with_data=days_with_data)
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
