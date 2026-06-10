"""AUDITORIA 4 — CORRESPONDÊNCIA ML × SECONDS (MATCHING INTELIGENTE)

Objetivo: Identificar por que os itens classificados como SEM_MATCH_SECONDS não estão
sendo encontrados na Seconds e recuperar automaticamente o máximo possível da cobertura CMV.

IMPORTANTE: Somente leitura e simulação. Não altera app.py, base final, DRE ou regras financeiras.

Saídas:
    resultado/matching_inteligente_seconds.csv
    AUDITORIA_MATCHING_ML_SECONDS.md
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Dependência opcional: rapidfuzz (mais rápida que python-Levenshtein/fuzzywuzzy)
# Fallback para difflib se não estiver instalada.
# ---------------------------------------------------------------------------
try:
    from rapidfuzz import fuzz as _fuzz
    from rapidfuzz import process as _process

    def ratio(a: str, b: str) -> float:
        return _fuzz.ratio(a, b)

    def partial_ratio(a: str, b: str) -> float:
        return _fuzz.partial_ratio(a, b)

    def token_sort_ratio(a: str, b: str) -> float:
        return _fuzz.token_sort_ratio(a, b)

    def token_set_ratio(a: str, b: str) -> float:
        return _fuzz.token_set_ratio(a, b)

    FUZZY_ENGINE = "rapidfuzz"

except ImportError:
    try:
        from fuzzywuzzy import fuzz as _fw_fuzz  # type: ignore

        def ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.ratio(a, b))

        def partial_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.partial_ratio(a, b))

        def token_sort_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.token_sort_ratio(a, b))

        def token_set_ratio(a: str, b: str) -> float:
            return float(_fw_fuzz.token_set_ratio(a, b))

        FUZZY_ENGINE = "fuzzywuzzy"

    except ImportError:
        import difflib

        def ratio(a: str, b: str) -> float:
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

        def partial_ratio(a: str, b: str) -> float:
            if len(b) == 0:
                return 0.0
            best = 0.0
            len_a = len(a)
            for start in range(len(b) - len_a + 1):
                sub = b[start : start + len_a]
                s = difflib.SequenceMatcher(None, a, sub).ratio() * 100
                if s > best:
                    best = s
            return best if len_a <= len(b) else ratio(a, b)

        def token_sort_ratio(a: str, b: str) -> float:
            return ratio(" ".join(sorted(a.split())), " ".join(sorted(b.split())))

        def token_set_ratio(a: str, b: str) -> float:
            set_a = set(a.split())
            set_b = set(b.split())
            inter = " ".join(sorted(set_a & set_b))
            only_a = " ".join(sorted(set_a - set_b))
            only_b = " ".join(sorted(set_b - set_a))
            t0 = inter
            t1 = (inter + " " + only_a).strip()
            t2 = (inter + " " + only_b).strip()
            return max(ratio(t0, t1), ratio(t0, t2), ratio(t1, t2))

        FUZZY_ENGINE = "difflib (fallback)"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULT_DIR = BASE_DIR / "resultado"

SEM_CMV_PATH = RESULT_DIR / "itens_sem_cmv_completo.csv"
SECONDS_PATH = DATA_DIR / "base_seconds_principal.csv"
OUTPUT_CSV = RESULT_DIR / "matching_inteligente_seconds.csv"
OUTPUT_MD = BASE_DIR / "AUDITORIA_MATCHING_ML_SECONDS.md"


# ---------------------------------------------------------------------------
# Palavras comuns removidas na normalização (stop words automotivas PT-BR)
# ---------------------------------------------------------------------------
STOP_WORDS = {
    "para", "com", "sem", "de", "do", "da", "dos", "das", "e", "em", "a",
    "o", "os", "as", "um", "uma", "no", "na", "por", "ate", "entre",
    "original", "novo", "nova", "kit", "jogo", "par", "jg", "conjunto",
    "completo", "completa", "todos", "todas", "modelo", "modelos",
    "motor", "dianteiro", "dianteira", "traseiro", "traseira",
    "freio", "freios", "pastilha", "disco", "tambor",
    "flex", "gasolina", "diesel", "turbo", "aspirado",
    "std", "oem", "original", "genuino", "genuina",
    "universal", "compativel", "compativel", "todos",
}


def normalize(text: object) -> str:
    """Normaliza texto para matching: minúsculas, sem acento, sem especiais, sem stop words."""
    if pd.isna(text) or str(text).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(text).strip().lower()
    # remove acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # remove caracteres especiais (mantém letras, números, espaço)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # normaliza espaços múltiplos
    s = re.sub(r"\s+", " ", s).strip()
    # remove stop words
    tokens = [t for t in s.split() if t not in STOP_WORDS and len(t) > 1]
    return " ".join(tokens)


def normalize_sku(sku: object) -> str:
    """Normaliza SKU: maiúsculas, sem espaço, sem hífen/ponto."""
    if pd.isna(sku) or str(sku).strip().lower() in {"n/d", "nan", "none", "", "nat"}:
        return ""
    s = str(sku).strip().upper()
    s = re.sub(r"[\s\-\./]", "", s)
    return s


def best_score(query: str, candidate: str) -> float:
    """Score máximo entre 4 métodos de similaridade."""
    if not query or not candidate:
        return 0.0
    scores = [
        ratio(query, candidate),
        partial_ratio(query, candidate),
        token_sort_ratio(query, candidate),
        token_set_ratio(query, candidate),
    ]
    return max(scores)


def classify_match(score: float) -> str:
    if score >= 90:
        return "MATCH_AUTOMATICO"
    if score >= 75:
        return "MATCH_PROVAVEL"
    if score >= 60:
        return "MATCH_DUVIDOSO"
    return "SEM_CORRESPONDENCIA"


def identify_error_pattern(ml_produto: str, sec_produto: str, ml_sku: str, sec_sku: str) -> str:
    """Tenta identificar o padrão de erro entre os dois descritores."""
    patterns = []

    # SKU: diferenças de hífen/espaço/prefixo
    if ml_sku and sec_sku:
        if ml_sku != sec_sku:
            if re.sub(r"[\s\-\./]", "", ml_sku.upper()) == re.sub(r"[\s\-\./]", "", sec_sku.upper()):
                patterns.append("sku_formatacao")
            elif ml_sku.upper().lstrip("0") == sec_sku.upper().lstrip("0"):
                patterns.append("sku_zeros_extras")
            elif ml_sku.upper() in sec_sku.upper() or sec_sku.upper() in ml_sku.upper():
                patterns.append("sku_prefixo_sufixo")
            else:
                patterns.append("sku_divergente")
    elif not ml_sku:
        patterns.append("sku_ausente_ml")
    elif not sec_sku:
        patterns.append("sku_ausente_seconds")

    # Produto: palavras extras / invertidas
    if ml_produto and sec_produto:
        ml_tokens = set(normalize(ml_produto).split())
        sec_tokens = set(normalize(sec_produto).split())
        if ml_tokens == sec_tokens:
            patterns.append("nomenclatura_invertida")
        elif len(ml_tokens - sec_tokens) > 2:
            patterns.append("palavras_extras_ml")
        elif len(sec_tokens - ml_tokens) > 2:
            patterns.append("palavras_extras_seconds")

    return "; ".join(patterns) if patterns else "sem_padrao_claro"


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float) -> str:
    return f"{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sem registros._"
    df2 = df.copy().fillna("").astype(str)
    headers = list(df2.columns)
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df2.iterrows():
        cells = [str(row[h]).replace("|", "\\|").replace("\n", " ").strip() or " " for h in headers]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ===========================================================================
# CARREGAMENTO
# ===========================================================================

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not SEM_CMV_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {SEM_CMV_PATH}")
    if not SECONDS_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {SECONDS_PATH}")

    sem_cmv = pd.read_csv(SEM_CMV_PATH, low_memory=False)
    seconds = pd.read_csv(SECONDS_PATH, low_memory=False)
    return sem_cmv, seconds


# ===========================================================================
# MATCHING INTELIGENTE
# ===========================================================================

def run_matching(sem_cmv: pd.DataFrame, seconds: pd.DataFrame) -> pd.DataFrame:
    # Filtrar apenas SEM_MATCH_SECONDS
    itens_df = sem_cmv[sem_cmv["motivo_sem_cmv"] == "SEM_MATCH_SECONDS"].copy()
    print(f"  Itens SEM_MATCH_SECONDS: {len(itens_df)}")

    # Preparar colunas da base Seconds
    sec_norm_produto = seconds["produto"].apply(normalize).tolist()
    sec_norm_sku = seconds["sku"].apply(normalize_sku).tolist()
    sec_produtos = seconds["produto"].fillna("").tolist()
    sec_skus = seconds["sku"].fillna("").tolist()
    sec_item_ids = seconds["item_id"].fillna("").tolist()
    sec_marcas = seconds["marca"].fillna("").tolist()
    sec_cmv = seconds["cmv_seconds_unitario"].fillna(0).tolist() if "cmv_seconds_unitario" in seconds.columns else [0] * len(seconds)

    results = []
    total = len(itens_df)

    for i, (_, row) in enumerate(itens_df.iterrows(), 1):
        if i % 50 == 0 or i == total:
            print(f"    Processando {i}/{total}...")

        item_id = str(row.get("item_id", ""))
        produto_ml = str(row.get("produto", ""))
        marca_ml = str(row.get("marca", "N/D"))
        sku_ml = str(row.get("sku", "N/D"))
        receita = float(row.get("receita_total", 0))
        pedidos = int(row.get("pedidos", 0))
        motivo = str(row.get("motivo_sem_cmv", "SEM_MATCH_SECONDS"))

        norm_produto_ml = normalize(produto_ml)
        norm_sku_ml = normalize_sku(sku_ml if sku_ml not in {"N/D", "nan", ""} else "")

        best_idx = -1
        best_sc = 0.0
        best_method = ""

        for j, (sp, ss) in enumerate(zip(sec_norm_produto, sec_norm_sku)):
            # Método 1: similaridade por produto
            sc_produto = best_score(norm_produto_ml, sp) if norm_produto_ml else 0.0

            # Método 2: SKU exato ou similar
            sc_sku = 0.0
            if norm_sku_ml and ss:
                if norm_sku_ml == ss:
                    sc_sku = 100.0
                else:
                    sc_sku = best_score(norm_sku_ml, ss)

            # Score final = máximo ponderado (SKU tem prioridade)
            if sc_sku >= 90:
                sc_final = sc_sku
            elif sc_sku >= 60:
                sc_final = max(sc_sku * 0.7 + sc_produto * 0.3, sc_produto)
            else:
                sc_final = sc_produto

            if sc_final > best_sc:
                best_sc = sc_final
                best_idx = j
                best_method = "sku" if sc_sku >= sc_produto else "produto"

        if best_idx >= 0:
            candidato_id = sec_item_ids[best_idx]
            candidato_produto = sec_produtos[best_idx]
            candidato_sku = sec_skus[best_idx]
            candidato_marca = sec_marcas[best_idx]
            candidato_cmv = sec_cmv[best_idx]
            padrao_erro = identify_error_pattern(
                produto_ml, candidato_produto, norm_sku_ml, candidato_sku
            )
        else:
            candidato_id = ""
            candidato_produto = ""
            candidato_sku = ""
            candidato_marca = ""
            candidato_cmv = 0.0
            padrao_erro = "sem_candidato"

        score = round(best_sc, 2)
        status = classify_match(score)

        results.append({
            "item_id": item_id,
            "produto_ml": produto_ml,
            "marca_ml": marca_ml,
            "sku_ml": sku_ml,
            "receita": receita,
            "pedidos": pedidos,
            "candidato_seconds_id": candidato_id,
            "candidato_seconds_produto": candidato_produto,
            "candidato_seconds_sku": candidato_sku,
            "candidato_seconds_marca": candidato_marca,
            "candidato_cmv_unitario": candidato_cmv,
            "score_similaridade": score,
            "metodo_match": best_method,
            "status_match_inteligente": status,
            "padrao_erro": padrao_erro,
            "motivo_original": motivo,
        })

    return pd.DataFrame(results)


# ===========================================================================
# ANÁLISE DE PADRÕES DE ERRO
# ===========================================================================

def analyze_error_patterns(df: pd.DataFrame) -> pd.DataFrame:
    padrao_counts = (
        df["padrao_erro"]
        .str.split("; ")
        .explode()
        .value_counts()
        .reset_index()
    )
    padrao_counts.columns = ["padrao", "ocorrencias"]
    return padrao_counts


# ===========================================================================
# IMPACTO FINANCEIRO
# ===========================================================================

def financial_impact(df: pd.DataFrame) -> pd.DataFrame:
    total_receita = df["receita"].sum()
    summary = (
        df.groupby("status_match_inteligente")
        .agg(
            Receita=("receita", "sum"),
            Pedidos=("pedidos", "sum"),
            Itens=("item_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"status_match_inteligente": "Tipo"})
    )
    summary["pct_receita_sem_cmv"] = summary["Receita"] / total_receita * 100 if total_receita else 0
    # Ordenar por prioridade
    order = ["MATCH_AUTOMATICO", "MATCH_PROVAVEL", "MATCH_DUVIDOSO", "SEM_CORRESPONDENCIA"]
    summary["_ord"] = summary["Tipo"].map({v: i for i, v in enumerate(order)}).fillna(9)
    summary = summary.sort_values("_ord").drop(columns="_ord")
    return summary


# ===========================================================================
# COBERTURA POTENCIAL
# ===========================================================================

def coverage_simulation(
    df_match: pd.DataFrame,
    total_receita_sem_cmv: float,
    receita_total: float,
    receita_com_cmv: float,
) -> list[dict]:
    """Simula cobertura se aplicar MATCH_AUTOMATICO e/ou MATCH_PROVAVEL."""
    scenarios = []

    auto_receita = df_match.loc[
        df_match["status_match_inteligente"] == "MATCH_AUTOMATICO", "receita"
    ].sum()
    provavel_receita = df_match.loc[
        df_match["status_match_inteligente"].isin(["MATCH_AUTOMATICO", "MATCH_PROVAVEL"]), "receita"
    ].sum()

    # Cenário 1: apenas MATCH_AUTOMATICO
    nova_cobertura_1 = (receita_com_cmv + auto_receita) / receita_total * 100 if receita_total else 0
    scenarios.append({
        "Cenário": "Aplicar MATCH_AUTOMATICO (score ≥ 90)",
        "Receita recuperada": auto_receita,
        "Nova cobertura CMV (%)": nova_cobertura_1,
        "Receita ainda sem CMV": total_receita_sem_cmv - auto_receita,
    })

    # Cenário 2: MATCH_AUTOMATICO + MATCH_PROVAVEL
    nova_cobertura_2 = (receita_com_cmv + provavel_receita) / receita_total * 100 if receita_total else 0
    scenarios.append({
        "Cenário": "Aplicar MATCH_AUTOMATICO + MATCH_PROVAVEL (score ≥ 75)",
        "Receita recuperada": provavel_receita,
        "Nova cobertura CMV (%)": nova_cobertura_2,
        "Receita ainda sem CMV": total_receita_sem_cmv - provavel_receita,
    })

    return scenarios


# ===========================================================================
# TOP 20 PARA AÇÃO MANUAL
# ===========================================================================

def top20_manual(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sem_corr = (
        df[df["status_match_inteligente"] == "SEM_CORRESPONDENCIA"]
        .nlargest(20, "receita")
        .reset_index(drop=True)
    )
    duvidoso = (
        df[df["status_match_inteligente"] == "MATCH_DUVIDOSO"]
        .nlargest(20, "receita")
        .reset_index(drop=True)
    )
    return sem_corr, duvidoso


# ===========================================================================
# GERAÇÃO DO RELATÓRIO MARKDOWN
# ===========================================================================

def write_report(
    df_match: pd.DataFrame,
    impact: pd.DataFrame,
    coverage: list[dict],
    top20_sem: pd.DataFrame,
    top20_duv: pd.DataFrame,
    error_patterns: pd.DataFrame,
    total_itens_sem_match: int,
    receita_total_sem_match: float,
    receita_total_geral: float,
    receita_com_cmv: float,
    cobertura_atual: float,
    fuzzy_engine: str,
) -> None:

    # Formatações financeiras
    impact_disp = impact.copy()
    impact_disp["Receita"] = impact_disp["Receita"].map(money)
    impact_disp["pct_receita_sem_cmv"] = impact_disp["pct_receita_sem_cmv"].map(percent)

    coverage_disp = pd.DataFrame(coverage)
    coverage_disp["Receita recuperada"] = coverage_disp["Receita recuperada"].map(money)
    coverage_disp["Nova cobertura CMV (%)"] = coverage_disp["Nova cobertura CMV (%)"].map(percent)
    coverage_disp["Receita ainda sem CMV"] = coverage_disp["Receita ainda sem CMV"].map(money)

    def top20_table(df: pd.DataFrame) -> str:
        cols = ["item_id", "produto_ml", "marca_ml", "receita", "pedidos",
                "candidato_seconds_produto", "score_similaridade", "padrao_erro"]
        cols = [c for c in cols if c in df.columns]
        t = df[cols].copy()
        if "receita" in t.columns:
            t["receita"] = t["receita"].map(money)
        return markdown_table(t)

    # Contagem por status
    status_counts = df_match["status_match_inteligente"].value_counts().to_dict()
    n_auto = status_counts.get("MATCH_AUTOMATICO", 0)
    n_prov = status_counts.get("MATCH_PROVAVEL", 0)
    n_duv = status_counts.get("MATCH_DUVIDOSO", 0)
    n_sem = status_counts.get("SEM_CORRESPONDENCIA", 0)

    auto_receita = df_match.loc[df_match["status_match_inteligente"] == "MATCH_AUTOMATICO", "receita"].sum()
    prov_receita = df_match.loc[df_match["status_match_inteligente"] == "MATCH_PROVAVEL", "receita"].sum()
    nova_cobertura_auto = (receita_com_cmv + auto_receita) / receita_total_geral * 100 if receita_total_geral else 0
    nova_cobertura_prov = (receita_com_cmv + auto_receita + prov_receita) / receita_total_geral * 100 if receita_total_geral else 0

    report = f"""# AUDITORIA 4 — CORRESPONDÊNCIA ML × SECONDS (MATCHING INTELIGENTE)

