# AUDITORIA 4 — CORRESPONDÊNCIA ML × SECONDS (MATCHING INTELIGENTE)

> Gerado automaticamente. Somente leitura — nenhum cálculo financeiro ou base foi alterada.  
> Engine de similaridade: **rapidfuzz**

---

## 1. Resumo Executivo

| Indicador | Valor |
|---|---|
| Total itens SEM_MATCH_SECONDS analisados | **159** |
| Receita impactada (sem CMV) | **R$ 155.311,42** |
| % da receita total sem CMV | **7,42%** |
| Cobertura CMV atual | **89,99%** |
| MATCH_AUTOMATICO encontrados (score ≥ 90) | **69** |
| MATCH_PROVAVEL encontrados (score 75–89) | **74** |
| MATCH_DUVIDOSO (score 60–74) | **15** |
| SEM_CORRESPONDENCIA (score < 60) | **1** |

### Receita Recuperável

| Cenário | Receita | Nova Cobertura CMV |
|---|---|---|
| Aplicar MATCH_AUTOMATICO | **R$ 69.118,52** | **93,29%** |
| Aplicar + MATCH_PROVAVEL | **R$ 131.271,64** | **96,26%** |

---

## 2. Impacto Financeiro por Tipo de Match

| Tipo | Receita | Pedidos | Itens | pct_receita_sem_cmv |
| --- | --- | --- | --- | --- |
| MATCH_AUTOMATICO | R$ 69.118,52 | 253 | 69 | 44,50% |
| MATCH_PROVAVEL | R$ 62.153,12 | 298 | 73 | 40,02% |
| MATCH_DUVIDOSO | R$ 23.761,83 | 70 | 15 | 15,30% |
| SEM_CORRESPONDENCIA | R$ 277,95 | 3 | 1 | 0,18% |

---

## 3. Ganho Potencial de Cobertura

| Cenário | Receita recuperada | Nova cobertura CMV (%) | Receita ainda sem CMV |
| --- | --- | --- | --- |
| Aplicar MATCH_AUTOMATICO (score ≥ 90) | R$ 69.118,52 | 93,29% | R$ 86.192,90 |
| Aplicar MATCH_AUTOMATICO + MATCH_PROVAVEL (score ≥ 75) | R$ 131.271,64 | 96,26% | R$ 24.039,78 |

---

## 4. Top 20 Itens para Ação Manual — SEM_CORRESPONDENCIA

Estes itens **não encontraram candidato adequado** na base Seconds e precisam de cadastro manual.

| item_id | produto_ml | marca_ml | receita | pedidos | candidato_seconds_produto | score_similaridade | padrao_erro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MLB5018697386 | Silicone Alta Temperatura Red ( Vermelho ) - Bastos | N/D | R$ 277,95 | 3 | Par De Disco De Freio Original Astra / Vectra | 58.33 | sku_ausente_ml; palavras_extras_ml |

---

## 5. Top 20 Itens para Revisão — MATCH_DUVIDOSO

Estes itens têm score entre 60–74. Precisam de revisão humana para confirmar ou rejeitar.

