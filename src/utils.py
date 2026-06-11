"""Utilitarios compartilhados do dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppConfig:
    """Configuracoes centrais carregadas do ambiente."""

    ml_client_id: str
    ml_client_secret: str
    ml_refresh_token: str
    ml_seller_id: str
    ml_site_id: str
    seconds_base_url: str
    seconds_api_key: str
    duckdb_path: str
    app_env: str

    @property
    def has_mercado_livre_credentials(self) -> bool:
        return all(
            [
                self.ml_client_id,
                self.ml_client_secret,
                self.ml_refresh_token,
                self.ml_seller_id,
            ]
        )

    @property
    def has_seconds_credentials(self) -> bool:
        return bool(self.seconds_base_url and self.seconds_api_key)


def load_config() -> AppConfig:
    """Carrega variaveis do .env e retorna uma configuracao tipada."""

    load_dotenv(ROOT_DIR / ".env")
    return AppConfig(
        ml_client_id=os.getenv("ML_CLIENT_ID", ""),
        ml_client_secret=os.getenv("ML_CLIENT_SECRET", ""),
        ml_refresh_token=os.getenv("ML_REFRESH_TOKEN", ""),
        ml_seller_id=os.getenv("ML_SELLER_ID", ""),
        ml_site_id=os.getenv("ML_SITE_ID", "MLB"),
        seconds_base_url=os.getenv("SECONDS_BASE_URL", ""),
        seconds_api_key=os.getenv("SECONDS_API_KEY", ""),
        duckdb_path=os.getenv("DUCKDB_PATH", "data/jitparts.duckdb"),
        app_env=os.getenv("APP_ENV", "development"),
    )


def format_currency(value: float | int | None) -> str:
    """Formata valores monetarios em BRL."""

    if value is None:
        value = 0
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_number(value: float | int | None, decimals: int = 0) -> str:
    """Formata numeros no padrao brasileiro."""

    if value is None:
        value = 0
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float | int | None, decimals: int = 1) -> str:
    """Formata percentuais."""

    if value is None:
        value = 0
    return f"{value:.{decimals}f}%".replace(".", ",")


def inject_global_css() -> str:
    """CSS executivo para Streamlit, mantendo compatibilidade dark/light."""

    return """
    <style>
        :root {
            --jit-accent: #00A884;
            --jit-accent-2: #2563EB;
            --jit-warning: #F59E0B;
            --jit-danger: #DC2626;
            --jit-card-radius: 8px;
        }

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1480px;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.16);
        }

        .jit-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.15rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.18);
            padding-bottom: 1rem;
        }

        .jit-title {
            font-size: clamp(1.45rem, 2.2vw, 2.25rem);
            font-weight: 800;
            line-height: 1.05;
            margin: 0;
            letter-spacing: 0;
        }

        .jit-subtitle {
            margin: 0.35rem 0 0 0;
            color: rgba(125, 125, 125, 0.96);
            font-size: 0.95rem;
        }

        .jit-badge {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .metric-card {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: var(--jit-card-radius);
            padding: 0.92rem 0.95rem;
            min-height: 112px;
            background: color-mix(in srgb, var(--background-color) 92%, var(--jit-accent) 8%);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
        }

        .metric-label {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0;
            color: rgba(125, 125, 125, 0.96);
            font-weight: 800;
            margin-bottom: 0.45rem;
        }

        .metric-value {
            font-size: clamp(1.18rem, 1.8vw, 1.72rem);
            font-weight: 850;
            line-height: 1.12;
            margin-bottom: 0.42rem;
            word-break: break-word;
        }

        .metric-delta {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--jit-accent);
        }

        .metric-delta.negative {
            color: var(--jit-danger);
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin: 0.25rem 0 0.5rem 0;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.16);
            border-radius: var(--jit-card-radius);
            padding: 0.75rem 0.85rem;
        }

        @media (max-width: 768px) {
            .jit-header {
                display: block;
            }
            .jit-badge {
                display: inline-block;
                margin-top: 0.8rem;
            }
        }
    </style>
    """


def metric_card(label: str, value: str, delta: str | None = None, negative: bool = False) -> str:
    """Retorna um card KPI em HTML seguro para markdown."""

    delta_html = ""
    if delta:
        delta_class = "metric-delta negative" if negative else "metric-delta"
        delta_html = f'<div class="{delta_class}">{delta}</div>'

    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """
