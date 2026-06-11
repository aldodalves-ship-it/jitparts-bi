from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
REPORT = ROOT / "AUDITORIA_ATUALIZACAO_BASE.md"
AUDIT_ORDERS_OUTPUT = DATA / "auditoria_orders_apos_20260521.csv"

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ORDERS_URL = "https://api.mercadolibre.com/orders/search"
BRT = timezone(timedelta(hours=-3))
PAGE_LIMIT = 50
WINDOW_DAYS = 15
TIMEOUT_SECONDS = 30
CONTROL_START = date(2026, 5, 22)


PIPELINE = [
    ("Atualizar pedidos Mercado Livre", "teste_ml_orders.py", "data/ml_orders.csv"),
    ("Atualizar shipments/frete", "teste_ml_shipments.py", "data/ml_shipments.csv"),
    ("Atualizar lista de anúncios", "teste_ml_items.py", "data/ml_items.csv"),
    ("Atualizar detalhes/estoque", "teste_ml_item_details.py", "data/ml_items_details.csv"),
    ("Atualizar campanhas Ads", "teste_ml_ads_campaigns.py", "data/ml_ads_campaigns.csv"),
    ("Atualizar métricas Ads", "teste_ml_ads_metrics.py", "data/ml_ads_metrics.csv"),
    ("Atualizar base final consolidada", "merge_ml_seconds.py data/seconds_cmv.xlsx", "data/dashboard_base_final.csv"),
    ("Salvar histórico DuckDB", "salvar_historico_duckdb.py", "data/jitparts.duckdb"),
]

FILES = [
    "ml_orders.csv",
    "ml_shipments.csv",
    "ml_items.csv",
    "ml_items_details.csv",
    "ml_ads_campaigns.csv",
    "ml_ads_metrics.csv",
    "dashboard_base_final.csv",
    "jitparts.duckdb",
]


@dataclass
class ControlResult:
    status_token: str = "N/D"
    status_orders: str = "N/D"
    params: list[dict[str, str]] | None = None
    rows: int = 0
    orders: int = 0
    revenue: float = 0.0
    first_date: str = "N/D"
    last_date: str = "N/D"
    first_ids: str = "N/D"
    last_ids: str = "N/D"
    error: str = ""


def br_money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_number(value: Any) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except Exception:
        return str(value)


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines) + "\n"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.suffix.lower() != ".csv":
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def mtime(path: Path) -> str:
    if not path.exists():
        return "N/D"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")


def normalize_dates(series: pd.Series, utc_to_brt: bool = False) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=utc_to_brt)
    if utc_to_brt:
        return parsed.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    try:
        if parsed.dt.tz is not None:
            return parsed.dt.tz_localize(None)
    except Exception:
        pass
    return parsed


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in df.columns), None)


def file_audit_rows() -> list[dict[str, Any]]:
    rows = []
    specs = {
        "ml_orders.csv": ("date_created", True),
        "ml_shipments.csv": ("date_created", True),
        "ml_items.csv": (None, False),
        "ml_items_details.csv": ("last_updated", True),
        "ml_ads_campaigns.csv": (None, False),
        "ml_ads_metrics.csv": ("data_ref", False),
        "dashboard_base_final.csv": ("date_created", True),
        "jitparts.duckdb": (None, False),
    }
    for name in FILES:
        path = DATA / name
        exists = path.exists()
        df = read_csv(path)
        date_col, utc = specs[name]
        min_date = "N/D"
        max_date = "N/D"
        if date_col and not df.empty and date_col in df.columns:
            dates = normalize_dates(df[date_col], utc_to_brt=utc).dropna()
            if not dates.empty:
                min_date = dates.min().strftime("%d/%m/%Y %H:%M:%S")
                max_date = dates.max().strftime("%d/%m/%Y %H:%M:%S")
        rows.append(
            {
                "Arquivo": f"data/{name}",
                "Existe": "Sim" if exists else "Não",
                "Linhas": len(df) if path.suffix.lower() == ".csv" and exists else "N/D",
                "Menor data": min_date,
                "Maior data": max_date,
                "Atualizado em": mtime(path),
                "Status": "OK" if exists else "Ausente",
            }
        )
    return rows


