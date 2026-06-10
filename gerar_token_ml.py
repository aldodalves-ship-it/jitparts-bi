import os
import requests
import webbrowser
from urllib.parse import urlencode
from dotenv import load_dotenv
from pathlib import Path

# CARREGA O .ENV EXPLICITAMENTE
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

print("Lendo .env em:")
print(env_path)

# LÊ AS VARIÁVEIS DO .ENV
CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

print("\nCLIENT_ID:")
print(CLIENT_ID)

# VALIDAÇÕES
if not CLIENT_ID:
    raise ValueError("ML_CLIENT_ID não encontrado no .env")

if not CLIENT_SECRET:
    raise ValueError("ML_CLIENT_SECRET não encontrado no .env")

if not REDIRECT_URI:
    raise ValueError("ML_REDIRECT_URI não encontrado no .env")

# PARAMETROS OAUTH
params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
}

# URL DE AUTORIZAÇÃO
url_autorizacao = (
    "https://auth.mercadolivre.com.br/authorization?"
    + urlencode(params)
)

print("\nAbra este link no navegador:\n")
print(url_autorizacao)

# ABRE O NAVEGADOR
webbrowser.open(url_autorizacao)

# RECEBE O CODE
code = input("\nCole aqui somente o CODE da URL: ").strip()

# ENDPOINT TOKEN
url_token = "https://api.mercadolibre.com/oauth/token"

payload = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "redirect_uri": REDIRECT_URI,
}

headers = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
}

# REQUEST TOKEN
resposta = requests.post(
    url_token,
    data=payload,
    headers=headers,
    timeout=30
)

print("\nSTATUS:")
print(resposta.status_code)

print("\nRESPOSTA:")
print(resposta.text)