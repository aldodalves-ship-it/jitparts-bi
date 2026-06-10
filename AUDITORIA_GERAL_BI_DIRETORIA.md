# AUDITORIA GERAL BI DIRETORIA

## 1. Resumo executivo

A principal divergência entre o print do Mercado Livre e o BI no intervalo 01/05/2026 a 31/05/2026 vem de cobertura temporal incompleta da base local. O BI informa base disponível de 01/02/2026 a 21/05/2026 e, portanto, para maio completo ele efetivamente consegue analisar somente até 21/05/2026. O filtro, antes da correção recomendada, permitia selecionar 31/05/2026 sem deixar claro que os dias 22/05/2026 a 31/05/2026 não estavam na base.

O filtro do app usa `date_created`, converte UTC para `America/Sao_Paulo`, gera `data_ref` e aplica comparação inclusiva `>= data inicial` e `<= data final`. Não foi encontrado erro de exclusão do dia final; o problema é comunicação/limitação do período efetivo.

## 2. Principal causa da divergência ML x BI

- Mercado Livre print, maio completo: R$ 539.369,00; 3.066 vendas; 3.193 unidades.
- BI print, período selecionado 01/05/2026 a 31/05/2026: R$ 355.428,81; 2.053 pedidos; ticket R$ 173,13.
- Base local disponível no BI: 01/02/2026 a 21/05/2026.
- Período efetivamente analisável para o filtro solicitado: 01/05/2026 a 21/05/2026.

| Métrica | Mercado Livre | BI observado | Diferença absoluta | Diferença % |
| --- | --- | --- | --- | --- |
| Receita | R$ 539.369,00 | R$ 355.428,81 | R$ 183.940,19 | 34,10% |
| Pedidos | 3.066 | 2.053 | 1.013 | 33,04% |
| Unidades | 3.193 | N/D no print BI | N/D | N/D |


Conclusão: a diferença principal é base ML local incompleta para o mês fechado. Deduplicação, timezone e filtro final inclusivo não explicam a divergência principal pela evidência encontrada.

## 3. Correções aplicadas

- Aplicado em `app.py`: quando o usuário solicita período fora da base disponível, o BI exibe aviso explícito de limitação.
- Aplicado em `app.py`: o cabeçalho passa a mostrar período solicitado e período efetivamente analisado quando houver truncamento pela base.
- Aplicado em `app.py`: os cálculos passam a usar o período efetivo com sobreposição real da base para evitar que o dashboard pareça analisar dias sem dados.

Nenhuma regra de receita, status, API, merge, CMV, comissão, frete, Ads ou Seconds foi alterada.

## 4. Correções recomendadas mas não aplicadas

- Atualizar a coleta Mercado Livre até 31/05/2026 antes de comparar maio fechado com o painel oficial.
- Salvar o relatório/export oficial do Mercado Livre com o mesmo escopo do print para conciliação documental.
- Auditar os 129 registros envolvidos em duplicidade de `shipment_id` antes de qualquer deduplicação.
- Não alterar regra de receita/status sem aprovação, pois a divergência observada é majoritariamente cobertura da base.
- Validar visualmente no navegador todas as abas antes da apresentação à diretoria.

## 5. Auditoria do filtro de período

| Dataframe | Coluna de data usada | Menor data | Maior data | Qtde registros no período |
| --- | --- | --- | --- | --- |
| base final consolidada | date_created | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 2053 |
| pedidos ML | date_created | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 2053 |
| shipments/frete | date_created | 01/02/2026 02:43:47 | 21/05/2026 00:06:21 | 2053 |
| Ads | data_ref | 01/05/2026 00:00:00 | 15/05/2026 00:00:00 | 345 |
| itens/anuncios | last_updated | 04/02/2026 21:19:32 | 02/06/2026 07:15:45 | 975 |
| Seconds | N/D | N/D | N/D | 0 |


Observações:

- `dashboard_base_final.csv`: app usa `date_created` em UTC convertido para BRT.
- Filtro é inclusivo na data inicial e final.
- Selecionar 31/05/2026 não adiciona dados inexistentes após 21/05/2026; sem aviso, isso gera interpretação incorreta.

## 6. Auditoria da receita / faturamento

| Fonte | Receita | Pedidos | Unidades | Ticket médio |
| --- | --- | --- | --- | --- |
| ml_orders.csv | R$ 355.428,81 | 2.053 | 2.131 | R$ 173,13 |
| dashboard_base_final.csv | R$ 355.428,81 | 2.053 | 2.131 | R$ 173,13 |
| base filtrada pelo app | R$ 355.428,81 | 2.053 | 2.131 | R$ 173,13 |
| print Mercado Livre | R$ 539.369,00 | 3.066 | 3.193 | R$ 175,92 |


Status dos pedidos ML no período local: `{'paid': 1897, 'cancelled': 155, 'partially_refunded': 1}`

Status na base consolidada filtrada: `{'ACTIVE': 1892, 'paid': 149, 'cancelled': 12}`

Receita usada pelo BI: primeira coluna disponível entre `receita`, `faturamento`, `faturamento_seconds`. Para a base híbrida atual, a coluna usada é `receita`.

## 7. KPIs auditados