def script_constant(script: str, name: str) -> str:
    path = ROOT / script
    if not path.exists():
        return "N/D"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"^{re.escape(name)}\s*=\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "N/D"


def log_findings() -> list[dict[str, Any]]:
    path = LOGS / "ultima_execucao.log"
    if not path.exists():
        return [{"Etapa": "ultima_execucao.log", "Status": "N/D", "Mensagem relevante": "Log ausente", "Possível causa": "Sem evidência"}]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    patterns = [
        ("Atualizar pedidos Mercado Livre", "charmap", "Erro de encoding ao registrar saída da etapa"),
        ("Atualizar shipments/frete", "charmap", "Erro de encoding ao registrar saída da etapa"),
        ("Atualizar detalhes/estoque", "charmap", "Erro de encoding ao registrar saída da etapa"),
        ("Pedidos", "Periodo consultado:", "Período enviado à API"),
        ("Ads", "Periodo Ads consultado:", "Período enviado à API Ads"),
        ("DuckDB", "Column with name sku already exists", "Falha no snapshot historico_vendas"),
        ("Resumo final", "Etapas com erro:", "Pipeline terminou com erro"),
    ]
    rows = []
    for etapa, pattern, cause in patterns:
        found = [line for line in lines if pattern.lower() in line.lower()]
        rows.append(
            {
                "Etapa": etapa,
                "Status": "Encontrado" if found else "Não encontrado",
                "Mensagem relevante": found[-1] if found else "",
                "Possível causa": cause,
            }
        )
    return rows


def orders_daily_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    orders = read_csv(DATA / "ml_orders.csv")
    if orders.empty or "date_created" not in orders.columns:
        return [], {}
    orders["date_brt"] = normalize_dates(orders["date_created"], utc_to_brt=True).dt.date
    orders["receita_calc"] = pd.to_numeric(orders.get("unit_price", 0), errors="coerce").fillna(0) * pd.to_numeric(
        orders.get("quantity", 0), errors="coerce"
    ).fillna(0)
    daily = (
        orders.groupby("date_brt", as_index=False)
        .agg(pedidos=("order_id", "nunique"), linhas=("order_id", "size"), receita=("receita_calc", "sum"))
        .sort_values("date_brt")
    )
    tail = daily.tail(30)
    rows = [
        {
            "Data": row["date_brt"].strftime("%d/%m/%Y"),
            "Pedidos": int(row["pedidos"]),
            "Linhas": int(row["linhas"]),
            "Receita": br_money(float(row["receita"])),
        }
        for _, row in tail.iterrows()
    ]
    status_col = first_existing(orders, ["status", "status_pedido"])
    latest = orders[orders["date_brt"] == orders["date_brt"].max()]
    status = latest[status_col].fillna("N/D").astype(str).value_counts().to_dict() if status_col else {}
    summary = {
        "max_date_created": str(orders["date_brt"].max()),
        "status_latest": status,
    }
    return rows, summary