> Gerado automaticamente. Somente leitura — nenhum cálculo financeiro ou base foi alterada.  
> Engine de similaridade: **{fuzzy_engine}**

---

## 1. Resumo Executivo

| Indicador | Valor |
|---|---|
| Total itens SEM_MATCH_SECONDS analisados | **{total_itens_sem_match}** |
| Receita impactada (sem CMV) | **{money(receita_total_sem_match)}** |
| % da receita total sem CMV | **{percent(receita_total_sem_match / receita_total_geral * 100 if receita_total_geral else 0)}** |
| Cobertura CMV atual | **{percent(cobertura_atual)}** |
| MATCH_AUTOMATICO encontrados (score ≥ 90) | **{n_auto}** |
| MATCH_PROVAVEL encontrados (score 75–89) | **{n_prov}** |
| MATCH_DUVIDOSO (score 60–74) | **{n_duv}** |
| SEM_CORRESPONDENCIA (score < 60) | **{n_sem}** |

### Receita Recuperável

| Cenário | Receita | Nova Cobertura CMV |
|---|---|---|
| Aplicar MATCH_AUTOMATICO | **{money(auto_receita)}** | **{percent(nova_cobertura_auto)}** |
| Aplicar + MATCH_PROVAVEL | **{money(auto_receita + prov_receita)}** | **{percent(nova_cobertura_prov)}** |