| KPI | Fonte | Fórmula | Valor atual | Status auditoria |
| --- | --- | --- | --- | --- |
| Visão Geral - Faturamento | dashboard_base_final.csv | sum(receita) | R$ 355.428,81 | OK, consistente com base filtrada |
| Visão Geral - Pedidos | dashboard_base_final.csv | nunique(order_id) | 2.053 | OK |
| Visão Geral - Ticket Médio | dashboard_base_final.csv | Receita / pedidos | R$ 173,13 | OK |
| Visão Geral - Margem Base | DRE híbrida | Receita - Comissão - CMV - Frete - Impostos - Rateio Seconds | R$ 37.727,31 | Recalculado |
| Visão Geral - Custos Comerciais | Ads + política operacional | Ads + devoluções + outras taxas + papelaria | R$ 13.690,75 | Recalculado parcialmente; devoluções dependem de coluna explícita |
| Visão Geral - Resultado Final da Margem | DRE | Resultado Base - Custos Comerciais | R$ 24.036,56 | Recalculado |
| Visão Geral - Investimento Ads | ml_ads_metrics.csv | sum(cost) | R$ 11.913,61 | OK com cobertura parcial |
| Visão Geral - Alertas | Regras internas do app | bundle de alertas por vendas/estoque/Ads | N/D via script | Requer smoke visual |
| Inteligência Comercial - Produtos em queda brusca | dashboard_base_final.csv | comparação temporal por produto no app | N/D via script | Regra deve ser validada visualmente |
| Inteligência Comercial - Oportunidades | vendas + estoque | alto giro/margem/estoque | N/D via script | Regra do app não alterada |
| Inteligência Comercial - Produtos perigosos | vendas + margem + estoque | margem negativa/risco operacional | 553 | Sinal recalculado por margem negativa |
| Inteligência Comercial - Produtos sem giro | ml_items_details.csv | vendidos_total <= 0 e estoque > 0 | 784 | Recalculado |
| Inteligência Comercial - Impacto financeiro estimado | estoque x preço | sum(estoque parado * preço) | R$ 7.824.907,81 | Estimativa preliminar |
| Financeiro Executivo - Receita Bruta | dashboard_base_final.csv | sum(receita) | R$ 355.428,81 | OK |
| Financeiro Executivo - Comissão ML | dashboard_base_final.csv | sum(sale_fee/comissao_ml) | R$ 38.302,29 | OK |
| Financeiro Executivo - CMV | Seconds aplicado ao ML | sum(CMV total/cmv_total) | R$ 166.080,79 | OK |
| Financeiro Executivo - Frete | ml_shipments/dashboard_base_final | sum(custo_frete_final/frete_total) | R$ 36.991,50 | OK; shipments duplicados não impactaram base final |
| Financeiro Executivo - Impostos | parâmetros Seconds | sum(imposto) | R$ 60.188,99 | OK |
| Financeiro Executivo - Rateio Operacional Seconds | parâmetros Seconds | sum(custo_fixo) | R$ 16.137,93 | OK |
| Financeiro Executivo - Custos Operacionais Comerciais | Ads + custos comerciais | Ads + devoluções + outras taxas + papelaria | R$ 13.690,75 | Parcial conforme colunas disponíveis |
| Financeiro Executivo - Resultado Base | DRE | Receita - custos diretos | R$ 37.727,31 | OK |
| Financeiro Executivo - Resultado Final da Margem | DRE | Resultado Base - Custos Comerciais | R$ 24.036,56 | OK |
| Publicidade - Investimento Ads | ml_ads_metrics.csv | sum(cost) | R$ 11.913,61 | OK |
| Publicidade - Receita Atribuída Ads | ml_ads_metrics.csv | sum(revenue) | R$ 98.941,17 | OK |
| Publicidade - ROAS | ml_ads_metrics.csv | receita Ads / custo Ads | 8,30 | OK |
| Publicidade - ACOS | ml_ads_metrics.csv | custo Ads / receita Ads | 12,04% | OK |
| Publicidade - CTR | ml_ads_metrics.csv | cliques / impressões | 0,20% | OK |
| Publicidade - CPC | ml_ads_metrics.csv | custo / cliques | R$ 0,65 | OK |
| Publicidade - Conversão | ml_ads_metrics.csv | unidades / cliques | 2,65% | OK |
| Publicidade - Cobertura | ml_ads_metrics.csv | dias Ads / dias efetivos | 71,43% | Parcial |
| Operacional - Estoque total | ml_items_details.csv | sum(estoque_atual) | 31.040 | OK |
| Operacional - Sem estoque | ml_items_details.csv | estoque <= 0 | 82 | OK |
| Operacional - Estoque baixo | ml_items_details.csv | 0 < estoque <= 5 | 402 | OK |
| Operacional - Produtos parados | ml_items_details.csv | vendidos_total <= 0 e estoque > 0 | 784 | OK |
| Operacional - Capital parado | ml_items_details.csv | estoque parado x preço | R$ 7.824.907,81 | Estimativa |
| Operacional - Cobertura | estoque + vendas | estoque / venda média diária | 305,9 dias | Estimativa |
| Operacional - Crescimento por marca | dashboard_base_final.csv | comparação mensal por marca | N/D via script | Requer validação visual da aba |
| Operacional - Participação por marca | dashboard_base_final.csv | receita marca / receita total | Disponível no app | Regra não alterada |


## 8. Bases auditadas

| Arquivo | Existe | Linhas | Atualizado em | Status |
| --- | --- | --- | --- | --- |
| data/ml_orders.csv | Sim | 10505 | 02/06/2026 08:37:18 | OK |
| data/ml_shipments.csv | Sim | 10505 | 02/06/2026 08:37:19 | OK |
| data/ml_items.csv | Sim | 1000 | 02/06/2026 08:37:32 | OK |
| data/ml_items_details.csv | Sim | 1000 | 02/06/2026 08:43:29 | OK |
| data/ml_ads_campaigns.csv | Sim | 23 | 02/06/2026 08:43:31 | OK |
| data/ml_ads_metrics.csv | Sim | 345 | 02/06/2026 08:46:41 | OK |
| data/dashboard_base_final.csv | Sim | 10505 | 02/06/2026 08:46:43 | OK |
| data/jitparts.duckdb | Sim | N/D | 02/06/2026 08:46:44 | OK |
| data/base_seconds_principal.csv | Sim | 7190 | 20/05/2026 15:11:44 | OK |
| data/seconds/ReportProfitability.xlsx | Sim | Excel | 20/05/2026 12:55:40 | OK |


