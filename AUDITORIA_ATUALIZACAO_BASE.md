# AUDITORIA DE ATUALIZAÇÃO DA BASE

## 1. Resumo executivo

A rotina de atualização foi mapeada e a causa principal da base parar em 21/05/2026 foi localizada: o script `teste_ml_orders.py` usa `DATA_FIM = "2026-05-20"` como padrão, e a base exibida no BI usa `date_created` convertido para BRT, fazendo o último registro aparecer em 21/05/2026. Além disso, a última execução registrou erro de logging `charmap` em pedidos, shipments e detalhes/estoque, embora os CSVs tenham sido gravados.

O teste controlado de pedidos de 22/05/2026 até hoje salvou `data/auditoria_orders_apos_20260521.csv` e encontrou 1.153 pedidos, com receita R$ 200.886,57. Isso comprova que a API tem dados após 21/05/2026 e que o limitador é técnico/local.

## 2. Fluxo de atualização

| Etapa | Script/Função | Arquivo gerado | Status esperado |
| --- | --- | --- | --- |
| Atualizar pedidos Mercado Livre | teste_ml_orders.py | data/ml_orders.csv | Arquivo atualizado e return code 0 |
| Atualizar shipments/frete | teste_ml_shipments.py | data/ml_shipments.csv | Arquivo atualizado e return code 0 |
| Atualizar lista de anúncios | teste_ml_items.py | data/ml_items.csv | Arquivo atualizado e return code 0 |
| Atualizar detalhes/estoque | teste_ml_item_details.py | data/ml_items_details.csv | Arquivo atualizado e return code 0 |
| Atualizar campanhas Ads | teste_ml_ads_campaigns.py | data/ml_ads_campaigns.csv | Arquivo atualizado e return code 0 |
| Atualizar métricas Ads | teste_ml_ads_metrics.py | data/ml_ads_metrics.csv | Arquivo atualizado e return code 0 |
| Atualizar base final consolidada | merge_ml_seconds.py data/seconds_cmv.xlsx | data/dashboard_base_final.csv | Arquivo atualizado e return code 0 |
| Salvar histórico DuckDB | salvar_historico_duckdb.py | data/jitparts.duckdb | Arquivo atualizado e return code 0 |


## 3. Arquivos da base

| Arquivo | Existe | Linhas | Menor data | Maior data | Atualizado em | Status |
| --- | --- | --- | --- | --- | --- | --- |
| data/ml_orders.csv | Sim | 10505 | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 02/06/2026 08:37:18 | OK |
| data/ml_shipments.csv | Sim | 10505 | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 02/06/2026 08:37:19 | OK |
| data/ml_items.csv | Sim | 1000 | N/D | N/D | 02/06/2026 08:37:32 | OK |
| data/ml_items_details.csv | Sim | 1000 | 04/02/2026 21:19:32 | 02/06/2026 07:15:45 | 02/06/2026 08:43:29 | OK |
| data/ml_ads_campaigns.csv | Sim | 23 | N/D | N/D | 02/06/2026 08:43:31 | OK |
| data/ml_ads_metrics.csv | Sim | 345 | 01/05/2026 00:00:00 | 15/05/2026 00:00:00 | 02/06/2026 08:46:41 | OK |
| data/dashboard_base_final.csv | Sim | 10505 | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 02/06/2026 08:46:43 | OK |
| data/jitparts.duckdb | Sim | N/D | N/D | N/D | 02/06/2026 08:46:44 | OK |


Arquivo limitante: `data/ml_orders.csv`. `data/dashboard_base_final.csv` herda o limite porque é gerado a partir dele.

## 4. Pedidos ML

Maior `date_created` local em `ml_orders.csv`: 2026-05-21.

Status dos pedidos no dia mais recente da base: `{'paid': 1}`.

Pedidos por dia nos últimos 30 dias disponíveis:

| Data | Pedidos | Linhas | Receita |
| --- | --- | --- | --- |
| 22/04/2026 | 158 | 158 | R$ 29.961,51 |
| 23/04/2026 | 140 | 140 | R$ 25.634,47 |
| 24/04/2026 | 158 | 158 | R$ 28.724,74 |
| 25/04/2026 | 86 | 86 | R$ 11.826,55 |
| 26/04/2026 | 96 | 96 | R$ 12.736,49 |
| 27/04/2026 | 141 | 141 | R$ 23.531,99 |
| 28/04/2026 | 123 | 123 | R$ 27.196,12 |
| 29/04/2026 | 113 | 113 | R$ 21.796,96 |
| 30/04/2026 | 129 | 129 | R$ 22.018,22 |
| 01/05/2026 | 103 | 103 | R$ 16.861,67 |
| 02/05/2026 | 81 | 81 | R$ 13.210,94 |
| 03/05/2026 | 65 | 65 | R$ 7.352,99 |
| 04/05/2026 | 135 | 135 | R$ 23.305,90 |
| 05/05/2026 | 137 | 137 | R$ 27.128,49 |
| 06/05/2026 | 141 | 141 | R$ 28.207,63 |
| 07/05/2026 | 112 | 112 | R$ 16.133,63 |
| 08/05/2026 | 102 | 102 | R$ 20.215,08 |
| 09/05/2026 | 77 | 77 | R$ 11.868,68 |
| 10/05/2026 | 51 | 51 | R$ 7.258,06 |
| 11/05/2026 | 103 | 103 | R$ 19.787,51 |
| 12/05/2026 | 108 | 108 | R$ 17.867,63 |
| 13/05/2026 | 106 | 106 | R$ 21.127,98 |
| 14/05/2026 | 119 | 119 | R$ 20.979,37 |
| 15/05/2026 | 88 | 88 | R$ 18.737,21 |
| 16/05/2026 | 71 | 71 | R$ 9.968,41 |
| 17/05/2026 | 63 | 63 | R$ 8.298,66 |
| 18/05/2026 | 144 | 144 | R$ 24.628,38 |
| 19/05/2026 | 122 | 122 | R$ 21.389,84 |
| 20/05/2026 | 124 | 124 | R$ 21.029,63 |
| 21/05/2026 | 1 | 1 | R$ 71,12 |


