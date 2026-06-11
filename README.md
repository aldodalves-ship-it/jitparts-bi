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

1. Suba o repositório no GitHub **sem a pasta `data/`** (os CSVs são gerados automaticamente)
2. Acesse [share.streamlit.io](https://share.streamlit.io) → conecte o repositório → selecione `app.py`
3. Em **Settings → Secrets**, adicione:

```toml
[mercadolivre]
ML_CLIENT_ID     = "seu_client_id"
ML_CLIENT_SECRET = "seu_client_secret"
ML_REFRESH_TOKEN = "seu_refresh_token"
ML_SELLER_ID     = "seu_seller_id"
```

4. Clique em **Deploy** — na primeira execução o app irá:
   - Detectar que `data/dashboard_base_final.csv` não existe
   - Executar automaticamente o pipeline de coleta (pedidos, shipments, ads, merge)
   - Exibir barra de progresso durante a geração
   - Carregar o dashboard quando os dados estiverem prontos

### Fluxo automático de dados (`bootstrap.py`)

```
Streamlit Cloud inicia
    ↓
ensure_data_ready()
    ├── CSV existe? → carrega normalmente
    └── CSV ausente?
            ├── st.secrets → injeta credenciais ML no os.environ
            ├── teste_ml_orders.py    → data/ml_orders.csv
            ├── teste_ml_shipments.py → data/ml_shipments.csv
            ├── teste_ml_items.py     → data/ml_items.csv
            ├── teste_ml_item_details.py
            ├── teste_ml_ads_*.py
            └── merge_ml_seconds.py  → data/dashboard_base_final.csv ✓
```

## Dados

Os CSVs em `data/` devem ser versionados no repositório.  
O arquivo `jitparts.duckdb` (60 MB) usa Git LFS ou pode ser regenerado localmente via `salvar_historico_duckdb.py`.