| item_id | produto_ml | marca_ml | receita | pedidos | candidato_seconds_produto | score_similaridade | padrao_erro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MLB4096861467 | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | N/D | R$ 5.310,35 | 18 | Pastilha Freio Vitara (ly) 1.6 2015 Em Diante | 68.75 | sku_ausente_ml; palavras_extras_ml |
| MLB6171701742 | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | N/D | R$ 3.504,57 | 2 | Molas Esportivas Eibach Porsche Macan 3.0 S 3.6 Turbo 2014+ | 73.68 | sku_ausente_ml; palavras_extras_ml |
| MLB6520374496 | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | N/D | R$ 3.163,68 | 14 | Jogo Junta Superior Cabeçote Motor Cruze 1.8 16v 2012/2016 | 73.53 | sku_ausente_ml; palavras_extras_ml |
| MLB5410760486 | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | Eibach | R$ 2.364,00 | 1 | Molas Eibach Pro-kit Vw Golf 2.0 Mk4 \| Mk4,5 De 1999 À 2013 | 71.19 | sku_ausente_ml; palavras_extras_ml |
| MLB6502062310 | Cano Duplo De Água Do Motor Para Amarok 2.0 16v 2010/... Preto | N/D | R$ 1.771,88 | 9 | Par Disco De Freio Diant Amarok 2.0 16v 2010 A 2018 | 73.47 | sku_ausente_ml; palavras_extras_ml |
| MLB4404425007 | Par Disco De Freio Dianteiro Para Volare V6 6000 2004 À 2012 | N/D | R$ 1.730,96 | 3 | Pastilha Freio A-class (w169) A 200 2004 A 2012 | 73.91 | sku_ausente_ml; palavras_extras_ml |
| MLB5663268708 | Tambor Campana Freio Traseira Fusca 4 Furos C/cubo Par | N/D | R$ 1.701,24 | 4 | Parafusos De Cabeçote Honda Fit 1.5 16v Gas/flex 2005 Á 2015 | 60.0 | sku_ausente_ml; palavras_extras_ml |
| MLB4404424995 | Par De Disco De Freio Dianteiro Sprinter 313 413 2002 À 2006 | N/D | R$ 1.652,34 | 5 | Pastilha Freio Dianteira Hb20 1.0 2020 A 2026 | 69.57 | sku_ausente_ml; palavras_extras_ml |
| MLB4404893661 | Jogo Junta Cabeçote Sentra Tiida Versa Fluence 1.8 2.0 06/19 | N/D | R$ 998,77 | 4 | Jogo Aneis Motor Std Sentra Tiida Fluence 1.8 2.0 16v 07/21 | 74.29 | sku_ausente_ml; palavras_extras_ml |
| MLB4419938395 | Pastilha De Freio Brembo Dianteira Up Tsi 1.0t 105hp P85041 | N/D | R$ 720,96 | 2 | Pastilha Freio Dianteiro Cerâmica Brembo Vw Up Tsi 2015 + | 68.0 | sku_ausente_ml; palavras_extras_ml |
| MLB6239427120 | Filtro De Óleo K&n Quadriciclos Can-am Jetski Sea Doo Spark | N/D | R$ 373,29 | 3 | Filtro Oleo Lubrificante Tiguan Jetta Passat Fusca 2.0 Mann | 63.04 | sku_ausente_ml; palavras_extras_ml |
| MLB4063268593 | Kit 3 Aditivo 100 Ml Otimizador Combustivel Flex 4x1 Fq4 | N/D | R$ 136,00 | 2 | Filtro De Combustível Aditivo Gasolina Etanol Flex 1l Fq4 | 73.02 | sku_ausente_ml; palavras_extras_ml |
| MLB6239553452 | Filtro Oleo K&n Kn-145 Yamaha Xt660 E Xt660r Mt-03 Tdm Todas | N/D | R$ 119,99 | 1 | Filtro Oleo K&n - Yamaha Xtz250 Xtz 250 Lander / 2023 2024 | 69.39 | sku_ausente_ml; palavras_extras_ml |
| MLB6239266218 | Filtro Oleo K&n Kn-112 Kawasaki D-tracker 250x | N/D | R$ 115,98 | 1 | Filtro De Óleo K&n Kn-401 Compatível Com Ninja 250 \| Zx11 | 69.23 | sku_ausente_ml; palavras_extras_ml |
| MLB5457247288 | Jogo De Pastilhas De Freio Diant Hb20 Hb20s 1.6 Desde 2012 | N/D | R$ 97,82 | 1 | Jogo Pastilhas Freio Dianteiras Com Abs Sonic 2012 A 2014 | 69.44 | sku_ausente_ml; palavras_extras_ml |

---

## 6. Padrões de Erro Detectados