## 9. Duplicidades encontradas

| Componente | Duplicidade encontrada? | Impacto estimado | Correção sugerida |
| --- | --- | --- | --- |
| Receita/base final por order_id | Não | Sem impacto detectado | Nenhuma |
| Itens por pedido/item | Não | Sem impacto detectado | Nenhuma |
| Pedidos ML por id | Não | Sem impacto detectado | Nenhuma |
| Pedidos ML por order_id | Não | Sem impacto detectado | Nenhuma |
| Shipments por shipment_id | Sim | 129 linhas envolvidas | Auditar granularidade antes de deduplicar |
| Shipments por id | Não | Sem impacto detectado | Nenhuma |
| Ads por campanha/data | Não | Sem impacto detectado | Nenhuma |
| Itens ML | Não | Sem impacto detectado | Nenhuma |
| Itens detalhes | Não | Sem impacto detectado | Nenhuma |
| Seconds por item_id | Não | Sem impacto detectado | Nenhuma |


Duplicidade por `order_id` na base final não deve ser corrigida automaticamente porque a granularidade pode ser por item do pedido. Deduplicar receita por pedido sem confirmar estrutura pode subcontar itens.

## 10. Teste de fechamento da DRE

| Linha DRE | Valor |
| --- | --- |
| Receita Bruta | R$ 355.428,81 |
| (-) Comissão ML | R$ 38.302,29 |
| (-) CMV | R$ 166.080,79 |
| (-) Frete | R$ 36.991,50 |
| (-) Impostos | R$ 60.188,99 |
| (-) Rateio Operacional Seconds | R$ 16.137,93 |
| Resultado Base | R$ 37.727,31 |
| (-) Custos Operacionais Comerciais | R$ 13.690,75 |
| Resultado Final da Margem | R$ 24.036,56 |


Observação: este fechamento replica a estrutura principal do app. A linha de custos comerciais pode divergir se houver colunas explícitas de devoluções/outras tarifas adicionais que precisem entrar no cálculo executivo.

## 11. Divergências entre abas

| Métrica | Aba 1 | Aba 2 | Diferença | Status |
| --- | --- | --- | --- | --- |
| Faturamento x Receita Bruta | R$ 355.428,81 | R$ 355.428,81 | R$ 0,00 | OK se ambas usam financial_filtered |
| Pedidos x ticket médio | 2.053 | 2.053 | 0 | OK |
| Investimento Ads | R$ 11.913,61 | R$ 11.913,61 | R$ 0,00 | OK com mesmo filtro Ads |
| Estoque total | 31.040 | 31.040 | 0 | OK |


## 12. Riscos antes de liberar para diretoria

- Alto: diretoria pode comparar maio fechado do Mercado Livre contra BI com base local até 21/05/2026.
- Médio: modo Seconds Oficial usa snapshot e não representa necessariamente o mesmo período de pedidos ML.
- Médio: granularidade por item/pedido precisa permanecer documentada para evitar deduplicação indevida.
- Médio: Ads pode ter cobertura parcial e deve exibir aviso quando o período do filtro não estiver totalmente coberto.

## 13. Checklist final de liberação

- [x] Aviso de base incompleta implementado quando período solicitado excede a base.
- [x] Cabeçalho mostra período solicitado e período efetivamente analisado.
- [ ] Diretoria informada de que maio completo só pode ser conciliado após atualizar ML até 31/05/2026.
- [ ] Export oficial ML do mesmo escopo salvo para conciliação final.
- [x] `python -m py_compile app.py` executado.
- [x] Smoke HTTP em `http://127.0.0.1:8510` retornou 200 OK.
- [x] Smoke programático realizado para período dentro da base, período maior que a base, período sem dados, modo híbrido e modo Seconds Oficial.
- [ ] Smoke visual final de todas as abas no navegador. Playwright não está instalado neste ambiente.
