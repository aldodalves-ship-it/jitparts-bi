# Jit Parts — BI Ecommerce

Dashboard executivo Mercado Livre + Seconds, construído em Streamlit.

## Estrutura

```
app.py                        # Aplicação principal
requirements.txt              # Dependências
data/
  dashboard_base_final.csv    # Base consolidada ML × Seconds
  base_seconds_principal.csv  # Parâmetros financeiros Seconds
  ml_ads_metrics.csv          # Métricas de campanhas Ads
  ml_items_details.csv        # Detalhes dos anúncios
  ml_orders.csv               # Pedidos ML
  ml_shipments.csv            # Fretes ML
  parametros_financeiros_seconds.csv
.streamlit/
  config.toml                 # Configuração do Streamlit
```

## Deploy local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy Streamlit Cloud

1. Suba o repositório no GitHub (sem `data/` pesada — use LFS ou suba os CSVs direto)
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte o repositório → selecione `app.py`
4. Configure secrets em **Settings → Secrets** se necessário

## Dados

Os CSVs em `data/` devem ser versionados no repositório.  
O arquivo `jitparts.duckdb` (60 MB) usa Git LFS ou pode ser regenerado localmente via `salvar_historico_duckdb.py`.
