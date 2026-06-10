# MATCHING_CONTROLADO_IMPLEMENTADO.md

> Implementação da Camada 2 (FUZZY_AUTO_CONTROLLED) no pipeline de matching ML × Seconds  
> Arquivo de merge modificado: `merge_ml_seconds.py`  
> Arquivo de BI modificado: `app.py` (somente painel de visibilidade)  
> **Nenhum cálculo financeiro, DRE, API ou coleta de dados foi alterado.**

---

## 1. Contexto

Após a implementação do `FUZZY_AUTO` (score ≥ 85, Camada 1), restavam **59 itens `MATCH_PROVAVEL`**
(score 75–84) com **R$ 62.588 de receita** sem CMV aplicado. Este documento descreve a Camada 2,
que trata o subconjunto mais seguro desses itens (score 80–84) com filtros adicionais de segurança.

---

## 2. Pipeline Completo — 5 Etapas

```
ETAPA 1 — MATCH_EXACT             (score = 100)
    └── merge direto por item_id — comportamento original inalterado

ETAPA 2 — FUZZY_AUTO              (score ≥ 85)
    └── aprovação automática por similaridade de nome
    └── CMV aplicado normalmente

ETAPA 3 — FUZZY_AUTO_CONTROLLED   (score 80–84 + TODOS os filtros abaixo)
    └── CMV aplicado — nova camada desta implementação

ETAPA 4 — MATCH_PROVAVEL          (score 75–79 OU score 80–84 com filtros reprovados)
    └── candidato registrado — CMV NÃO aplicado — aguarda revisão manual

ETAPA 5 — SEM_MATCH               (score < 75)
    └── nenhuma ação
```

---

## 3. Filtros de Segurança da Camada Controlada

Para um item ser classificado como `FUZZY_AUTO_CONTROLLED`, **todos** os critérios abaixo devem ser satisfeitos:

| # | Critério | Parâmetro | Lógica |
|---|---|---|---|
| 1 | Score mínimo | ≥ 80 | `token_set_ratio` ou `token_sort_ratio` |
| 2 | Palavras técnicas em comum | ≥ 2 | Interseção com vocabulário automotivo (freio, junta, filtro, etc.) |
| 3 | Similaridade de comprimento | diff ≤ 30% | `abs(len_a - len_b) / max(len_a, len_b)` |
| 4 | Marca não conflitante | sem conflito | Ambas vazias = inconclusivo (não bloqueia); marcas diferentes = rejeita |
| 5 | Gap de ambiguidade | top1 − top2 ≥ 5 pts | Garante que o candidato é claramente o melhor |

Itens que passam no score 80–84 mas reprovam em qualquer filtro são **rebaixados para `MATCH_PROVAVEL`**.

---

## 4. Normalização de Texto

Função `_normalize_text()` aplicada em ambos os lados antes do scoring:
- Minúsculas + remoção de acentos (NFD)
- Remove caracteres especiais (mantém letras, números, espaço)
- Remove stop-words automotivas PT-BR:
  `para, com, sem, de, do, da, original, novo, nova, flex, gasolina, diesel, todos, universal...`

---

## 5. Novo Campo: `match_confidence`

Adicionado ao `dashboard_base_final.csv` junto com `match_type`, `match_score` e `matched_item_seconds`:

| Valor | Quando |
|---|---|
| `ALTA` | EXACT ou FUZZY_AUTO com score ≥ 92 |
| `MEDIA` | FUZZY_AUTO score < 92, ou FUZZY_AUTO_CONTROLLED |
| `BAIXA` | MATCH_PROVAVEL ou SEM_MATCH |

---

## 6. Regra de Aplicação de CMV

| match_type | CMV aplicado? |
|---|---|
| `EXACT` | ✅ Sim |
| `FUZZY_AUTO` | ✅ Sim |
| `FUZZY_AUTO_CONTROLLED` | ✅ Sim |
| `MATCH_PROVAVEL` | ❌ Não |
| `SEM_MATCH` | ❌ Não |

---

## 7. Resultados Obtidos

### Comparação Antes × Depois

| Métrica | Antes (baseline) | Depois | Delta |
|---|---|---|---|
| Receita Total | R$ 2.094.004,42 | R$ 2.094.004,42 | **+R$ 0,00** ✅ |
| Receita com CMV válido | R$ 1.884.332,70 | R$ 1.899.321,82 | +R$ 14.989,12 |
| Cobertura CMV | 89,987% | 90,703% | +0,716pp |

