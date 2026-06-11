"""Cliente base para a API do Mercado Livre.

O modulo isola autenticacao OAuth, renovacao de token, paginacao e chamadas
operacionais para que o dashboard possa crescer sem acoplar API ao Streamlit.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


class MercadoLivreAPIError(RuntimeError):
    """Erro padronizado da integracao Mercado Livre."""


@dataclass
class TokenState:
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0
    user_id: str | int | None = None

    def is_valid(self, safety_window_seconds: int = 120) -> bool:
        return bool(self.access_token) and time.time() < (self.expires_at - safety_window_seconds)


class MercadoLivreAPI:
    """Cliente REST Mercado Livre com OAuth e paginacao."""

    BASE_URL = "https://api.mercadolibre.com"
    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout: int = 30,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_state = TokenState(refresh_token=refresh_token)
        self.timeout = timeout
        self.session = requests.Session()

    def refresh_access_token(self) -> TokenState:
        """Renova o access_token usando o refresh_token atual."""

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.token_state.refresh_token,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }

        response = self.session.post(
            self.TOKEN_URL,
            data=payload,
            headers=headers,
            timeout=self.timeout,
        )
        self._raise_for_response(response, "Falha ao renovar token Mercado Livre")
        data = response.json()

        self.token_state = TokenState(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", self.token_state.refresh_token),
            expires_at=time.time() + int(data.get("expires_in", 0)),
            user_id=data.get("user_id"),
        )
        return self.token_state

    def _get_access_token(self) -> str:
        if not self.token_state.is_valid():
            self.refresh_access_token()
        return self.token_state.access_token

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        retry_on_unauthorized: bool = True,
    ) -> dict[str, Any] | list[Any]:
        """Executa uma requisicao autenticada com retry simples para 401."""

        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self._get_access_token()}"}
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json,
            timeout=self.timeout,
        )

        if response.status_code == 401 and retry_on_unauthorized:
            self.refresh_access_token()
            return self._request(method, endpoint, params, json, retry_on_unauthorized=False)

        self._raise_for_response(response, f"Erro Mercado Livre em {endpoint}")
        if response.text:
            return response.json()
        return {}

    @staticmethod
    def _raise_for_response(response: requests.Response, message: str) -> None:
        if response.ok:
            return
        detail: str
        try:
            detail = str(response.json())
        except ValueError:
            detail = response.text
        raise MercadoLivreAPIError(f"{message}: HTTP {response.status_code} - {detail}")

    def paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        results_key: str = "results",
        limit: int = 50,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Percorre endpoints paginados por limit/offset."""

        params = dict(params or {})
        params["limit"] = limit
        offset = int(params.get("offset", 0))
        records: list[dict[str, Any]] = []
        page = 0

        while True:
            params["offset"] = offset
            payload = self._request("GET", endpoint, params=params)
            if not isinstance(payload, dict):
                break

            page_records = payload.get(results_key, [])
            if not page_records:
                break

            records.extend(page_records)
            page += 1
            paging = payload.get("paging", {})
            total = int(paging.get("total", len(records)))
            offset += limit

            if offset >= total:
                break
            if max_pages is not None and page >= max_pages:
                break

        return records

    def get_orders(
        self,
        seller_id: str,
        date_from_iso: str | None = None,
        date_to_iso: str | None = None,
        status: str | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Busca pedidos do seller no endpoint orders/search."""

        params: dict[str, Any] = {"seller": seller_id, "sort": "date_desc"}
        if status:
            params["order.status"] = status
        if date_from_iso:
            params["order.date_created.from"] = date_from_iso
        if date_to_iso:
            params["order.date_created.to"] = date_to_iso
        return self.paginate("/orders/search", params=params, max_pages=max_pages)

    def get_items_by_seller(
        self,
        seller_id: str,
        status: str | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Lista anuncios do vendedor."""

        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        item_ids = self.paginate(
            f"/users/{seller_id}/items/search",
            params=params,
            results_key="results",
            max_pages=max_pages,
        )
        return [{"id": item_id} if isinstance(item_id, str) else item_id for item_id in item_ids]

    def get_items_details(self, item_ids: list[str], attributes: list[str] | None = None) -> list[dict[str, Any]]:
        """Busca detalhes em lotes de ate 20 itens."""

        if not item_ids:
            return []

        details: list[dict[str, Any]] = []
        for start in range(0, len(item_ids), 20):
            batch = item_ids[start : start + 20]
            params: dict[str, Any] = {"ids": ",".join(batch)}
            if attributes:
                params["attributes"] = ",".join(attributes)
            response = self._request("GET", "/items", params=params)
            if isinstance(response, list):
                details.extend([row.get("body", {}) for row in response if row.get("code") == 200])
        return details

    def get_shipment(self, shipment_id: str | int) -> dict[str, Any]:
        return self._request("GET", f"/shipments/{shipment_id}")  # type: ignore[return-value]

    def get_reputation(self, seller_id: str) -> dict[str, Any]:
        return self._request("GET", f"/users/{seller_id}")  # type: ignore[return-value]
