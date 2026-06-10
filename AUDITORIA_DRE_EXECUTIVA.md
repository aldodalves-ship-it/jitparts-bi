# Auditoria Financeira da DRE Executiva

Data da auditoria: 2026-05-29  
Arquivo auditado: `app.py`  
Recorte usado para reproduzir a Receita Bruta informada no dashboard: 29/04/2026 a 21/05/2026, modo `Estimativa Hibrida ML + Seconds`.

## 1. Mapeamento da DRE

| Linha DRE | Funcao | Fonte | Colunas | Formula |
|---|---|---|---|---|
| Receita Bruta | `calculate_executive_financials` / `build_dre_executiva` | ML enriquecido ou Seconds Oficial, conforme modo | `receita`, `faturamento`, `faturamento_seconds` | soma da primeira coluna disponivel |
| Comissao ML | `calculate_executive_financials` / `use_hybrid_financial_columns` | Hibrido: Seconds quando confiavel, fallback ML `sale_fee`; Oficial: Seconds | `sale_fee`, `comissao_ml`, `comissao_total`, `comissao_seconds` | soma da primeira coluna disponivel |
| CMV | `calculate_executive_financials` | Seconds | `CMV total`, `cmv_total`, `cmv_seconds` | soma da primeira coluna disponivel |
| Frete | `calculate_executive_financials` | Seconds/parametros enriquecidos; ML shipment fica disponivel mas nao e usado na DRE | `custo_frete_final`, `frete_total`, `frete_seconds` | soma da primeira coluna disponivel |
| Impostos | `calculate_executive_financials` | Seconds | `imposto_total`, `imposto`, `imposto_seconds` | soma da primeira coluna disponivel |
| Rateio Operacional Seconds | `calculate_executive_financials` | Seconds | `custo_fixo_total`, `custo_fixo`, `custo_fixo_seconds` | soma da primeira coluna disponivel |
| Resultado Base | `calculate_executive_financials` | Calculo interno | campos acima | Receita - CMV - Comissao - Frete - Impostos - Rateio |
| Custos Operacionais Comerciais | `calculate_executive_financials` / `build_commercial_operational_costs` | ML Ads + Seconds/ML enriquecido + regra interna | `ads cost`, FULL/frete, devolucao, outras taxas, frete Extrema, papelaria | Ads + FULL + Devolucoes + Outras Tarifas + Frete Extrema + Receita x 0,5% |
| Resultado Final da Margem | `calculate_executive_financials` | Calculo interno | Resultado Base, Custos Operacionais Comerciais | Resultado Base - Custos Operacionais Comerciais |

Referencias principais: `app.py:1873`, `app.py:2071`, `app.py:2703`, `app.py:5017`, `app.py:5058`, `app.py:5162`.

## 2. Duplicidade

DUPLICIDADE IDENTIFICADA: SIM.

| Componente | Onde entra primeiro | Onde entra novamente | Impacto estimado no recorte |
|---|---|---|---:|
| Mercado Envios FULL | Linha `Frete`: `frete_total`/`custo_frete_final` ja inclui frete dos pedidos FULL | Custos Operacionais Comerciais: `full_value` soma o frete das linhas FULL | R$ 29.252,35 |
| Frete para Extrema | Potencialmente em `Frete` quando houver custo logistico nas mesmas linhas | Custos Operacionais Comerciais: `frete_extrema_value` | R$ 0,00 no recorte |

Nao foi identificada duplicidade atual para Ads, Devolucoes, Outras Tarifas, Comissao ML ou Rateio Operacional Seconds. Ads entra somente no bloco comercial. Devolucoes e Outras Tarifas estao zeradas por ausencia de coluna explicita no CSV atual.

## 3. Conciliacao Mercado Livre

| Coleta | Endpoint | Campos coletados/usados | Campos ignorados ou nao persistidos |
|---|---|---|---|
| Vendas | `https://api.mercadolibre.com/orders/search` | `order_id`, `date_created`, `status`, `total_amount`, `paid_amount`, `item_id`, `quantity`, `unit_price`, `sale_fee`, `listing_type_id` | Detalhe financeiro completo do pedido, pagamentos/repasse, ajustes, descontos, estornos e breakdown de charges |
| Shipment/Frete | `/orders/{order_id}` e `/shipments/{shipment_id}` | `logistic_type`, `shipping_option.cost`, `shipping_option.list_cost`, `receiver_cost`, `sender_cost` | Demais componentes internos do shipment e eventuais ajustes financeiros nao expostos nas colunas persistidas |
| Ads | `/advertising/MLB/product_ads/campaigns/{id}` e `/advertising/MLB/advertisers/{id}/product_ads/campaigns/search` | `clicks`, `prints`, `ctr`, `cost`, `cpc`, `acos`, `cvr`, `roas`, `units_quantity`, `total_amount` | Segmentacoes/cortes nao persistidos; historico limitado ao CSV atual |
| Seconds | `ReportProfitability.xlsx` processado localmente | CMV, comissao, frete, imposto, custo fixo, lucro, margem, vendidos | Nao e API ML; serve como base gerencial parametrizada |

O dashboard esta utilizando 100% das informacoes financeiras disponiveis da API? NAO.