## 5. Evidências nos logs antes da correção

A tabela abaixo preserva os sinais encontrados no log que motivou a correção. Após os ajustes, a nova execução completa terminou com `Etapas com sucesso: 8` e `Etapas com erro: 0`.

| Etapa | Status | Mensagem relevante | Possível causa |
| --- | --- | --- | --- |
| Atualizar pedidos Mercado Livre | Encontrado | [2026-06-02 08:46:45] - Atualizar detalhes/estoque dos anuncios: Erro inesperado: 'charmap' codec can't encode character '\ufffd' in position 55: character maps to <undefined> | Erro de encoding ao registrar saída da etapa |
| Atualizar shipments/frete | Encontrado | [2026-06-02 08:46:45] - Atualizar detalhes/estoque dos anuncios: Erro inesperado: 'charmap' codec can't encode character '\ufffd' in position 55: character maps to <undefined> | Erro de encoding ao registrar saída da etapa |
| Atualizar detalhes/estoque | Encontrado | [2026-06-02 08:46:45] - Atualizar detalhes/estoque dos anuncios: Erro inesperado: 'charmap' codec can't encode character '\ufffd' in position 55: character maps to <undefined> | Erro de encoding ao registrar saída da etapa |
| Pedidos | Encontrado | [2026-06-02 08:37:18] Periodo consultado: 2026-02-01T00:00:00.000-03:00 a 2026-05-20T23:59:59.999-03:00 | Período enviado à API |
| Ads | Encontrado | [2026-06-02 08:46:41] Periodo Ads consultado: 01/05/2026 a 15/05/2026 | Período enviado à API Ads |
| DuckDB | Encontrado | [2026-06-02 08:46:45] [2026-06-02 08:46:44] ERRO: Falha ao inserir em historico_vendas: Catalog Error: Column with name sku already exists! | Falha no snapshot historico_vendas |
| Resumo final | Encontrado | [ERRO] Etapas com erro: | Pipeline terminou com erro |


## 6. Cache e deduplicação

- `teste_ml_orders.py`: não usa cache de pedidos; consulta a API e sobrescreve `data/ml_orders.csv`.
- Deduplicação de pedidos: `drop_duplicates(subset=["order_id", "item_id"], keep="last")`.
- `teste_ml_shipments.py`: usa `data/ml_shipments.csv` como cache, chave principal `order_id`; consulta apenas pedidos novos.
- O cache de shipments não impede pedidos novos; ele depende de `ml_orders.csv`. Se `ml_orders.csv` para em 21/05, shipments também para.
- `merge_ml_seconds.py`: não exclui pedidos sem CMV; mantém pedido, zera custos Seconds não confiáveis e usa fallback de comissão ML.

## 7. Token e API Mercado Livre

- Geração de token no teste controlado: HTTP 200.
- `orders/search` no teste controlado: HTTP 200.
- Tokens e segredos não foram impressos neste relatório.
- Logs antigos de alguns scripts imprimem payload de token e devem ser mascarados em correção futura.

## 8. Parâmetros de data da coleta

| Endpoint | Data inicial enviada | Data final enviada | Campo de data usado |
| --- | --- | --- | --- |
| orders/search | "2026-02-01" | "2026-05-20" | order.date_created |
| Product Ads metrics | "2026-05-01" | "2026-05-15" | date_from/date_to |


Parâmetros usados no teste controlado:

| endpoint | from | to | field |
| --- | --- | --- | --- |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |
| https://api.mercadolibre.com/orders/search | 2026-05-22T00:00:00.000-03:00 | 2026-06-03T23:59:59.999-03:00 | order.date_created |


## 9. Teste controlado 22/05/2026 até hoje

| Métrica | Valor |
| --- | --- |
| Status token | 200 |
| Status orders/search | 200 |
| Quantidade encontrada | 1.153 |
| Linhas item/pedido | 1.153 |
| Receita encontrada | R$ 200.886,57 |
| Primeira data | 2026-05-21 23:22:59-04:00 |
| Última data | 2026-06-03 10:36:01-04:00 |
| 5 primeiros order_id | 2000016552918882, 2000016553083504, 2000016554308506, 2000016554454246, 2000016554524112 |
| 5 últimos order_id | 2000016755116030, 2000016755394554, 2000016755555092, 2000016755613028, 2000016755820782 |
| Erro | Nenhum |