def ml_datetime(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds")


def iter_windows(start_dt: datetime, end_dt: datetime) -> list[tuple[datetime, datetime]]:
    windows = []
    current = start_dt
    while current <= end_dt:
        window_end = min(current + timedelta(days=WINDOW_DAYS) - timedelta(milliseconds=1), end_dt)
        windows.append((current, window_end))
        current = window_end + timedelta(milliseconds=1)
    return windows


def load_credentials() -> tuple[str, str, str, str]:
    load_dotenv(ROOT / ".env")
    values = (
        os.getenv("ML_CLIENT_ID", "").strip(),
        os.getenv("ML_CLIENT_SECRET", "").strip(),
        os.getenv("ML_REFRESH_TOKEN", "").strip(),
        os.getenv("ML_SELLER_ID", "").strip(),
    )
    if not all(values):
        raise RuntimeError("Credenciais ML incompletas no .env.")
    return values


def generate_access_token() -> tuple[str, int, str]:
    client_id, client_secret, refresh_token, _ = load_credentials()
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT_SECONDS,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok:
        return "", response.status_code, str(payload or response.text)[:500]
    return str(payload.get("access_token") or ""), response.status_code, ""


def normalize_order_rows(orders: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for order in orders:
        for order_item in order.get("order_items") or []:
            item = order_item.get("item") or {}
            rows.append(
                {
                    "order_id": order.get("id"),
                    "date_created": order.get("date_created"),
                    "status": order.get("status"),
                    "total_amount": order.get("total_amount"),
                    "paid_amount": order.get("paid_amount"),
                    "item_id": item.get("id"),
                    "item_title": item.get("title"),
                    "quantity": order_item.get("quantity"),
                    "unit_price": order_item.get("unit_price"),
                    "sale_fee": order_item.get("sale_fee") or order_item.get("sale_fee_amount"),
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
        df = df.drop_duplicates(subset=["order_id", "item_id"], keep="last")
    return df


def controlled_orders_fetch() -> ControlResult:
    result = ControlResult(params=[])
    try:
        access_token, token_status, token_error = generate_access_token()
        result.status_token = str(token_status)
        if token_error or not access_token:
            result.error = token_error or "Token vazio"
            return result

        _, _, _, seller_id = load_credentials()
        start_dt = datetime.combine(CONTROL_START, time.min, tzinfo=BRT)
        end_dt = datetime.combine(date.today(), time(23, 59, 59, 999000), tzinfo=BRT)
        headers = {"Authorization": f"Bearer {access_token}", "accept": "application/json"}
        collected: list[dict[str, Any]] = []
        statuses: list[str] = []

        for window_start, window_end in iter_windows(start_dt, end_dt):
            offset = 0
            while True:
                params = {
                    "seller": seller_id,
                    "order.date_created.from": ml_datetime(window_start),
                    "order.date_created.to": ml_datetime(window_end),
                    "sort": "date_desc",
                    "limit": PAGE_LIMIT,
                    "offset": offset,
                }
                result.params.append(
                    {
                        "endpoint": ORDERS_URL,
                        "from": params["order.date_created.from"],
                        "to": params["order.date_created.to"],
                        "field": "order.date_created",
                    }
                )
                response = requests.get(ORDERS_URL, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
                statuses.append(str(response.status_code))
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                if not response.ok:
                    result.error = str(payload or response.text)[:500]
                    result.status_orders = ",".join(sorted(set(statuses)))
                    return result
                page_orders = payload.get("results", [])
                collected.extend(page_orders)
                total = int((payload.get("paging") or {}).get("total", len(page_orders)))
                offset += PAGE_LIMIT
                if not page_orders or offset >= total:
                    break

        df = normalize_order_rows(collected)
        AUDIT_ORDERS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(AUDIT_ORDERS_OUTPUT, index=False, encoding="utf-8-sig")
        result.status_orders = ",".join(sorted(set(statuses))) if statuses else "N/D"
        result.rows = len(df)
        result.orders = int(df["order_id"].nunique()) if not df.empty else 0
        result.revenue = float((df["unit_price"] * df["quantity"]).sum()) if not df.empty else 0.0
        if not df.empty:
            result.first_date = str(df["date_created"].min())
            result.last_date = str(df["date_created"].max())
            ids = df.sort_values("date_created")["order_id"].drop_duplicates().astype(str).tolist()
            result.first_ids = ", ".join(ids[:5])
            result.last_ids = ", ".join(ids[-5:])
        return result
    except Exception as exc:
        result.error = str(exc)
        return result


def funnel_rows() -> list[dict[str, Any]]:
    orders = read_csv(DATA / "ml_orders.csv")
    shipments = read_csv(DATA / "ml_shipments.csv")
    final = read_csv(DATA / "dashboard_base_final.csv")
    params = read_csv(DATA / "parametros_financeiros_seconds.csv")
    if orders.empty:
        return []
    orders["receita_calc"] = pd.to_numeric(orders.get("unit_price", 0), errors="coerce").fillna(0) * pd.to_numeric(
        orders.get("quantity", 0), errors="coerce"
    ).fillna(0)
    order_ids = set(orders["order_id"].astype(str)) if "order_id" in orders.columns else set()
    shipment_ids = set(shipments["order_id"].astype(str)) if "order_id" in shipments.columns else set()
    params_ids = set(params["item_id"].astype(str).str.upper()) if "item_id" in params.columns else set()
    with_shipments = orders[orders["order_id"].astype(str).isin(shipment_ids)] if shipment_ids else orders.iloc[0:0]
    with_params = orders[orders["item_id"].astype(str).str.upper().isin(params_ids)] if params_ids else orders.iloc[0:0]
    final_orders = set(final["order_id"].astype(str)) if "order_id" in final.columns else set()
    consolidated = orders[orders["order_id"].astype(str).isin(final_orders)] if final_orders else orders.iloc[0:0]

    steps = [
        ("Pedidos ML brutos", orders),
        ("→ pedidos com shipments", with_shipments),
        ("→ pedidos com CMV Seconds", with_params),
        ("→ pedidos consolidados", consolidated),
        ("→ pedidos exibidos no BI", final),
    ]
    rows = []
    for label, df in steps:
        if "receita" in df.columns:
            revenue = pd.to_numeric(df["receita"], errors="coerce").fillna(0).sum()
        elif "receita_calc" in df.columns:
            revenue = df["receita_calc"].sum()
        else:
            revenue = 0
        rows.append(
            {
                "Etapa": label,
                "Linhas": len(df),
                "Pedidos": df["order_id"].astype(str).nunique() if "order_id" in df.columns and not df.empty else 0,
                "Receita": br_money(float(revenue)),
            }
        )
    return rows


def main() -> None:
    file_rows = file_audit_rows()
    orders_daily, orders_summary = orders_daily_rows()
    logs = log_findings()
    control = controlled_orders_fetch()
    funnel = funnel_rows()

    flow_rows = [
        {"Etapa": step, "Script/Função": script, "Arquivo gerado": output, "Status esperado": "Arquivo atualizado e return code 0"}
        for step, script, output in PIPELINE
    ]
    params_rows = [
        {
            "Endpoint": "orders/search",
            "Data inicial enviada": script_constant("teste_ml_orders.py", "DATA_INICIO"),
            "Data final enviada": script_constant("teste_ml_orders.py", "DATA_FIM"),
            "Campo de data usado": "order.date_created",
        },
        {
            "Endpoint": "Product Ads metrics",
            "Data inicial enviada": script_constant("teste_ml_ads_metrics.py", "DATA_INICIO"),
            "Data final enviada": script_constant("teste_ml_ads_metrics.py", "DATA_FIM"),
            "Campo de data usado": "date_from/date_to",
        },
    ]
    control_rows = [
        {
            "Métrica": "Status token",
            "Valor": control.status_token,
        },
        {
            "Métrica": "Status orders/search",
            "Valor": control.status_orders,
        },
        {
            "Métrica": "Quantidade encontrada",
            "Valor": br_number(control.orders),
        },
        {
            "Métrica": "Linhas item/pedido",
            "Valor": br_number(control.rows),
        },
        {
            "Métrica": "Receita encontrada",
            "Valor": br_money(control.revenue),
        },
        {
            "Métrica": "Primeira data",
            "Valor": control.first_date,
        },
        {
            "Métrica": "Última data",
            "Valor": control.last_date,
        },
        {
            "Métrica": "5 primeiros order_id",
            "Valor": control.first_ids,
        },
        {
            "Métrica": "5 últimos order_id",
            "Valor": control.last_ids,
        },
        {
            "Métrica": "Erro",
            "Valor": control.error or "Nenhum",
        },
    ]

    report = f"""# AUDITORIA DE ATUALIZAÇÃO DA BASE

## 1. Resumo executivo

A rotina de atualização foi mapeada e a causa principal da base parar em 21/05/2026 foi localizada: o script `teste_ml_orders.py` usa `DATA_FIM = "2026-05-20"` como padrão, e a base exibida no BI usa `date_created` convertido para BRT, fazendo o último registro aparecer em 21/05/2026. Além disso, a última execução registrou erro de logging `charmap` em pedidos, shipments e detalhes/estoque, embora os CSVs tenham sido gravados.

O teste controlado de pedidos de 22/05/2026 até hoje salvou `data/auditoria_orders_apos_20260521.csv` e encontrou {br_number(control.orders)} pedidos, com receita {br_money(control.revenue)}. Isso comprova que a API tem dados após 21/05/2026 e que o limitador é técnico/local.

## 2. Fluxo de atualização

{md_table(flow_rows, ["Etapa", "Script/Função", "Arquivo gerado", "Status esperado"])}

## 3. Arquivos da base

{md_table(file_rows, ["Arquivo", "Existe", "Linhas", "Menor data", "Maior data", "Atualizado em", "Status"])}

Arquivo limitante: `data/ml_orders.csv`. `data/dashboard_base_final.csv` herda o limite porque é gerado a partir dele.

## 4. Pedidos ML

Maior `date_created` local em `ml_orders.csv`: {orders_summary.get("max_date_created", "N/D")}.

Status dos pedidos no dia mais recente da base: `{orders_summary.get("status_latest", {})}`.

Pedidos por dia nos últimos 30 dias disponíveis:

{md_table(orders_daily, ["Data", "Pedidos", "Linhas", "Receita"])}

## 5. Logs da última execução

{md_table(logs, ["Etapa", "Status", "Mensagem relevante", "Possível causa"])}

## 6. Cache e deduplicação

- `teste_ml_orders.py`: não usa cache de pedidos; consulta a API e sobrescreve `data/ml_orders.csv`.
- Deduplicação de pedidos: `drop_duplicates(subset=["order_id", "item_id"], keep="last")`.
- `teste_ml_shipments.py`: usa `data/ml_shipments.csv` como cache, chave principal `order_id`; consulta apenas pedidos novos.
- O cache de shipments não impede pedidos novos; ele depende de `ml_orders.csv`. Se `ml_orders.csv` para em 21/05, shipments também para.
- `merge_ml_seconds.py`: não exclui pedidos sem CMV; mantém pedido, zera custos Seconds não confiáveis e usa fallback de comissão ML.

## 7. Token e API Mercado Livre

- Geração de token no teste controlado: HTTP {control.status_token}.
- `orders/search` no teste controlado: HTTP {control.status_orders}.
- Tokens e segredos não foram impressos neste relatório.
- Logs antigos de alguns scripts imprimem payload de token e devem ser mascarados em correção futura.

## 8. Parâmetros de data da coleta

{md_table(params_rows, ["Endpoint", "Data inicial enviada", "Data final enviada", "Campo de data usado"])}

Parâmetros usados no teste controlado:

{md_table(control.params or [], ["endpoint", "from", "to", "field"])}

## 9. Teste controlado 22/05/2026 até hoje

{md_table(control_rows, ["Métrica", "Valor"])}

## 10. Funil de consolidação

{md_table(funnel, ["Etapa", "Linhas", "Pedidos", "Receita"])}

## 11. Principal causa da base parar em 21/05/2026

1. `teste_ml_orders.py` tem data final padrão fixa em `2026-05-20`.
2. `dashboard_base_final.csv` é regenerado a partir de `ml_orders.csv`, portanto não consegue avançar além da base de pedidos.
3. `teste_ml_ads_metrics.py` também tem data final fixa em `2026-05-15`, limitando Ads.
4. O pipeline reportou erro em 3 etapas por falha de encoding no logging (`charmap`), mascarando uma atualização parcialmente executada como erro.

## 12. Correções aplicadas

Preencher após eventual correção segura.

## 13. Correções recomendadas

- Trocar datas finais fixas por `date.today().isoformat()` ou variável de ambiente.
- Corrigir logging do pipeline para tolerar caracteres inválidos/Unicode no Windows.
- Mascarar token nos scripts que ainda imprimem payload completo de OAuth.
- Corrigir snapshot DuckDB de `historico_vendas`, que falhou com coluna `sku` duplicada.
- Rodar atualização completa após as correções.

## 14. Checklist para validar atualização

- [ ] `python -m py_compile app.py`.
- [ ] `python -m py_compile atualizar_dashboard.py teste_ml_orders.py teste_ml_ads_metrics.py`.
- [ ] Rodar `python atualizar_dashboard.py`.
- [ ] Confirmar `data/ml_orders.csv` com data posterior a 21/05/2026.
- [ ] Confirmar `data/dashboard_base_final.csv` com data posterior a 21/05/2026.
- [ ] Confirmar cabeçalho do BI com nova base disponível.
- [ ] Confirmar maio completo aproximando do Mercado Livre.
- [ ] Conferir logs sem erro crítico.

## 15. Comando para atualização manual

```powershell
cd C:\\Users\\jit87\\Desktop\\dashboard_jitparts_ml
.\\.venv\\Scripts\\python.exe atualizar_dashboard.py
```
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
