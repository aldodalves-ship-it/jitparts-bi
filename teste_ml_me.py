"""Teste de autenticacao Mercado Livre via refresh token.

Fluxo:
1. Gera um novo access_token usando ML_CLIENT_ID, ML_CLIENT_SECRET e
   ML_REFRESH_TOKEN do arquivo .env.
2. Consulta https://api.mercadolibre.com/users/me com o access_token gerado.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ME_URL = "https://api.mercadolibre.com/users/me"
TIMEOUT_SECONDS = 30


def load_credentials() -> tuple[str, str, str]:
    """Carrega as credenciais Mercado Livre do arquivo .env."""

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


def print_response(title: str, response: requests.Response) -> None:
    """Imprime status code e corpo da resposta em formato legivel."""

    print(f"\n{'=' * 80}")
    print(title)
    print("=" * 80)
    print(f"Status code: {response.status_code}")
    print("Resposta:")

    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(response.text)


def generate_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
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
    print_response("GERACAO DO ACCESS TOKEN", response)
    response.raise_for_status()
    return response.json()


def get_authenticated_user(access_token: str) -> dict:
    """Consulta os dados da conta autenticada no endpoint /users/me."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }

    response = requests.get(
        ME_URL,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )
    print_response("CONSULTA DO USUARIO AUTENTICADO (/users/me)", response)
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Executa o teste completo de autenticacao e consulta do usuario."""

    try:
        client_id, client_secret, refresh_token = load_credentials()
        token_data = generate_access_token(client_id, client_secret, refresh_token)

        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError("A resposta do token nao retornou access_token.")

        get_authenticated_user(access_token)

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
