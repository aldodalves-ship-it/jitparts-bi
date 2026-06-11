"""Bootstrap do pipeline de dados para Streamlit Cloud.

Quando o dashboard_base_final.csv nao existe (deploy sem CSV),
este modulo executa o pipeline de coleta e merge automaticamente.

Fluxo:
  1. Injeta credenciais ML do st.secrets no ambiente (se cloud)
  2. Coleta pedidos, shipments, items e ads via API ML
  3. Roda merge_ml_seconds.py para gerar dashboard_base_final.csv
  4. Exibe progresso via st.progress no Streamlit

Nao altera: logica financeira, DRE, calculos, merges existentes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

# Imports opcionais — so importa streamlit se estiver rodando via st
try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

# Arquivo principal que indica que o pipeline ja foi executado
DASHBOARD_CSV = DATA_DIR / "dashboard_base_final.csv"

# Scripts de coleta (em ordem de execucao)
PIPELINE_SCRIPTS: list[tuple[str, str, Path]] = [
    # (label_ui, script, arquivo_de_saida_esperado)
    ("Coletando pedidos ML...",     "teste_ml_orders.py",        DATA_DIR / "ml_orders.csv"),
    ("Coletando fretes ML...",      "teste_ml_shipments.py",     DATA_DIR / "ml_shipments.csv"),
    ("Coletando anuncios ML...",    "teste_ml_items.py",         DATA_DIR / "ml_items.csv"),
    ("Coletando detalhes...",       "teste_ml_item_details.py",  DATA_DIR / "ml_items_details.csv"),
    ("Coletando campanhas Ads...",  "teste_ml_ads_campaigns.py", DATA_DIR / "ml_ads_campaigns.csv"),
    ("Coletando metricas Ads...",   "teste_ml_ads_metrics.py",   DATA_DIR / "ml_ads_metrics.csv"),
    ("Gerando base consolidada...", "merge_ml_seconds.py",       DASHBOARD_CSV),
]


# ---------------------------------------------------------------------------
# Injecao de credenciais (cloud: st.secrets → env; local: .env via dotenv)
# ---------------------------------------------------------------------------

def inject_credentials_from_secrets() -> bool:
    """Injeta credenciais ML do st.secrets no os.environ.

    Retorna True se as credenciais foram encontradas e injetadas.
    Requer que o Streamlit Cloud tenha em Settings > Secrets:
        [mercadolivre]
        ML_CLIENT_ID     = "..."
        ML_CLIENT_SECRET = "..."
        ML_REFRESH_TOKEN = "..."
        ML_SELLER_ID     = "..."
    """
    if not _HAS_ST:
        return False

    try:
        secrets = st.secrets.get("mercadolivre", {})
        if not secrets:
            return False

        for key in ["ML_CLIENT_ID", "ML_CLIENT_SECRET", "ML_REFRESH_TOKEN", "ML_SELLER_ID"]:
            value = secrets.get(key, "")
            if value:
                os.environ[key] = str(value)

        return bool(os.environ.get("ML_CLIENT_ID"))
    except Exception:
        return False


def inject_credentials_from_dotenv() -> bool:
    """Carrega credenciais do arquivo .env local (ambiente de desenvolvimento)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return False
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return bool(os.environ.get("ML_CLIENT_ID"))
    except ImportError:
        return False


def has_credentials() -> bool:
    """Verifica se as credenciais ML estao disponíveis no ambiente."""
    return bool(os.environ.get("ML_CLIENT_ID") and os.environ.get("ML_REFRESH_TOKEN"))


# ---------------------------------------------------------------------------
# Execucao de scripts do pipeline
# ---------------------------------------------------------------------------

def _run_script(
    script: str,
    label: str,
    progress_fn: Callable[[float, str], None] | None = None,
    step_pct: float = 0.0,
) -> tuple[bool, str]:
    """Executa um script Python do pipeline. Retorna (sucesso, mensagem)."""
    script_path = ROOT / script
    if not script_path.exists():
        return False, f"Script nao encontrado: {script}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60 * 20,  # 20 min max por etapa
            check=False,
        )
        if result.returncode != 0:
            erro = (result.stderr or result.stdout or "Erro desconhecido")[:500]
            return False, f"{label} falhou: {erro}"

        if progress_fn:
            progress_fn(step_pct, label + " ✓")
        return True, label + " concluido."

    except subprocess.TimeoutExpired:
        return False, f"{label} excedeu o tempo limite (20 min)."
    except Exception as exc:
        return False, f"{label} erro inesperado: {exc}"


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def needs_bootstrap() -> bool:
    """Retorna True se o pipeline precisa ser executado."""
    return not DASHBOARD_CSV.exists() or DASHBOARD_CSV.stat().st_size < 1_000