---

## 2. Impacto Financeiro por Tipo de Match

{markdown_table(impact_disp)}

---

## 3. Ganho Potencial de Cobertura

{markdown_table(coverage_disp)}

---

## 4. Top 20 Itens para Ação Manual — SEM_CORRESPONDENCIA

Estes itens **não encontraram candidato adequado** na base Seconds e precisam de cadastro manual.

{top20_table(top20_sem)}

---

## 5. Top 20 Itens para Revisão — MATCH_DUVIDOSO

Estes itens têm score entre 60–74. Precisam de revisão humana para confirmar ou rejeitar.

{top20_table(top20_duv)}

---

## 6. Padrões de Erro Detectados

{markdown_table(error_patterns.head(15))}

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
- Remover hífens, espaços e pontos antes do merge: `re.sub(r'[\\s\\-\\./]', '', sku.upper())`
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
- {n_auto + n_prov} itens com score ≥ 75 para validação humana rápida (confirmar ou rejeitar candidato)
- Receita potencial: {money(auto_receita + prov_receita)}

### Fase 3 — Cadastro manual (SEM_CORRESPONDENCIA + MATCH_DUVIDOSO)
- {n_sem + n_duv} itens sem candidato adequado
- Priorizar pelos de maior receita (Top 20 listados acima)
- Ação: cadastrar na Seconds ou criar tabela de equivalência