Pode ser incorporado, se aprovado: detalhe financeiro completo por pedido, pagamentos/repasse, descontos, ajustes, estornos/refunds/claims, breakdown de taxas extras/outros servicos e conciliacao oficial de frete/tarifas por pedido.

## 4. Auditoria da Receita

| Origem | Valor |
|---|---:|
| Mercado Livre informado no print | R$ 501.027,00 |
| Dashboard reproduzido no CSV atual | R$ 398.604,29 |
| Diferenca | R$ 102.422,71 |
| Motivo principal provavel | O CSV do dashboard termina em 21/05/2026; o print do ML provavelmente inclui dias posteriores. No recorte reproduzido, o dashboard e o `ml_orders.csv` batem exatamente em R$ 398.604,29. |

Detalhes do recorte 29/04/2026 a 21/05/2026:

| Item | Valor |
|---|---:|
| Receita total dashboard/raw ML local | R$ 398.604,29 |
| Pedidos pagos | R$ 372.684,72 |
| Pedidos cancelados incluidos no dashboard | R$ 25.919,57 |
| Pedidos sem CMV | R$ 40.318,96 |
| Pedidos sem enrich Seconds | R$ 32.041,10 |
| Ultima data da base dashboard | 21/05/2026 |
| Diferenca vs print em dias medios do recorte | ~5,9 dias de venda media |

Filtros aplicados pelo dashboard: periodo, marca, categoria, FULL, Flex, status do anuncio, status de estoque, listing type, produto e MLB (`apply_filters`). Sem filtros adicionais, a receita bate com o CSV ML local para o periodo reproduzido.

## 5. Custos Operacionais Comerciais

| Item | Valor | % Receita | Fonte |
|---|---:|---:|---|
| Ads | R$ 18.267,54 | 4,58% | Mercado Ads + estimativa temporal |
| FULL | R$ 29.252,35 | 7,34% | Linhas FULL usando frete parametrizado |
| Devolucoes | R$ 0,00 | 0,00% | Coluna explicita ausente |
| Outras Tarifas | R$ 0,00 | 0,00% | Coluna explicita ausente |
| Frete para Extrema | R$ 0,00 | 0,00% | Nao identificado no recorte |
| Papelaria | R$ 1.993,02 | 0,50% | Regra interna: Receita x 0,5% |
| Total | R$ 49.512,91 | 12,42% | Soma dos itens |

Formula: `18.267,54 + 29.252,35 + 0,00 + 0,00 + 0,00 + 1.993,02 = 49.512,91`.

## 6. Comparacao com relatorio financeiro local ML

| Componente | Mercado Livre local | Dashboard | Diferenca |
|---|---:|---:|---:|
| Tarifas de venda | R$ 43.537,03 (`sale_fee`) | R$ 41.069,50 | -R$ 2.467,53 |
| Tarifas de envio | R$ 46.438,62 (`shipping_option_list_cost`) | R$ 41.325,55 | -R$ 5.113,07 |
| Publicidade | R$ 11.913,61 real no CSV | R$ 18.267,54 | +R$ 6.353,93 estimado |
| FULL | R$ 28.909,44 (`shipping_option_list_cost` FULL) | R$ 29.252,35 | +R$ 342,91 |
| Devolucoes | N/D custo real; cancelados R$ 25.919,57 em vendas | R$ 0,00 | N/D |
| Outras Tarifas | N/D | R$ 0,00 | N/D |
| Total tarifas/investimentos comparaveis | R$ 101.980,10 | R$ 128.427,29* | +R$ 26.447,19 |

`*` Soma dashboard incluindo Frete DRE, Comissao DRE e Custos Operacionais Comerciais. A diferenca e afetada pela duplicidade do FULL e pela estimativa de Ads.

## 7. Teste de fechamento

Receita Bruta: R$ 398.604,29  
(-) Comissao ML: R$ 41.069,50  
(-) CMV: R$ 187.124,46  
(-) Frete: R$ 41.325,55  
(-) Impostos: R$ 67.885,95  
(-) Rateio Operacional Seconds: R$ 18.165,82  
= Resultado Base: R$ 43.033,01  
(-) Custos Operacionais Comerciais: R$ 49.512,91  
= Resultado Final da Margem: -R$ 6.479,90

O fechamento matematico da DRE esta consistente com o codigo atual. A consistencia financeira gerencial fica ressalvada pela duplicidade identificada no FULL.

## 8. Tooltips

Implementado em `app.py` sem alterar calculos:

- `DRE_TOOLTIPS` em `app.py:79`
- renderizacao na DRE em `render_dre_executiva`, `app.py:2765`

Validacao tecnica: `python -m py_compile app.py` executado com sucesso.

## Conclusao

A DRE fecha matematicamente com as regras atuais, mas NAO esta plenamente consistente financeiramente porque o componente Mercado Envios FULL e contado duas vezes: uma dentro de Frete e outra dentro dos Custos Operacionais Comerciais. A divergencia de Receita contra o print do Mercado Livre e explicada principalmente por diferenca temporal/base desatualizada: o dashboard local termina em 21/05/2026, enquanto o print informado aparenta contemplar vendas posteriores.
