"""Teste de consulta/atualizacao de CMV na API Seconds.

Objetivo: verificar se o endpoint /beta/items/cost retorna o CMV atual ou se
apenas executa atualizacao de custo conforme payload enviado.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


TIMEOUT_SECONDS = 30
ENDPOINT = "/beta/items/cost"


def build_url(base_url: str) -> str:
    """Monta a URL final garantindo apenas uma barra entre base e endpoint."""

    return f"{base_url.rstrip('/')}{ENDPOINT}"


def main() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    base_url = os.getenv("SECONDS_BASE_URL", "").strip()
    api_key = os.getenv("SECONDS_API_KEY", "").strip()

    if not base_url:
        raise ValueError("SECONDS_BASE_URL nao encontrado no arquivo .env.")
    if not api_key:
        raise ValueError("SECONDS_API_KEY nao encontrado no arquivo .env.")

    url = build_url(base_url)
    payload = [
        {
            "IdMeliItem": "MLB5694691462",
            "Cost": 0.01,
        }
    ]
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
    }

    print("URL utilizada:")
    print(url)
    print("\nPayload enviado:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        response = requests.put(
            url,
            headers=headers,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )

        print("\nStatus code:")
        print(response.status_code)
        print("\nResposta completa da API:")

        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            print(response.text)

        response.raise_for_status()

    except requests.exceptions.Timeout:
        print(f"\nErro: timeout apos {TIMEOUT_SECONDS} segundos.")
    except requests.exceptions.HTTPError as exc:
        print(f"\nErro HTTP: {exc}")
    except requests.exceptions.RequestException as exc:
        print(f"\nErro de requisicao: {exc}")


if __name__ == "__main__":
    main()
