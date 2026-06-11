"""Cliente base para integracao com a API Seconds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


class SecondsAPIError(RuntimeError):
    """Erro padronizado da integracao Seconds."""


@dataclass
class SecondsProductCost:
    mlb: str
    sku: str | None
    product_cost: float
    sale_price: float | None = None


class SecondsAPI:
    """Cliente generico para custos por MLB/IdMeliItem.

    Como a especificacao exata dos endpoints Seconds pode variar por conta,
    este cliente centraliza headers, erros e normalizacao para ajustes futuros.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        response = self.session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        if response.ok:
            return response.json()
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise SecondsAPIError(f"Erro Seconds: HTTP {response.status_code} - {detail}")

    def get_product_by_mlb(self, mlb: str) -> SecondsProductCost | None:
        """Busca custo/preco por MLB. Ajuste o endpoint se a conta Seconds usar outra rota."""

        payload = self._get("/products", params={"IdMeliItem": mlb})
        row: dict[str, Any] | None = None

        if isinstance(payload, list) and payload:
            row = payload[0]
        elif isinstance(payload, dict):
            data = payload.get("data") or payload.get("results") or payload
            if isinstance(data, list) and data:
                row = data[0]
            elif isinstance(data, dict):
                row = data

        if not row:
            return None

        return SecondsProductCost(
            mlb=str(row.get("IdMeliItem") or row.get("mlb") or mlb),
            sku=row.get("sku") or row.get("SKU"),
            product_cost=float(row.get("cmv") or row.get("cost") or row.get("product_cost") or 0),
            sale_price=float(row.get("sale_price") or row.get("price") or 0) or None,
        )

    def get_costs_dataframe(self, mlbs: list[str]) -> pd.DataFrame:
        """Consulta uma lista de MLBs e retorna DataFrame normalizado."""

        rows = []
        for mlb in sorted(set(filter(None, mlbs))):
            product = self.get_product_by_mlb(mlb)
            if product:
                rows.append(product.__dict__)
        return pd.DataFrame(rows)