### Objetivo Final
- Cobertura atual: **{percent(cobertura_atual)}**
- Meta após Fase 1+2: **{percent(nova_cobertura_prov)}**
- Meta após Fase 3 (manual): **≥ 98%**

---

## 9. Observações de Controle

- Nenhum arquivo de dados foi alterado por esta auditoria
- `app.py`, `dashboard_base_final.csv` e regras financeiras estão intactos
- Os resultados estão em `resultado/matching_inteligente_seconds.csv`
- Para aplicar as correções, editar `data/parametros_financeiros_seconds.csv` ou criar tabela de equivalência
"""

    OUTPUT_MD.write_text(report, encoding="utf-8")
    print(f"  Relatório: {OUTPUT_MD}")


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    print("=" * 70)
    print("AUDITORIA 4 — MATCHING INTELIGENTE ML × SECONDS")
    print("=" * 70)
    print(f"Engine fuzzy: {FUZZY_ENGINE}")

    print("\n[1/6] Carregando dados...")
    sem_cmv, seconds = load_data()

    # Métricas globais a partir do itens_sem_cmv_completo
    # (que agrega todos os motivos, incluindo SEM_MATCH_SECONDS e outros)
    receita_total_sem_match_seconds = float(
        sem_cmv.loc[sem_cmv["motivo_sem_cmv"] == "SEM_MATCH_SECONDS", "receita_total"].sum()
    )
    receita_total_sem_cmv = float(sem_cmv["receita_total"].sum())

    # Estimar receita total e com CMV a partir do CSV de itens (sem base final completa)
    # Usar como proxy: receita_total_sem_cmv é ~10% => receita_total ~= receita_total_sem_cmv / 0.1071
    # Mas para ser preciso, verificamos se temos a base final
    from pathlib import Path
    base_final_path = BASE_DIR / "data" / "dashboard_base_final.csv"
    if base_final_path.exists():
        print("  Lendo base final para métricas globais...")
        df_final = pd.read_csv(base_final_path, usecols=["receita", "parametro_confiavel", "match_seconds", "cmv_total", "cmv_unitario_seconds"], low_memory=False)
        receita_total_geral = float(df_final["receita"].sum())
        # CMV confiável: match_seconds = True e parametro_confiavel = True e cmv > 0
        mask_ok = (
            df_final["match_seconds"].fillna(False).astype(str).str.lower().isin({"true", "1"}) &
            df_final["parametro_confiavel"].fillna(False).astype(str).str.lower().isin({"true", "1"}) &
            (pd.to_numeric(df_final["cmv_total"], errors="coerce").fillna(0) > 0) &
            (pd.to_numeric(df_final["cmv_unitario_seconds"], errors="coerce").fillna(0) > 0)
        )
        receita_com_cmv = float(df_final.loc[mask_ok, "receita"].sum())
        cobertura_atual = receita_com_cmv / receita_total_geral * 100 if receita_total_geral else 0
    else:
        # Estimativa
        receita_total_geral = receita_total_sem_cmv / 0.1071
        receita_com_cmv = receita_total_geral - receita_total_sem_cmv
        cobertura_atual = receita_com_cmv / receita_total_geral * 100

    print(f"  Receita total geral: R$ {receita_total_geral:,.2f}")
    print(f"  Receita com CMV válido: R$ {receita_com_cmv:,.2f}")
    print(f"  Cobertura CMV atual: {cobertura_atual:.2f}%")
    print(f"  Receita SEM_MATCH_SECONDS: R$ {receita_total_sem_match_seconds:,.2f}")
    print(f"  Base Seconds: {len(seconds)} itens")

    print("\n[2/6] Executando matching inteligente...")
    df_match = run_matching(sem_cmv, seconds)

    print("\n[3/6] Calculando impacto financeiro...")
    impact = financial_impact(df_match)

    print("\n[4/6] Simulando cobertura potencial...")
    coverage = coverage_simulation(
        df_match,
        receita_total_sem_match_seconds,
        receita_total_geral,
        receita_com_cmv,
    )

    print("\n[5/6] Identificando padrões de erro e top itens...")
    error_patterns = analyze_error_patterns(df_match)
    top20_sem, top20_duv = top20_manual(df_match)

    print("\n[6/6] Salvando resultados...")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    df_match.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  CSV: {OUTPUT_CSV}")

    write_report(
        df_match=df_match,
        impact=impact,
        coverage=coverage,
        top20_sem=top20_sem,
        top20_duv=top20_duv,
        error_patterns=error_patterns,
        total_itens_sem_match=len(df_match),
        receita_total_sem_match=receita_total_sem_match_seconds,
        receita_total_geral=receita_total_geral,
        receita_com_cmv=receita_com_cmv,
        cobertura_atual=cobertura_atual,
        fuzzy_engine=FUZZY_ENGINE,
    )

    # Resumo no terminal
    print("\n" + "=" * 70)
    print("RESUMO DO MATCHING INTELIGENTE")
    print("=" * 70)
    for _, row in impact.iterrows():
        print(f"  {row['Tipo']:<25} | Receita: R$ {row['Itens']:>4} itens | {row['pct_receita_sem_cmv']:.1f}% da receita sem CMV")

    print(f"\nCobertura atual:       {cobertura_atual:.2f}%")
    for c in coverage:
        print(f"  {c['Cenário'][:50]}: {c['Nova cobertura CMV (%)']:.2f}%")

    print(f"\nTop padrões de erro:")
    for _, row in error_patterns.head(5).iterrows():
        print(f"  {row['padrao']:<30}: {row['ocorrencias']} ocorrências")

    print(f"\nCSV salvo: {OUTPUT_CSV.name}")
    print(f"Relatório: {OUTPUT_MD.name}")


if __name__ == "__main__":
    main()