| padrao | ocorrencias |
| --- | --- |
| sku_ausente_ml | 156 |
| palavras_extras_ml | 85 |
| palavras_extras_seconds | 21 |
| nomenclatura_invertida | 9 |
| sku_divergente | 3 |

### Descrição dos Padrões

| Padrão | Descrição |
|---|---|
| `sku_formatacao` | SKU igual mas com diferença de hífen, espaço ou ponto (ex: `S-1410` vs `S1410`) |
| `sku_zeros_extras` | SKU com zeros extras à esquerda |
| `sku_prefixo_sufixo` | SKU do ML contém ou está contido no SKU da Seconds |
| `sku_divergente` | SKUs completamente diferentes apesar do nome similar |
| `sku_ausente_ml` | Item do ML sem SKU cadastrado (campo N/D) |
| `sku_ausente_seconds` | Candidato na Seconds sem SKU cadastrado |
| `nomenclatura_invertida` | Mesmo conjunto de palavras em ordem diferente |
| `palavras_extras_ml` | ML tem mais palavras que a Seconds (descrição mais longa) |
| `palavras_extras_seconds` | Seconds tem mais palavras que o ML |
| `sem_padrao_claro` | Diferença não se encaixa nos padrões acima |

---

## 7. Sugestões de Melhoria no Algoritmo de Merge

### 7.1 Normalização de Texto
- Aplicar `normalize()` nos dois lados antes do merge (lowercase + sem acento + sem especiais)
- Remover stop words automotivas (para, com, dianteiro, traseiro, etc.)

### 7.2 Padronização de SKU
- Remover hífens, espaços e pontos antes do merge: `re.sub(r'[\s\-\./]', '', sku.upper())`
- Criar coluna `sku_normalizado` em ambas as bases antes do join

### 7.3 Fuzzy Matching no Merge Atual
- Substituir o merge por item_id puro por um pipeline de múltiplos passes:
  1. **Passo 1:** merge exato por item_id (atual — mantém)
  2. **Passo 2:** merge por SKU normalizado para itens sem match
  3. **Passo 3:** fuzzy matching por nome do produto para itens ainda sem match

### 7.4 Tabela Auxiliar de Equivalência SKU
- Criar arquivo `data/sku_equivalencias.csv` com colunas: `sku_ml`, `sku_seconds`, `item_id_ml`
- Aplicar este mapeamento antes do merge principal

### 7.5 Dicionário de Sinônimos
- Exemplos identificados:
  - "jogo" = "kit" = "jg" = "conjunto"
  - "diant." = "dianteiro" = "dianteira"
  - "tras." = "traseiro" = "traseira"
  - "pastilha" = "pastilhas" (plural)
  - Variações com/sem marca no título

---

## 8. Plano de Correção — Priorização

### Fase 1 — Automático (sem esforço manual)
- Implementar merge por SKU normalizado → recupera itens com `sku_formatacao`
- Estimativa de itens recuperáveis: todos com `padrao_erro` = `sku_formatacao`

### Fase 2 — Revisão rápida (MATCH_AUTOMATICO + MATCH_PROVAVEL)
- 143 itens com score ≥ 75 para validação humana rápida (confirmar ou rejeitar candidato)
- Receita potencial: R$ 131.271,64

### Fase 3 — Cadastro manual (SEM_CORRESPONDENCIA + MATCH_DUVIDOSO)
- 16 itens sem candidato adequado
- Priorizar pelos de maior receita (Top 20 listados acima)
- Ação: cadastrar na Seconds ou criar tabela de equivalência

### Objetivo Final
- Cobertura atual: **89,99%**
- Meta após Fase 1+2: **96,26%**
- Meta após Fase 3 (manual): **≥ 98%**

---

## 9. Observações de Controle

- Nenhum arquivo de dados foi alterado por esta auditoria
- `app.py`, `dashboard_base_final.csv` e regras financeiras estão intactos
- Os resultados estão em `resultado/matching_inteligente_seconds.csv`
- Para aplicar as correções, editar `data/parametros_financeiros_seconds.csv` ou criar tabela de equivalência
