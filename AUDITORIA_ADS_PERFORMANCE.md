# Auditoria da Aba Publicidade & Performance

Data: 2026-05-29  
Arquivo principal: `app.py`  
Arquivo de dados Ads: `data/ml_ads_metrics.csv`

## 1. Fonte dos Dados

| KPI | Fonte | Coluna | Formula | Confiabilidade |
|---|---|---|---|---|
| Investimento Total Ads | `data/ml_ads_metrics.csv` | `cost` | `sum(cost)`; se parcial, `ads_real + ads_estimado` | Alta quando cobertura completa; estimada quando parcial |
| Receita Atribuida Ads | `data/ml_ads_metrics.csv` | `revenue` | `sum(revenue)` | Alta para dias cobertos pela API |
| ROAS | `data/ml_ads_metrics.csv` | `revenue`, `cost` | `sum(revenue) / sum(cost ajustado)` | Ponderado por totais |
| ACOS | `data/ml_ads_metrics.csv` | `cost`, `revenue` | `sum(cost ajustado) / sum(revenue) * 100` | Ponderado por totais |
| CTR | `data/ml_ads_metrics.csv` | `clicks`, `impressions` | `sum(clicks) / sum(impressions) * 100` | Ponderado por totais |
| CPC | `data/ml_ads_metrics.csv` | `cost`, `clicks` | `sum(cost ajustado) / sum(clicks)` | Ponderado por totais |
| Conversao | `data/ml_ads_metrics.csv` | `units`, `clicks` | `sum(units) / sum(clicks) * 100` | Ponderado por totais |
| Cliques | `data/ml_ads_metrics.csv` | `clicks` | `sum(clicks)` | Alta para dias cobertos |
| Impressoes | `data/ml_ads_metrics.csv` | `impressions` | `sum(impressions)` | Alta para dias cobertos |

Origem API Mercado Livre: `teste_ml_ads_metrics.py` consulta Product Ads usando:

- `/advertising/MLB/product_ads/campaigns/{campaign_id}`
- `/advertising/MLB/advertisers/{advertiser_id}/product_ads/campaigns/search`

Metricas solicitadas na coleta: `clicks`, `prints`, `ctr`, `cost`, `cpc`, `acos`, `cvr`, `roas`, `units_quantity`, `total_amount`.

## 2. Formulas Encontradas e Ajustadas

A versao anterior ja calculava os KPIs principais por totais em `calculate_ads_kpis`, sem media simples de campanhas:

- ROAS = receita total / investimento total
- ACOS = investimento total / receita total x 100
- CTR = cliques totais / impressoes totais x 100
- CPC = investimento total / cliques totais
- Conversao = unidades atribuidas / cliques totais x 100

Foi adicionada a versao ajustada por cobertura em `calculate_ads_kpis_adjusted`, mantendo calculo ponderado por totais e usando investimento ajustado quando o periodo de Ads e parcial.

## 3. Cobertura Temporal

Nova funcao: `ads_temporal_coverage`.

Campos gerados:

- `ads_data_inicio`
- `ads_data_fim`
- `periodo_filtro_inicio`
- `periodo_filtro_fim`
- `cobertura_ads_percentual`
- `status_cobertura_ads`
- `dias_cobertos`
- `dias_faltantes`
- `ads_real`
- `ads_estimado`
- `ads_total_ajustado`
- `ads_fonte`

Status possiveis:

- `Completo`
- `Parcial`
- `Sem dados`

Regra importante: quando nao ha dado real de Ads no periodo, o dashboard nao inventa estimativa.

## 4. Reconciliacao com Financeiro Executivo

Nova conciliacao compara o investimento ajustado da aba de Ads com o valor usado em `calculate_executive_financials`.

| Metrica | Resultado |
|---|---|
| Fonte da aba Ads | `calculate_ads_kpis_adjusted` |
| Fonte Financeiro Executivo | `calculate_executive_financials` |
| Esperado | Diferenca zero para o mesmo periodo/filtro |
| Smoke test | Diferenca menor que R$ 0,01 |

## 5. Correcoes Aplicadas

- Aba renomeada visualmente para `Publicidade & Performance`.
- Novo bloco `Resumo Executivo Ads`.
- Novo bloco `Eficiencia de Funil`.
- Novo bloco `Rentabilidade Ads`.
- Novo bloco `Alertas de Ads`.
- Evolucao temporal separada em `Investimento x Receita Ads` e `ROAS x ACOS`.
- Ranking e tabela de campanhas movidos para estrutura mais executiva.
- Classificacao automatica de campanha:
  - Excelente: ROAS >= 10 e ACOS <= 10%
  - Boa: ROAS >= 6 e ACOS <= 16%
  - Atencao: ROAS >= 3 e ACOS <= 25%
  - Ruim: ROAS < 3 ou ACOS > 25%
- Tooltips adicionados aos KPIs principais.
- Auditoria da fonte de Ads incluida em expander da aba.

## 6. Pontos que Dependem de Coleta/API

- A receita atribuida continua limitada ao que a API Product Ads retorna em `total_amount`/`revenue`.
- A estimativa de investimento nao reconstrui receita atribuida faltante, apenas investimento.
- A conversao usa `units`; se a diretoria preferir pedidos, a coleta ja possui `orders`, mas a regra precisa ser aprovada.
- O CSV atual nao traz segmentacoes de produto/item por campanha, logo a conciliacao por SKU/MLB ainda nao e possivel.

## 7. Validacao

Executado:

- `python -m py_compile app.py`
- Inicializacao Streamlit em `http://localhost:8502`, resposta HTTP `200`

Smoke tests:

| Cenario | Status |
|---|---|
| Periodo com Ads completo | OK |
| Periodo com Ads parcial | OK |
| Periodo sem Ads | OK |
| Estimativa Hibrida ML + Seconds | OK |
| Seconds Oficial | OK |
| Filtro curto | OK |
| Filtro longo | OK |
| ROAS/ACOS ponderados por totais | OK |
| Conciliacao com Financeiro Executivo | OK |