## 10. Funil de consolidação

| Etapa | Linhas | Pedidos | Receita |
| --- | --- | --- | --- |
| Pedidos ML brutos | 10505 | 10505 | R$ 1.868.164,81 |
| → pedidos com shipments | 10505 | 10505 | R$ 1.868.164,81 |
| → pedidos com CMV Seconds | 9910 | 9910 | R$ 1.716.907,32 |
| → pedidos consolidados | 10505 | 10505 | R$ 1.868.164,81 |
| → pedidos exibidos no BI | 10505 | 10505 | R$ 1.868.164,81 |


## 11. Principal causa da base parar em 21/05/2026

1. `teste_ml_orders.py` tem data final padrão fixa em `2026-05-20`.
2. `dashboard_base_final.csv` é regenerado a partir de `ml_orders.csv`, portanto não consegue avançar além da base de pedidos.
3. `teste_ml_ads_metrics.py` também tem data final fixa em `2026-05-15`, limitando Ads.
4. O pipeline reportou erro em 3 etapas por falha de encoding no logging (`charmap`), mascarando uma atualização parcialmente executada como erro.

## 12. Correções aplicadas

- `teste_ml_orders.py`: `DATA_FIM` deixou de ser fixa em `2026-05-20` e passou a usar `date.today().isoformat()` como padrão, preservando override por `ML_ORDERS_DATA_FIM`.
- `teste_ml_ads_metrics.py`: `DATA_FIM` deixou de ser fixa em `2026-05-15` e passou a usar `date.today().isoformat()`.
- `atualizar_dashboard.py`: logging passou a tolerar Unicode/encoding do Windows e força `PYTHONIOENCODING=utf-8` nos subprocessos.
- `teste_ml_orders.py`, `teste_ml_items.py`, `teste_ml_item_details.py`, `teste_ml_ads_campaigns.py` e `teste_ml_ads_metrics.py`: `access_token` e `refresh_token` passaram a ser mascarados nos logs.
- `salvar_historico_duckdb.py`: snapshot histórico passou a tratar colisões de colunas case-insensitive no DuckDB, corrigindo o erro `Column with name sku already exists`.
- `logs/ultima_execucao.log`: tokens OAuth gravados durante a execução intermediária foram redigidos.

Nenhuma regra financeira, merge de negócio, status de pedido, CMV, comissão, frete, Ads ou Seconds foi alterada.

## 13. Correções recomendadas

- Trocar datas finais fixas por `date.today().isoformat()` ou variável de ambiente.
- Corrigir logging do pipeline para tolerar caracteres inválidos/Unicode no Windows.
- Mascarar token nos scripts que ainda imprimem payload completo de OAuth.
- Corrigir snapshot DuckDB de `historico_vendas`, que falhou com coluna `sku` duplicada.
- Rodar atualização completa após as correções.

## 14. Checklist para validar atualização

- [x] `python -m py_compile app.py`.
- [x] `python -m py_compile atualizar_dashboard.py teste_ml_orders.py teste_ml_ads_metrics.py salvar_historico_duckdb.py`.
- [x] `python atualizar_dashboard.py` executado após correções.
- [x] `data/ml_orders.csv` com data posterior a 21/05/2026.
- [x] `data/dashboard_base_final.csv` com data posterior a 21/05/2026.
- [x] `data/ml_ads_metrics.csv` atualizado até 03/06/2026.
- [x] Maio completo passou a aproximar o Mercado Livre.
- [x] Logs sem erro crítico: `Etapas com sucesso: 8`; `Etapas com erro: 0`.
- [ ] Confirmar visualmente no Streamlit o cabeçalho com nova base disponível.

## 14.1 Validação após correção

| Item | Resultado |
| --- | --- |
| `data/ml_orders.csv` | 11.765 linhas; maior data `2026-06-03 15:59:39+00:00` |
| `data/ml_shipments.csv` | 11.765 linhas; maior data `2026-06-03 15:59:40+00:00` |
| `data/ml_ads_metrics.csv` | 782 linhas; maior data `2026-06-03 03:00:00+00:00` |
| `data/dashboard_base_final.csv` | 11.765 linhas; maior data `2026-06-03 15:59:39+00:00` |
| Maio no dashboard atualizado | 3.067 pedidos; 3.194 unidades; receita `R$ 539.491,39` |
| Mercado Livre print | 3.066 vendas; 3.193 unidades; vendas brutas `R$ 539.369,00` |
| Diferença após atualização | +1 pedido; +1 unidade; +`R$ 122,39` |
| `logs/ultima_execucao.log` | `Etapas com sucesso: 8`; `Etapas com erro: 0`; tokens mascarados |

## 15. Comando para atualização manual

```powershell
cd C:\Users\jit87\Desktop\dashboard_jitparts_ml
.\.venv\Scripts\python.exe atualizar_dashboard.py
```
