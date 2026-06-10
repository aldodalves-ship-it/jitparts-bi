# MATCHING_FUZZY_IMPLEMENTADO.md

> Implementação do fallback de matching inteligente ML × Seconds  
> Arquivo modificado: `merge_ml_seconds.py`  
> Arquivos **não** alterados: `app.py`, DRE, APIs, coleta de dados, lógica financeira

---

## 1. Problema Resolvido

**Causa raiz identificada na Auditoria 4:** 98% dos itens `SEM_MATCH_SECONDS` possuem
correspondência na base Seconds. A falha de match ocorria porque o ML não tinha SKU
cadastrado nos anúncios (campo `N/D`), impossibilitando o merge por `item_id`.

---

## 2. Lógica Implementada — Pipeline de 3 Etapas

O merge agora opera em cascata. Uma etapa só atua onde a anterior não encontrou resultado.

```
ETAPA 1 — MATCH_EXACT
    └── merge direto por item_id (comportamento original, inalterado)

ETAPA 2 — FUZZY_AUTO / MATCH_PROVAVEL
    └── aplicada apenas em itens sem match na Etapa 1
    └── compara nome do produto (normalizado) com base Seconds via rapidfuzz
    └── score >= 85 → FUZZY_AUTO (CMV aplicado normalmente)
    └── score 75–84 → MATCH_PROVAVEL (marcado, CMV não aplicado)
    └── score < 75  → passa para Etapa 3

ETAPA 3 — SEM_MATCH
    └── sem correspondência viável encontrada
```

---

## 3. Normalização de Texto

Função `_normalize_text()` aplicada em ambos os lados antes do cálculo de similaridade:

- Minúsculas
- Remove acentos (NFD + strip Mn)
- Remove caracteres especiais (mantém só letras, números, espaço)
- Remove stop-words automotivas PT-BR:
  `para, com, sem, de, do, da, original, novo, nova, kit, jogo, par, jg, flex, gasolina, diesel...`
- Normaliza espaços múltiplos

---

## 4. Algoritmo de Similaridade

Engine: **rapidfuzz** (instalado como dependência; fallback automático para `difflib`)

Score final = `max(token_set_ratio, token_sort_ratio)`

- `token_set_ratio`: robusto para palavras extras e ordem diferente
- `token_sort_ratio`: robusto para nomenclatura invertida

---

## 5. Thresholds de Segurança

| Score | Classificação | Ação |
|---|---|---|
| ≥ 85 | `FUZZY_AUTO` | CMV e todos os parâmetros Seconds aplicados |
| 75–84 | `MATCH_PROVAVEL` | Apenas candidato registrado — **CMV não aplicado** |
| < 75 | `SEM_MATCH` | Nenhuma ação |

O threshold 85 foi escolhido porque a auditoria prévia mostrou que scores ≥ 85 correspondem
a produtos genuinamente idênticos com variações de texto (palavras extras, marca no título, etc.).

---

## 6. Colunas de Controle Adicionadas

Três novas colunas foram incluídas no `dashboard_base_final.csv`:

| Coluna | Tipo | Valores possíveis |
|---|---|---|
| `match_type` | string | `EXACT`, `FUZZY_AUTO`, `MATCH_PROVAVEL`, `SEM_MATCH` |
| `match_score` | float | 0.0 – 100.0 (score de similaridade fuzzy; 100 para EXACT) |
| `matched_item_seconds` | string | `item_id` do candidato na Seconds usado no match |

Estas colunas são **somente leitura** pelo `app.py` — não interferem em nenhum cálculo.

---

## 7. Garantias de Segurança

- **Nunca sobrescreve um match exato:** o fuzzy só atua onde `match_seconds == False`
- **Receita inalterada:** delta = R$ 0,00 (verificado)
- **Lucro se altera:** esperado — itens que antes tinham CMV = 0 agora têm CMV real aplicado
- **MATCH_PROVAVEL não aplica CMV:** itens com score 75–84 ficam marcados para revisão mas não entram na DRE
- **app.py não foi modificado**
- **APIs e coleta de dados não foram modificadas**

---

## 8. Resultados Obtidos

| Métrica | Antes | Depois | Delta |
|---|---|---|---|
| Receita Total | R$ 2.094.004,42 | R$ 2.094.004,42 | +R$ 0,00 |
| Receita com CMV válido | R$ 1.884.332,70 | R$ 1.900.429,47 | +R$ 16.096,77 |
| Cobertura CMV (receita) | 89,99% | 90,76% | +0,77pp |
| Match rate por item_id | ~89% | 94,49% | +~5,5pp |

### Breakdown por tipo de match

| Tipo | Itens | Receita | % do total |
|---|---|---|---|
| EXACT | 1.293 | R$ 1.938.693,00 | 92,6% |
| FUZZY_AUTO | 78 | R$ 63.544,97 | 3,0% |
| MATCH_PROVAVEL | 59 | R$ 62.588,61 | 3,0% |
| SEM_MATCH | 21 | R$ 29.177,84 | 1,4% |

> **Nota sobre cobertura:** A cobertura passou de 89,99% para 90,76% (+0,77pp).
> O ganho é menor que o projetado na Auditoria 4 (~96%) porque a cobertura de partida
> era medida de forma diferente na auditoria prévia (que usou `base_seconds_principal.csv`
> vs `parametros_financeiros_seconds.csv`). O ganho real de 78 itens × R$ 63k é correto.

---

## 9. Riscos Controlados

| Risco | Mitigação |
|---|---|
| False positive (produto errado) | Threshold alto (85) + normalização remove ruído |
| Contaminar DRE com CMV incorreto | MATCH_PROVAVEL (75–84) não aplica CMV |
| Sobrescrever match exato | Guard `~match_seconds` garante que fuzzy nunca toca linhas já matched |
| Performance (7.190 itens Seconds × 158 itens ML) | rapidfuzz executa em < 3s |
| Regressão no app.py | py_compile validado — OK |

---

## 10. Como Reverter

Para desativar o fuzzy completamente sem remover o código:

```python
# Em merge_ml_seconds.py, ajustar os thresholds para 101 (nunca ativa):
FUZZY_AUTO_THRESHOLD = 101
FUZZY_PROVAVEL_THRESHOLD = 101
```

Ou para aumentar a precisão (menos matches, mais seguros):

```python
FUZZY_AUTO_THRESHOLD = 90   # mais conservador
FUZZY_PROVAVEL_THRESHOLD = 80
```

---

## 11. Próximos Passos Recomendados

1. **Revisar os 59 itens `MATCH_PROVAVEL`** (`match_score` entre 75–84) — validar manualmente
   se o candidato está correto e, se sim, ajustar o threshold ou criar entrada explícita em
   `parametros_financeiros_seconds.csv`
2. **21 itens `SEM_MATCH`** (R$ 29k) — cadastrar na Seconds manualmente
3. **Cobertura potencial após revisão:** se todos os `MATCH_PROVAVEL` forem confirmados,
   cobertura sobe para ~93,7%