def run_pipeline_with_ui() -> bool:
    """Executa o pipeline completo com feedback visual no Streamlit.

    Retorna True se o pipeline concluiu com sucesso.
    Exibe erros amigaveis via st.error se algo falhar.
    """
    if not _HAS_ST:
        return run_pipeline_silent()

    # Garantir pasta data/
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    st.markdown("---")
    st.subheader("⏳ Gerando base de dados...")
    st.caption(
        "Primeira execucao: coletando dados do Mercado Livre e gerando a base do dashboard. "
        "Isso pode levar alguns minutos."
    )

    progress_bar = st.progress(0, text="Iniciando pipeline...")
    status_box = st.empty()
    n = len(PIPELINE_SCRIPTS)

    for i, (label, script, output_path) in enumerate(PIPELINE_SCRIPTS):
        pct = int((i / n) * 100)
        progress_bar.progress(pct, text=label)
        status_box.info(f"🔄 {label}")

        # Se o arquivo de saida ja existe, pular (idempotente)
        if output_path.exists() and output_path.stat().st_size > 100:
            status_box.success(f"✅ {label} (ja existe, pulado)")
            continue

        success, msg = _run_script(script, label)
        if not success:
            progress_bar.progress(pct, text="Erro no pipeline")
            status_box.empty()
            st.error(
                f"❌ **Falha no pipeline:** {msg}\n\n"
                "Verifique:\n"
                "- Credenciais ML em **Settings → Secrets**\n"
                "- Conectividade com a API do Mercado Livre\n"
                "- Logs para detalhes"
            )
            with st.expander("Detalhes do erro"):
                st.code(msg)
            return False

        status_box.success(f"✅ {msg}")

    progress_bar.progress(100, text="Base de dados gerada com sucesso!")
    status_box.empty()
    st.success("✅ Base de dados gerada. Carregando dashboard...")
    st.cache_data.clear()
    return True


def run_pipeline_silent() -> bool:
    """Executa o pipeline sem UI (modo CLI / testes). Retorna True se ok."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for label, script, output_path in PIPELINE_SCRIPTS:
        if output_path.exists() and output_path.stat().st_size > 100:
            print(f"[SKIP] {label} — arquivo ja existe")
            continue
        print(f"[RUN ] {label}")
        success, msg = _run_script(script, label)
        if not success:
            print(f"[ERRO] {msg}")
            return False
        print(f"[OK  ] {msg}")

    return True


# ---------------------------------------------------------------------------
# Ponto de entrada — chamado pelo app.py antes de carregar dados
# ---------------------------------------------------------------------------

def ensure_data_ready(show_ui: bool = True) -> bool:
    """Garante que dashboard_base_final.csv existe.

    1. Injeta credenciais (st.secrets > .env)
    2. Se o CSV ja existe → retorna True imediatamente
    3. Se nao existe → roda pipeline (com ou sem UI)

    Retorna True se os dados estao prontos para uso.
    """
    # Injetar credenciais: cloud primeiro, depois .env local
    inject_credentials_from_secrets() or inject_credentials_from_dotenv()

    if not needs_bootstrap():
        return True

    if not has_credentials():
        if _HAS_ST and show_ui:
            st.error(
                "⚠️ **Dados nao encontrados e credenciais ML ausentes.**\n\n"
                "Para gerar os dados automaticamente, configure em "
                "**Settings → Secrets** do Streamlit Cloud:\n\n"
                "```toml\n"
                "[mercadolivre]\n"
                "ML_CLIENT_ID     = \"seu_client_id\"\n"
                "ML_CLIENT_SECRET = \"seu_client_secret\"\n"
                "ML_REFRESH_TOKEN = \"seu_refresh_token\"\n"
                "ML_SELLER_ID     = \"seu_seller_id\"\n"
                "```\n\n"
                "Ou faca upload manual dos arquivos CSV na pasta `data/`."
            )
            st.stop()
        return False

    if show_ui and _HAS_ST:
        return run_pipeline_with_ui()
    return run_pipeline_silent()