### Evolução por Camada

| Camada | Cobertura acumulada |
|---|---|
| Baseline (EXACT only) | 92,58% |
| + FUZZY_AUTO (≥ 85) | 95,90% |
| + FUZZY_AUTO_CONTROLLED (80–84 + filtros) | **95,91%** |

### Breakdown Final

| Tipo | Itens | Receita | % total |
|---|---|---|---|
| EXACT | 1.293 | R$ 1.938.693,00 | 92,6% |
| FUZZY_AUTO | 79 | R$ 69.420,37 | 3,3% |
| FUZZY_AUTO_CONTROLLED | **3** | R$ 287,51 | 0,01% |
| MATCH_PROVAVEL | 53 | R$ 59.265,12 | 2,8% |
| SEM_MATCH | 23 | R$ 26.338,42 | 1,3% |

---

## 8. Por que apenas 3 itens na Camada Controlada?

O filtro de **keywords técnicas em comum (≥ 2)** é o mais restritivo. A maioria dos 59 itens MATCH_PROVAVEL
tem **marca = N/D** e descrições do ML com mais palavras que a Seconds (veículos específicos no título),
o que reduz a interseção de keywords técnicas. Os 3 aprovados são todos da marca **Bastos/Bastos Juntas**
(juntas de cabeçote e carter) com nomes curtos e termos técnicos compatíveis.

Para aumentar a Camada Controlada, a ação mais efetiva é:
1. Cadastrar as marcas ausentes nos anúncios do ML
2. Reduzir `FUZZY_MIN_SHARED_KEYWORDS` de 2 para 1 (com cautela — aumenta risco de false positive)

---

## 9. Painel no BI (app.py)

Adicionado expander **"Matching Inteligente ML x Seconds"** na aba financeira, após "Produtos sem CMV Confiável":

- Métricas de cobertura por etapa (EXACT → FUZZY_AUTO → CONTROLLED)
- Tabela de breakdown por tipo e confiança
- Lista de itens MATCH_PROVAVEL para revisão manual (com candidato sugerido e score)
- Instrução de como aprovar um MATCH_PROVAVEL manualmente

---

## 10. Garantias de Segurança

| Risco | Mitigação |
|---|---|
| Sobrescrever match exato | Guard `~match_seconds` — fuzzy nunca atua em linhas já matched |
| False positive na Camada Controlada | 5 filtros obrigatórios simultâneos; threshold alto (80) |
| Contaminar DRE | MATCH_PROVAVEL não aplica CMV; apenas registra candidato |
| Receita alterada | Verificado: delta = R$ 0,00 |
| app.py quebrado | py_compile validado — OK |
| Regressão de linhas | 11.765 linhas antes e depois — idêntico |

---

## 11. Como Ajustar os Thresholds

Os parâmetros estão no início do `merge_ml_seconds.py`:

```python
FUZZY_AUTO_THRESHOLD = 85           # score >= 85: FUZZY_AUTO
FUZZY_CONTROLLED_THRESHOLD = 80    # score 80-84 + filtros: FUZZY_AUTO_CONTROLLED
FUZZY_PROVAVEL_THRESHOLD = 75       # score 75-79: MATCH_PROVAVEL
FUZZY_MIN_GAP_CONTROLLED = 5.0      # gap mínimo top1-top2
FUZZY_MIN_SHARED_KEYWORDS = 2       # mín de keywords técnicas em comum
FUZZY_MAX_LENGTH_DIFF = 0.30        # máx diferença de comprimento
```

Para desativar o fuzzy completamente: `FUZZY_AUTO_THRESHOLD = 101`

---

## 12. Próximos Passos para >96% de Cobertura

Os 53 itens `MATCH_PROVAVEL` remanescentes (R$ 59.265) são o principal alvo:

1. **Revisar a lista no painel BI** → expander "Matching Inteligente" → tabela MATCH_PROVAVEL
2. Para cada item confirmado: cadastrar o `item_id` ML em `parametros_financeiros_seconds.csv`
3. Regenerar base: `python merge_ml_seconds.py`
4. Cobertura esperada pós-revisão manual: **≥ 98%**
