from __future__ import annotations

from datetime import date, timedelta
import html
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import duckdb

# ── Detecção de ambiente ──────────────────────────────────────────────
# No Streamlit Cloud a variável STREAMLIT_SHARING_MODE é injetada.
# Também detectamos pela ausência do venv local.
_IS_CLOUD = (
    os.environ.get("STREAMLIT_SHARING_MODE") == "true"
    or os.environ.get("HOME", "").startswith("/home/appuser")
    or not Path(".venv").exists()
)


DATA_PATH = Path("data/dashboard_base_final.csv")
SECONDS_OFFICIAL_PATH = Path("data/base_seconds_principal.csv")
INVENTORY_PATH = Path("data/ml_items_details.csv")
ADS_METRICS_PATH = Path("data/ml_ads_metrics.csv")
SHIPMENTS_PATH = Path("data/ml_shipments.csv")
UPDATE_SCRIPT_PATH = Path("atualizar_dashboard.py")
LAST_RUN_LOG_PATH = Path("logs/ultima_execucao.log")
DUCKDB_PATH = Path("data/jitparts.duckdb")
APP_TIMEZONE = "America/Sao_Paulo"
FINANCIAL_MODE_OFFICIAL = "Seconds Oficial"
FINANCIAL_MODE_HYBRID = "Estimativa Híbrida ML + Seconds"
SECONDS_OFFICIAL_FALLBACK_PERIOD = (date(2026, 5, 4), date(2026, 5, 8))
META_OPERACIONAL_TOTAL_PERCENTUAL = 5.0
META_OPERACIONAL_ADS_PERCENTUAL = 3.0
META_OPERACIONAL_FULL_PERCENTUAL = 0.5
META_OPERACIONAL_DEVOLUCOES_PERCENTUAL = 0.5
META_OPERACIONAL_OUTRAS_TARIFAS_PERCENTUAL = 0.5
AJUSTE_OPERACIONAL_PADRAO_PERCENTUAL = META_OPERACIONAL_TOTAL_PERCENTUAL
PAPELARIA_EMBALAGENS_PERCENTUAL = 0.5
OTHER_OPERATIONAL_FEE_COLUMNS = [
    "outras_taxas",
    "outras_taxas_operacionais",
    "outras_tarifas",
    "custos_outros_servicos",
    "outros_servicos",
    "taxas_extras",
    "tarifas_operacionais",
    "tarifas_extras",
    "extra_fee",
    "extra_fees",
    "other_fee",
    "other_fees",
    "other_cost",
    "other_costs",
    "extra",
]
RETURN_COST_COLUMNS = [
    "custo_devolucao",
    "tarifa_devolucao",
    "taxa_devolucao",
    "devolucao_custo",
    "devolucao_tarifa",
    "return_cost",
    "return_fee",
    "refund_cost",
    "refund_fee",
    "chargeback_fee",
    "custo_estorno",
    "tarifa_estorno",
]
FRETE_EXTREMA_COLUMNS = [
    "frete_extrema",
    "frete_para_extrema",
    "custo_frete_extrema",
    "shipping_extrema_cost",
]
FRETE_EXTREMA_TEXT_COLUMNS = [
    "shipping_option_name",
    "logistic_type",
    "shipping_mode",
]
DRE_TOOLTIPS = {
    "Receita Bruta": "Total vendido no periodo selecionado.",
    "(-) Comissao ML": "Taxas cobradas pelo Mercado Livre sobre as vendas.",
    "(-) CMV": "Custo das mercadorias vendidas obtido pela Seconds.",
    "(-) Frete": "Custo logistico associado aos pedidos.",
    "(-) Impostos": "Tributos estimados sobre o faturamento.",
    "(-) Rateio Operacional Seconds": "Custos operacionais parametrizados por item na Seconds.",
    "(-) Custos Operacionais Comerciais": (
        "Publicidade, devolucoes, outras tarifas e papelaria. "
        "FULL e mostrado apenas como informativo quando ja incluido no Frete."
    ),
    "Resultado Base": "Margem apos custos diretos da operacao.",
    "Resultado Final da Margem": "Resultado final apos todos os custos comerciais.",
}
COMMERCIAL_COST_TOOLTIPS = {
    "FULL informativo": (
        "Valor monitorado separadamente, mas nao descontado novamente porque ja compoe a linha Frete."
    ),
}
ADS_KPI_TOOLTIPS = {
    "Score Ads": (
        "Definicao: Indicador composto que avalia a eficiencia geral da publicidade considerando retorno, custo, "
        "engajamento, conversao e qualidade da cobertura dos dados.\n"
        "Formula: combinacao ponderada de ROAS, ACOS, CTR, Conversao e Cobertura.\n"
        "Meta: acima de 80.\n"
        "Interpretacao: quanto maior, melhor."
    ),
    "Investimento Ads": (
        "Definicao: Valor investido em publicidade Mercado Livre no periodo.\n"
        "Formula: soma do custo de Ads, com ajuste temporal quando a cobertura e parcial.\n"
        "Meta: monitorar contra 3% da receita total.\n"
        "Interpretacao: deve gerar retorno suficiente para preservar margem."
    ),
    "Receita Atribuida": (
        "Definicao: Receita atribuida pelo Mercado Livre as campanhas.\n"
        "Formula: soma da receita atribuida pela API de Ads.\n"
        "Meta: crescer com ROAS saudavel.\n"
        "Interpretacao: mede o faturamento associado as campanhas."
    ),
    "Receita Ads": (
        "Definicao: Receita atribuida pelo Mercado Livre as campanhas.\n"
        "Formula: soma da receita atribuida pela API de Ads.\n"
        "Meta: crescer com ROAS saudavel.\n"
        "Interpretacao: mede o faturamento associado as campanhas."
    ),
    "Impressoes": (
        "Definicao: quantidade de visualizacoes dos anuncios.\n"
        "Formula: soma de impressoes do periodo.\n"
        "Meta: crescer com CTR qualificado.\n"
        "Interpretacao: mede alcance de midia."
    ),
    "Cliques": (
        "Definicao: quantidade de cliques recebidos pelos anuncios.\n"
        "Formula: soma de cliques do periodo.\n"
        "Meta: crescer sem degradar conversao.\n"
        "Interpretacao: mede trafego gerado por Ads."
    ),
    "Conversoes": (
        "Definicao: vendas/unidades atribuidas aos anuncios.\n"
        "Formula: soma de unidades atribuidas pelo Mercado Livre.\n"
        "Meta: crescer com ROAS saudavel.\n"
        "Interpretacao: mede a transformacao de cliques em venda."
    ),
    "ROAS": (
        "Definicao: ROAS (Return On Ad Spend) mede quanto a empresa recebe em receita para cada R$ 1 investido em publicidade.\n"
        "Formula: Receita Ads / Investimento Ads.\n"
        "Meta: acima de 6.\n"
        "Interpretacao: quanto maior, melhor."
    ),
    "ACOS": (
        "Definicao: ACOS representa o percentual da receita consumido pela publicidade.\n"
        "Formula: Investimento Ads / Receita Ads x 100.\n"
        "Meta: ate 15%.\n"
        "Interpretacao: quanto menor, melhor."
    ),
    "CTR": (
        "Definicao: CTR mede o percentual de pessoas que clicaram no anuncio apos visualiza-lo.\n"
        "Formula: Cliques / Impressoes x 100.\n"
        "Meta: acima de 0,25%.\n"
        "Interpretacao: quanto maior, melhor."
    ),
    "CPC": (
        "Definicao: Custo medio pago por clique recebido nos anuncios.\n"
        "Formula: Investimento Ads / Cliques.\n"
        "Meta: sem meta fixa configurada.\n"
        "Interpretacao: deve ser lido junto com ROAS e Conversao."
    ),
    "Conversao": (
        "Definicao: Conversao mede o percentual de cliques que geraram vendas.\n"
        "Formula: Conversoes / Cliques x 100.\n"
        "Meta: acima de 2,5%.\n"
        "Interpretacao: quanto maior, melhor."
    ),
    "Cobertura dos Dados": (
        "Definicao: Indica quanto dos dados de publicidade foi efetivamente coletado para o periodo selecionado.\n"
        "Formula: dias com dados reais / dias do periodo filtrado x 100.\n"
        "Meta: 100%.\n"
        "Interpretacao: cobertura parcial exige leitura com cautela."
    ),
    "Impacto na Margem": (
        "Definicao: Investimento Ads ajustado dividido pela receita total do periodo.\n"
        "Formula: Investimento Ads / Receita total x 100.\n"
        "Meta: ate 3%.\n"
        "Interpretacao: quanto menor, menor a pressao na margem."
    ),
    "Margem Gerada": (
        "Definicao: leitura executiva da contribuicao direta de Ads antes de custos de produto.\n"
        "Formula: Receita Ads - Investimento Ads.\n"
        "Meta: positiva e crescente.\n"
        "Interpretacao: quanto maior, melhor."
    ),
    "Participacao no Resultado Final": (
        "Definicao: relacao entre a margem gerada por Ads e o resultado final da margem.\n"
        "Formula: Margem gerada / Resultado Final da Margem x 100.\n"
        "Meta: monitoramento executivo.\n"
        "Interpretacao: indica a relevancia de Ads no resultado do periodo."
    ),
}
ADS_SECTION_TOOLTIPS = {
    "Score Ads": (
        "Indicador composto que avalia a eficiencia geral da publicidade considerando retorno, custo, engajamento, "
        "conversao e qualidade da cobertura dos dados."
    ),
    "Resumo Executivo Ads": (
        "Visao consolidada dos principais KPIs de publicidade, metas e sinais de leitura executiva."
    ),
    "Eficiencia de Funil": (
        "Leitura do caminho de midia: impressoes, cliques, conversoes e receita atribuida."
    ),
    "Rentabilidade Ads": (
        "Indicadores de retorno financeiro da publicidade e pressao do investimento sobre a margem."
    ),
    "Alertas de Ads": (
        "Alertas automaticos de criticidade, impacto financeiro e recomendacao de acao."
    ),
    "Evolucao Temporal": (
        "Graficos diarios para acompanhar investimento, receita atribuida, ROAS e ACOS."
    ),
    "Conciliacao com Financeiro Executivo": (
        "Comparacao entre o investimento de Ads desta aba e o valor usado no Financeiro Executivo."
    ),
    "Campanhas": (
        "Ranking operacional das campanhas com investimento, receita, eficiencia e recomendacao."
    ),
    "Quadrante de Campanhas": (
        "Classificacao estrategica das campanhas considerando retorno e volume investido."
    ),
    "Oportunidades de Escala": (
        "Recomendacoes automaticas baseadas na eficiencia financeira das campanhas."
    ),
    "Participacao dos Investimentos": (
        "Distribuicao do orcamento publicitario entre as campanhas."
    ),
    "Impacto dos Ads na Margem": (
        "Demonstra a contribuicao da publicidade para o resultado financeiro do periodo."
    ),
    "Radar de Oportunidades": (
        "Resumo automatico dos principais pontos de melhoria e oportunidades encontrados na operacao publicitaria."
    ),
    "Conversao por Campanha": (
        "Formula: Unidades vendidas / Cliques x 100. "
        "Mede a eficiencia do trafego pago em gerar vendas. "
        "Meta: acima de 2,5%. "
        "Interpretacao: conversao baixa indica problema de segmentacao, criativos ou oferta. "
        "Acao: revisar campanhas com muitos cliques e poucas vendas."
    ),
    "Qualidade do Trafego": (
        "Matriz 2x2 que cruza volume de cliques (eixo X) com taxa de conversao (eixo Y). "
        "Limiares calculados pelas medianas do periodo filtrado. "
        "Escalar: alto trafego + alta conversao — aumentar orcamento. "
        "Oportunidade: baixo trafego + alta conversao — escalar com cautela. "
        "Trafego Ruim: alto trafego + baixa conversao — revisar criativos e segmentacao. "
        "Revisar: baixo trafego + baixa conversao — avaliar pausa."
    ),
    "Tendencia de Conversao": (
        "Formula: Conversao diaria = Unidades vendidas / Cliques x 100. "
        "MM7 (linha azul): media dos ultimos 7 dias — tendencia de curto prazo. "
        "MM30 (linha laranja pontilhada): media dos ultimos 30 dias — referencia de medio prazo. "
        "Meta: acima de 2,5%. "
        "Interpretacao: MM7 acima da MM30 indica melhora de eficiencia; abaixo indica queda. "
        "Acao: revisar criativos, segmentacao e oferta quando MM7 cair mais de 10% abaixo da MM30."
    ),
    "Tendencia de Trafego (Cliques Diarios)": (
        "Grafico de barras diarias de cliques com duas medias moveis sobrepostas. "
        "MM7 (linha azul): media dos ultimos 7 dias — tendencia de curto prazo. "
        "MM30 (linha laranja pontilhada): media dos ultimos 30 dias — tendencia de medio prazo. "
        "Interpretacao: MM7 acima da MM30 indica aceleracao de trafego; abaixo indica queda. "
        "Acao: investigar causa quando MM7 cair mais de 10% abaixo da MM30."
    ),
    "Conciliacao com Financeiro Executivo": (
        "Comparacao entre o investimento de Ads desta aba e o valor usado no Financeiro Executivo."
    ),
    "Evolucao Temporal": (
        "Graficos diarios de investimento, receita atribuida, ROAS e ACOS. "
        "Permite identificar dias com pico de gasto, queda de retorno ou oscilacoes de eficiencia."
    ),
    "Score Ads": ADS_KPI_TOOLTIPS.get("Score Ads", ""),
    "Resumo Executivo Ads": (
        "Visao consolidada dos principais KPIs de publicidade, metas e sinais de leitura executiva."
    ),
    "Eficiencia de Funil": (
        "Leitura do caminho de midia: impressoes > cliques > conversoes > receita atribuida. "
        "Formula: CTR = Cliques / Impressoes. Conversao = Unidades / Cliques. "
        "Interpretacao: gargalos em cada etapa indicam onde otimizar."
    ),
    "Rentabilidade Ads": (
        "ROAS = Receita atribuida / Investimento. Meta: acima de 6. "
        "ACOS = Investimento / Receita x 100. Meta: abaixo de 15%. "
        "Impacto na Margem = Investimento / Receita total x 100. Meta: abaixo de 3%."
    ),
    "Impacto dos Ads na Margem": (
        "Demonstra a contribuicao da publicidade para o resultado financeiro do periodo. "
        "Margem gerada = Receita atribuida - Investimento. "
        "Participacao no resultado = Margem gerada / Resultado final da margem x 100."
    ),
    "Radar de Oportunidades": (
        "Resumo automatico dos principais pontos de melhoria e oportunidades encontrados na operacao publicitaria."
    ),
    "Quadrante de Campanhas": (
        "Classificacao estrategica das campanhas considerando retorno (ROAS) e volume investido. "
        "Eixo X = ROAS; Eixo Y = Investimento. Tamanho do ponto proporcional a receita. "
        "Escalar: ROAS >= 6 e alto investimento. Oportunidade: ROAS >= 6 e baixo investimento. "
        "Revisar: ROAS < 3 e alto investimento."
    ),
    "Oportunidades de Escala": (
        "Recomendacoes automaticas baseadas na eficiencia financeira das campanhas. "
        "Aumentar investimento: ROAS > 10 e ACOS < 10%. Manter: ROAS entre 6 e 10. Revisar: ROAS < 3."
    ),
    "Participacao dos Investimentos": (
        "Distribuicao percentual do orcamento publicitario entre as campanhas do periodo. "
        "Permite identificar concentracao de verba e campanhas sem investimento relevante."
    ),
    "Alertas de Ads": (
        "Alertas automaticos gerados por regras de criticidade sobre ROAS, ACOS, cobertura e conversao. "
        "Criticidade Alta: acao imediata. Media: acompanhar. Oportunidade: escalar."
    ),
    "Campanhas": (
        "Ranking operacional das campanhas com investimento, receita, ROAS, ACOS, CTR, CPC e recomendacao de acao."
    ),
    "Conversao ML Ajustada vs Ads": (
        "Conversao ML Ajustada = Conversao Ads + Fator de Ajuste. "
        "Fator = Conversao ML real (painel ML) - media Conversao Ads do periodo. "
        "Se nenhum valor ML for informado, a linha ML coincide com a linha Ads. "
        "Linhas: Branco/destaque = Conv. ML MM7 (principal) | Azul = Conv. Ads MM7 | "
        "Pontilhado = MM30 | Tracejado = meta ou valor ML informado."
    ),
    "Top Produtos — Trafego e Conversao Estimados": (
        "Visitas por produto sao estimadas distribuindo os cliques diarios de Ads "
        "proporcionalmente a participacao de cada produto nas vendas do dia. "
        "Formula: visitas_sku = (units_sku / units_total_dia) x clicks_dia. "
        "Conversao = unidades vendidas / visitas estimadas. "
        "Requer sobreposicao de datas entre vendas e dados de Ads."
    ),
}
COLORWAY = ["#0F766E", "#2563EB", "#D97706", "#DC2626", "#7C3AED", "#0891B2", "#111827"]
DATE_AXIS_FORMAT = "%Y-%m-%d"
CRESCIMENTO_META_VERDE = 18.0
CRESCIMENTO_META_AMARELO = 15.0
TOP_MARCAS_HEATMAP_EXECUTIVO = 15
TOP_MARCAS_PARTICIPACAO_TENDENCIA = 10
MONTH_NAMES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}
MONTH_ABBR_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}
MONEY_COLUMNS = [
    "receita",
    "faturamento_ultimos_7d",
    "faturamento_30d_anteriores",
    "media_diaria_7d",
    "media_diaria_30d",
    "impacto_faturamento_perdido",
    "impacto_perdido",
    "sale_fee",
    "Comissão",
    "CMV total",
    "imposto",
    "custo_fixo",
    "extra",
    "lucro_bruto",
    "lucro_operacional",
    "lucro_liquido_estimado",
    "faturamento",
    "impacto_financeiro",
    "cost",
    "revenue",
    "cost_ads",
    "lucro_pos_ads",
    "Lucro Bruto",
    "Lucro Liquido Seconds",
]
PERCENT_COLUMNS = [
    "Margem Seconds",
    "margem calculada",
    "margem_bruta",
    "margem_operacional",
    "margem_operacional_pct",
    "margem",
    "margem_base",
    "margem_liquida_estimada",
    "ctr",
    "acos",
    "conversion_rate",
    "margem_pos_ads",
    "impacto_comercial_total_pct",
    "resultado_operacional_pct",
    "ads_pct",
    "ajuste_operacional_padrao_pct",
    "full_pct",
    "full_pct_considerado",
    "devolucao_pct",
    "devolucao_pct_considerado",
    "devolucao_valor_venda_monitorado_pct",
    "outras_taxas_pct",
    "queda_percentual",
]

KPI_EXPLANATIONS = {
    "faturamento": {
        "titulo": "Faturamento",
        "descricao": "Receita bruta consolidada dos pedidos no periodo filtrado.",
        "formula": {
            FINANCIAL_MODE_OFFICIAL: "Soma da receita oficial exportada pela Seconds.",
            FINANCIAL_MODE_HYBRID: "Soma da receita dos pedidos do Mercado Livre enriquecidos com parametros Seconds.",
        },
        "interpretacao": "Mostra o tamanho da venda. Deve ser lido junto com margem e lucro para evitar crescimento sem rentabilidade.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "lucro_liquido_estimado": {
        "titulo": "Lucro liquido interno",
        "descricao": "Resultado financeiro auxiliar mantido para analises detalhadas, nao usado como KPI executivo principal.",
        "formula": {
            FINANCIAL_MODE_OFFICIAL: "Soma do resultado liquido da fonte financeira selecionada.",
            FINANCIAL_MODE_HYBRID: "Receita ML - CMV Seconds - frete ML - comissao ML - impostos - custos fixos - extras.",
        },
        "interpretacao": "Use como apoio analitico; a leitura diretiva principal deve priorizar resultado operacional consolidado.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "margem_liquida": {
        "titulo": "Margem liquida",
        "descricao": "Percentual do faturamento que vira lucro liquido.",
        "formula": "Lucro liquido / Faturamento x 100.",
        "interpretacao": "Resume a eficiencia economica da venda. Quanto maior, mais folga para Ads, descontos e variacoes de custo.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "lucro_operacional": {
        "titulo": "Lucro operacional",
        "descricao": "Resultado operacional usado no modo financeiro selecionado.",
        "formula": {
            FINANCIAL_MODE_OFFICIAL: "Soma do resultado operacional da fonte financeira selecionada.",
            FINANCIAL_MODE_HYBRID: "Soma do lucro operacional calculado na base ML + Seconds.",
        },
        "interpretacao": "Ajuda a entender o resultado da operacao antes das leituras especificas de Ads e alertas.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "margem_operacional": {
        "titulo": "Margem Base",
        "descricao": "Margem base antes dos custos comerciais reais.",
        "formula": "(Receita - CMV - comissao ML - frete - impostos estimados - custos fixos operacionais) / Receita x 100.",
        "interpretacao": "Mostra a rentabilidade operacional de partida para a formula usada pela diretoria.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "impacto_comercial": {
        "titulo": "Custos Operacionais Comerciais",
        "descricao": "Somatoria dos custos comerciais usados pela diretoria.",
        "formula": "Publicidade + FULL + Devolucoes + Outras Tarifas + Frete Extrema + Papelaria.",
        "interpretacao": "Mostra quanto da receita foi consumido pelas alavancas comerciais e operacionais do Mercado Livre.",
        "fonte": "Hibrido: Mercado Livre, Seconds e Mercado Ads.",
    },
    "resultado_operacional_consolidado": {
        "titulo": "Resultado Final da Margem",
        "descricao": "Resultado base depois dos custos operacionais comerciais definidos pela diretoria.",
        "formula": "Resultado Base - Publicidade - FULL - Devolucoes - Outras Tarifas - Frete Extrema - Papelaria.",
        "interpretacao": "Mostra a margem final do periodo apos os custos comerciais; verde acima de 12%, amarelo entre 7% e 12%, vermelho abaixo de 7%.",
        "fonte": "Modelo executivo da diretoria.",
    },
    "investimento_ads": {
        "titulo": "Investimento Ads",
        "descricao": "Valor investido em Mercado Ads no periodo filtrado.",
        "formula": "Soma do custo de Ads filtrado pelo periodo global.",
        "interpretacao": "Deve ser lido junto com ROAS, ACOS e resultado operacional consolidado.",
        "fonte": "Mercado Ads.",
    },
    "custos_extras_operacionais": {
        "titulo": "Custos extras operacionais",
        "descricao": "Custos comerciais reais fora dos custos base, sem dupla contagem de frete.",
        "formula": "Outras taxas operacionais + tarifas reais de devolucao, quando disponiveis.",
        "interpretacao": "FULL e devolucoes medidas por valor de venda sao exibidos como monitoramento, nao como custo incremental.",
        "fonte": "Hibrido: Mercado Livre + Seconds.",
    },
    "cmv": {
        "titulo": "CMV",
        "descricao": "Custo das mercadorias vendidas no periodo.",
        "formula": "Soma do CMV dos itens vendidos.",
        "interpretacao": "E um dos maiores direcionadores de margem. CMV alto pressiona lucro e pode indicar necessidade de revisar custo ou preco.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Seconds, aplicado aos pedidos do Mercado Livre.",
        },
    },
    "frete": {
        "titulo": "Frete",
        "descricao": "Custo de frete atribuido aos pedidos do periodo.",
        "formula": "Soma do custo de frete final dos pedidos.",
        "interpretacao": "Frete elevado reduz margem e pode sinalizar produtos, regioes ou modalidades logisticas pouco rentaveis.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Mercado Livre, com fallback consolidado na base financeira.",
        },
    },
    "impostos": {
        "titulo": "Impostos",
        "descricao": "Total de impostos estimados ou oficiais associados as vendas.",
        "formula": "Soma da coluna de imposto no periodo filtrado.",
        "interpretacao": "Ajuda a separar perda de margem estrutural de perda causada por preco, frete ou CMV.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Parametros Seconds aplicados aos pedidos Mercado Livre.",
        },
    },
    "margem_pos_ads": {
        "titulo": "Margem pos Ads",
        "descricao": "Margem depois de descontar o investimento em Mercado Ads do lucro liquido.",
        "formula": "(Lucro liquido - investimento Ads) / Faturamento x 100.",
        "interpretacao": "Mostra se a venda continua rentavel apos midia. Margem baixa pede revisao de campanhas, precos ou mix.",
        "fonte": "Hibrido: financeiro selecionado + Mercado Ads.",
    },
    "roas": {
        "titulo": "ROAS",
        "descricao": "Receita gerada para cada real investido em Ads.",
        "formula": "Receita atribuida Ads / Investimento Ads.",
        "interpretacao": "Quanto maior, melhor a eficiencia da midia. ROAS baixo indica campanha com pouco retorno comercial.",
        "fonte": "Mercado Ads.",
    },
    "acos": {
        "titulo": "ACOS",
        "descricao": "Percentual da receita atribuida que foi consumido por Ads.",
        "formula": "Investimento Ads / Receita atribuida Ads x 100.",
        "interpretacao": "Quanto menor, mais eficiente a campanha. ACOS alto pode consumir a margem do produto.",
        "fonte": "Mercado Ads.",
    },
    "ticket_medio": {
        "titulo": "Ticket medio",
        "descricao": "Valor medio vendido por pedido no periodo.",
        "formula": "Faturamento / Numero de pedidos.",
        "interpretacao": "Ajuda a avaliar mix, bundles e potencial de aumento de valor por compra.",
        "fonte": {
            FINANCIAL_MODE_OFFICIAL: "Seconds Oficial",
            FINANCIAL_MODE_HYBRID: "Hibrido: Mercado Livre + Seconds",
        },
    },
    "impacto_financeiro": {
        "titulo": "Impacto financeiro",
        "descricao": "Estimativa do valor financeiro exposto pelos alertas priorizados.",
        "formula": "Soma do impacto financeiro estimado dos alertas filtrados.",
        "interpretacao": "Prioriza onde agir primeiro. Quanto maior o impacto, maior o potencial de perda ou recuperacao.",
        "fonte": "Hibrido: regras executivas sobre vendas ML, Seconds, estoque e Ads.",
    },
    "alertas_alta_prioridade": {
        "titulo": "Alertas alta prioridade",
        "descricao": "Quantidade de alertas classificados como alta prioridade.",
        "formula": "Contagem de alertas com prioridade = Alta.",
        "interpretacao": "Mostra o volume de riscos que exigem acao imediata.",
        "fonte": "Hibrido: vendas ML, financeiro Seconds, estoque e Mercado Ads.",
    },
    "acoes_para_hoje": {
        "titulo": "Acoes para hoje",
        "descricao": "Quantidade de alertas com prazo sugerido para hoje.",
        "formula": "Contagem de alertas com prazo_sugerido = Hoje.",
        "interpretacao": "Traduz os riscos em fila operacional diaria para reduzir perdas rapidamente.",
        "fonte": "Hibrido: motor de alertas executivo.",
    },
}

KPI_EXPLANATION_ALIASES = {
    "faturamento": "faturamento",
    "lucro liquido estimado": "lucro_liquido_estimado",
    "margem liquida oficial": "margem_liquida",
    "margem liquida estimada": "margem_liquida",
    "margem liquida": "margem_liquida",
    "lucro oficial": "lucro_operacional",
    "lucro operacional": "lucro_operacional",
    "margem oficial": "margem_operacional",
    "margem operacional": "margem_operacional",
    "margem base": "margem_operacional",
    "impacto comercial": "impacto_comercial",
    "custos comerciais reais": "impacto_comercial",
    "resultado operacional consolidado": "resultado_operacional_consolidado",
    "resultado final da margem": "resultado_operacional_consolidado",
    "investimento ads": "investimento_ads",
    "investimento total ads": "investimento_ads",
    "custos extras operacionais": "custos_extras_operacionais",
    "cmv": "cmv",
    "cmv total": "cmv",
    "frete": "frete",
    "frete total": "frete",
    "impostos": "impostos",
    "margem pos ads": "margem_pos_ads",
    "margem pós ads": "margem_pos_ads",
    "roas": "roas",
    "roas medio": "roas",
    "roas médio": "roas",
    "acos": "acos",
    "acos medio": "acos",
    "acos médio": "acos",
    "ticket medio": "ticket_medio",
    "ticket médio": "ticket_medio",
    "impacto financeiro estimado": "impacto_financeiro",
    "impacto financeiro total estimado": "impacto_financeiro",
    "impacto financeiro pendente": "impacto_financeiro",
    "alertas alta prioridade": "alertas_alta_prioridade",
    "acoes para hoje": "acoes_para_hoje",
    "ações para hoje": "acoes_para_hoje",
}


st.set_page_config(
    page_title="Jit Parts Ecommerce BI",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    """Aplica identidade visual executiva ao Streamlit."""

    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1500px;
                padding-top: 1.25rem;
                padding-bottom: 2rem;
            }
            [data-testid="stSidebar"] {
                border-right: 1px solid rgba(128,128,128,.18);
            }
            .app-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                gap: 1rem;
                padding-bottom: 1rem;
                margin-bottom: 1rem;
                border-bottom: 1px solid rgba(128,128,128,.18);
            }
            .app-title {
                font-size: clamp(1.5rem, 2.4vw, 2.35rem);
                font-weight: 850;
                line-height: 1.05;
                margin: 0;
                letter-spacing: 0;
            }
            .app-subtitle {
                color: rgba(125,125,125,.95);
                margin-top: .35rem;
                font-size: .95rem;
            }
            .app-badge {
                border: 1px solid rgba(128,128,128,.24);
                border-radius: 999px;
                padding: .42rem .78rem;
                font-size: .78rem;
                font-weight: 750;
                white-space: nowrap;
            }
            .kpi-card {
                border: 1px solid rgba(128,128,128,.17);
                border-radius: 8px;
                padding: .95rem;
                min-height: 112px;
                background: color-mix(in srgb, var(--background-color) 93%, #0F766E 7%);
                box-shadow: 0 10px 26px rgba(15,23,42,.045);
            }
            .kpi-label {
                font-size: .74rem;
                text-transform: uppercase;
                color: rgba(125,125,125,.96);
                font-weight: 800;
                margin-bottom: .45rem;
                position: relative;
            }
            .kpi-help {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1rem;
                height: 1rem;
                margin-left: .28rem;
                border-radius: 999px;
                border: 1px solid rgba(125,125,125,.35);
                font-size: .66rem;
                line-height: 1;
                cursor: help;
                text-transform: none;
                color: rgba(125,125,125,.96);
            }
            .kpi-tooltip {
                position: relative;
                display: inline-flex;
                align-items: center;
            }
            .kpi-value {
                font-size: clamp(1.15rem, 1.8vw, 1.68rem);
                font-weight: 850;
                line-height: 1.1;
                word-break: break-word;
            }
            .section-title {
                font-size: 1.05rem;
                font-weight: 820;
                margin: .2rem 0 .6rem 0;
            }
            .action-summary {
                border: 1px solid rgba(128,128,128,.18);
                border-left: 4px solid #2563EB;
                border-radius: 8px;
                padding: .95rem 1rem;
                margin: .4rem 0 1rem 0;
                background: color-mix(in srgb, var(--background-color) 91%, #2563EB 9%);
            }
            .action-summary-title {
                font-size: .78rem;
                text-transform: uppercase;
                color: rgba(125,125,125,.96);
                font-weight: 850;
                margin-bottom: .28rem;
            }
            .action-summary-text {
                font-size: 1rem;
                line-height: 1.45;
                font-weight: 650;
            }
            .priority-card {
                border: 1px solid rgba(128,128,128,.18);
                border-left: 5px solid var(--priority-color);
                border-radius: 8px;
                padding: .95rem;
                min-height: 132px;
                background: color-mix(in srgb, var(--background-color) 90%, var(--priority-color) 10%);
                box-shadow: 0 10px 26px rgba(15,23,42,.045);
            }
            .priority-card-title {
                font-size: .82rem;
                font-weight: 850;
                text-transform: uppercase;
                margin-bottom: .5rem;
            }
            .priority-card-count {
                font-size: clamp(1.35rem, 2vw, 1.85rem);
                line-height: 1;
                font-weight: 900;
                margin-bottom: .35rem;
            }
            .priority-card-meta {
                color: rgba(125,125,125,.98);
                font-size: .82rem;
                line-height: 1.35;
                font-weight: 700;
            }
            .action-card {
                border: 1px solid rgba(128,128,128,.18);
                border-left: 5px solid var(--priority-color);
                border-radius: 8px;
                padding: 1rem;
                min-height: 250px;
                background: color-mix(in srgb, var(--background-color) 92%, var(--priority-color) 8%);
                box-shadow: 0 10px 26px rgba(15,23,42,.05);
                margin-bottom: .8rem;
            }
            .action-card-header {
                display: flex;
                justify-content: space-between;
                gap: .8rem;
                align-items: center;
                margin-bottom: .65rem;
            }
            .action-card-priority {
                font-size: .77rem;
                font-weight: 900;
                letter-spacing: 0;
                text-transform: uppercase;
                color: var(--priority-color);
            }
            .action-card-category {
                font-size: .74rem;
                font-weight: 800;
                color: rgba(125,125,125,.98);
                text-transform: uppercase;
                white-space: nowrap;
            }
            .action-card-product {
                font-size: 1rem;
                line-height: 1.25;
                font-weight: 850;
                margin-bottom: .55rem;
            }
            .action-card-line {
                color: rgba(125,125,125,.98);
                font-size: .86rem;
                line-height: 1.38;
                margin: .32rem 0;
            }
            .action-card-line strong {
                color: color-mix(in srgb, currentColor 70%, var(--text-color) 30%);
                font-weight: 850;
            }
            .action-card-impact {
                font-size: .98rem;
                font-weight: 900;
                color: var(--priority-color);
                margin: .45rem 0;
            }
            .action-card-metrics {
                margin-top: .65rem;
                padding-top: .6rem;
                border-top: 1px solid rgba(128,128,128,.16);
                color: rgba(125,125,125,.98);
                font-size: .82rem;
                line-height: 1.35;
                font-weight: 750;
            }
            @media (max-width: 768px) {
                .app-header { display: block; }
                .app-badge { display: inline-block; margin-top: .75rem; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def br_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_percent(value: float | int | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):.{decimals}f}%".replace(".", ",")


def safe_bool(value: object, default: bool = False) -> bool:
    """Converte valores escalares para bool sem quebrar com pd.NA."""

    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "nan", "none", "nat", "<na>", "n/d"}:
            return default
        if normalized in {"1", "true", "sim", "yes", "y"}:
            return True
        if normalized in {"0", "false", "nao", "não", "no", "n"}:
            return False
    return bool(value)


def safe_text(value: object, default: str = "N/D") -> str:
    """Converte valores escalares para texto seguro."""

    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "nan", "none", "nat", "<na>"} else text


def safe_number(value: object, default: float = 0.0) -> float:
    """Converte valores escalares para float sem avaliar pd.NA como booleano."""

    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        parsed = pd.to_numeric(value, errors="coerce")
        return default if pd.isna(parsed) else float(parsed)


def safe_debug_value(value: object) -> str:
    """Representa valores de debug sem quebrar o console Windows."""

    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")


def normalize_kpi_label(label: str) -> str:
    """Normaliza o titulo exibido para buscar explicacoes por alias."""

    normalized = unicodedata.normalize("NFKD", label)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(normalized.casefold().strip().split())


def explanation_value(value: object, financial_mode: str) -> str:
    """Resolve campos da explicacao que mudam pelo modo financeiro."""

    if isinstance(value, dict):
        selected = value.get(financial_mode)
        if selected is None:
            selected = value.get(FINANCIAL_MODE_HYBRID) or value.get(FINANCIAL_MODE_OFFICIAL)
        if selected is None and value:
            selected = next(iter(value.values()))
        return str(selected or "")
    return str(value or "")


def get_kpi_explanation(
    label: str,
    financial_mode: str = FINANCIAL_MODE_HYBRID,
    explanation_key: str | None = None,
) -> dict[str, str] | None:
    """Retorna a explicacao executiva do KPI exibido no card."""

    key = explanation_key or KPI_EXPLANATION_ALIASES.get(normalize_kpi_label(label))
    if not key:
        return None

    explanation = KPI_EXPLANATIONS.get(key)
    if not explanation:
        return None

    return {
        "titulo": explanation_value(explanation.get("titulo"), financial_mode),
        "descricao": explanation_value(explanation.get("descricao"), financial_mode),
        "formula": explanation_value(explanation.get("formula"), financial_mode),
        "interpretacao": explanation_value(explanation.get("interpretacao"), financial_mode),
        "fonte": explanation_value(explanation.get("fonte"), financial_mode),
    }


def render_kpi_label(label: str, explanation: dict[str, str] | None) -> str:
    """Monta o titulo do card com tooltip quando houver explicacao."""

    label_html = html.escape(label)
    if not explanation:
        return label_html

    title = (
        f'Descricao: {explanation["descricao"]}\n'
        f'Formula: {explanation["formula"]}\n'
        f'Interpretacao: {explanation["interpretacao"]}\n'
        f'Fonte: {explanation["fonte"]}'
    )
    title_html = html.escape(title, quote=True)
    return (
        f'<span class="kpi-tooltip" title="{title_html}">'
        f"{label_html}"
        f'<span class="kpi-help" title="{title_html}" aria-label="Explicacao do KPI">&#8505;</span>'
        f"</span>"
    )


def kpi_card(
    label: str,
    value: str,
    financial_mode: str = FINANCIAL_MODE_HYBRID,
    explanation_key: str | None = None,
) -> None:
    explanation = get_kpi_explanation(label, financial_mode, explanation_key)
    label_html = render_kpi_label(label, explanation)
    value_html = html.escape(value)
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label_html}</div>
            <div class="kpi-value">{value_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_status_card(
    label: str,
    value: str,
    status: str,
    financial_mode: str = FINANCIAL_MODE_HYBRID,
    explanation_key: str | None = None,
) -> None:
    """Renderiza KPI com semaforo executivo."""

    colors = {
        "saudavel": "#0F766E",
        "atencao": "#D97706",
        "risco": "#DC2626",
    }
    color = colors.get(status, "#64748B")
    explanation = get_kpi_explanation(label, financial_mode, explanation_key)
    label_html = render_kpi_label(label, explanation)
    value_html = html.escape(value)
    st.markdown(
        f"""
        <div class="kpi-card" style="border-top: 4px solid {color};">
            <div class="kpi-label">{label_html}</div>
            <div class="kpi-value">{value_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Converte colunas numericas sem quebrar quando alguma estiver ausente."""

    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def ensure_columns(df: pd.DataFrame, defaults: dict[str, object]) -> pd.DataFrame:
    """Garante colunas esperadas com defaults seguros."""

    df = df.copy()
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
    return df


def ensure_compat_column(
    df: pd.DataFrame,
    target: str,
    sources: Iterable[str],
    default: object = pd.NA,
) -> pd.DataFrame:
    """Cria/preenche uma coluna a partir do primeiro alias disponivel."""

    df = df.copy()
    target_existed = target in df.columns
    if target not in df.columns:
        df[target] = pd.NA

    target_series = df[target]
    for source in sources:
        if source not in df.columns or source == target:
            continue

        target_text = target_series.astype("string").str.strip().str.lower()
        missing = target_series.isna() | target_text.isin(["", "nan", "none", "nat", "<na>", "n/d"])
        target_series = target_series.where(~missing, df[source])

    if not target_existed or sources:
        target_series = target_series.fillna(default)
    df[target] = target_series
    return df


def apply_seconds_column_compatibility(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza aliases antigos do app para a nova base financeira Seconds."""

    df = df.copy()

    canonical_aliases = {
        "cmv_seconds": ["CMV total", "CMV unitario", "CMV unitário", "CMV unit�rio", "CMV unitÃ¡rio"],
        "lucro_liquido_seconds": ["lucro_liquido_estimado", "Lucro Liquido Seconds", "Lucro unitario", "Lucro unitário"],
        "faturamento_seconds": ["receita", "faturamento"],
        "margem_seconds": ["margem_liquida_estimada", "Margem Seconds", "margem calculada"],
        "preco_venda_seconds": ["unit_price", "Preço unitario", "Preco unitario", "Preço unitário", "Preco unitário"],
        "comissao_seconds": ["sale_fee", "Comissão", "ComissÃ£o"],
        "frete_seconds": ["custo_frete_final", "custo_frete"],
        "imposto_seconds": ["imposto"],
        "custo_fixo_seconds": ["custo_fixo"],
        "lucro_bruto_seconds": ["lucro_bruto", "Lucro Bruto"],
    }
    for target, sources in canonical_aliases.items():
        df = ensure_compat_column(df, target, sources, default=0)

    legacy_aliases = {
        "receita": ["faturamento_seconds"],
        "faturamento": ["faturamento_seconds"],
        "unit_price": ["preco_venda_seconds"],
        "Preço unitario": ["preco_venda_seconds"],
        "Preco unitario": ["preco_venda_seconds"],
        "Preço unitário": ["preco_venda_seconds"],
        "Preco unitário": ["preco_venda_seconds"],
        "sale_fee": ["comissao_seconds"],
        "Comissão": ["comissao_seconds"],
        "ComissÃ£o": ["comissao_seconds"],
        "custo_frete_final": ["frete_seconds"],
        "custo_frete": ["frete_seconds"],
        "CMV total": ["cmv_seconds"],
        "CMV unitario": ["cmv_seconds"],
        "CMV unitário": ["cmv_seconds"],
        "CMV unit�rio": ["cmv_seconds"],
        "CMV unitÃ¡rio": ["cmv_seconds"],
        "imposto": ["imposto_seconds"],
        "custo_fixo": ["custo_fixo_seconds"],
        "lucro_bruto": ["lucro_bruto_seconds"],
        "Lucro Bruto": ["lucro_bruto_seconds"],
        "lucro_liquido_estimado": ["lucro_liquido_seconds"],
        "Lucro Liquido Seconds": ["lucro_liquido_seconds"],
        "Lucro unitario": ["lucro_liquido_seconds"],
        "Lucro unitário": ["lucro_liquido_seconds"],
        "margem_liquida_estimada": ["margem_seconds"],
        "Margem Seconds": ["margem_seconds"],
        "margem calculada": ["margem_seconds"],
        "lucro_operacional": ["lucro_bruto_seconds"],
        "extra": [],
    }
    for target, sources in legacy_aliases.items():
        df = ensure_compat_column(df, target, sources, default=0)

    return df


def last_update_label(path: Path) -> str:
    """Retorna o horario mais recente encontrado no log da rotina diaria."""

    if not path.exists():
        return "Ultima atualizacao: N/D"

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "Ultima atualizacao: N/D"

    for line in reversed(lines):
        if line.startswith("[") and "]" in line:
            return f"Ultima atualizacao: {line[1:20]}"
    return "Ultima atualizacao: N/D"


def run_dashboard_update() -> subprocess.CompletedProcess[str]:
    """Executa a rotina manual de atualizacao do dashboard."""

    return subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT_PATH)],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@st.cache_data(show_spinner="Carregando base executiva...")
def load_data(path: str) -> pd.DataFrame:
    """Carrega e prepara a base final do dashboard."""

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {csv_path}. "
            "No Streamlit Cloud, faca upload dos dados CSV para a pasta data/ do repositorio."
        )

    df = pd.read_csv(csv_path, low_memory=False)
    df = apply_seconds_column_compatibility(df)
    df = safe_numeric(
        df,
        [
            "quantity",
            "unit_price",
            "receita",
            "sale_fee",
            "Comissão",
            "CMV unitário",
            "CMV total",
            "cmv_total",
            "frete_total",
            "imposto_total",
            "custo_fixo_total",
            "comissao_total",
            "imposto",
            "custo_fixo",
            "extra",
            "lucro_bruto",
            "lucro_operacional",
            "lucro_liquido_estimado",
            "margem_bruta",
            "margem_operacional",
            "margem_liquida_estimada",
            "Lucro Bruto",
            "Lucro Liquido Seconds",
            "Margem Seconds",
            "margem calculada",
        ],
    )
    df = safe_numeric(
        df,
        [
            "faturamento",
            "faturamento_seconds",
            "preco_venda_seconds",
            "comissao_seconds",
            "Comissão",
            "CMV unitario",
            "CMV unitário",
            "CMV unit�rio",
            "cmv_seconds",
            "imposto_seconds",
            "custo_fixo_seconds",
            "frete_seconds",
            "lucro_bruto_seconds",
            "lucro_liquido_seconds",
            "margem_seconds",
            "Preço unitario",
            "Preco unitario",
            "Preço unitário",
            "Preco unitário",
            "Lucro unitario",
            "Lucro unitário",
        ],
    )

    df["date_created"] = pd.to_datetime(df.get("date_created"), errors="coerce", utc=True).dt.tz_convert(APP_TIMEZONE)
    df["data_ref"] = df["date_created"].dt.date
    df["date"] = df["data_ref"]
    df["month"] = df["date_created"].dt.tz_localize(None).dt.to_period("M").astype(str)
    df["weekday"] = df["date_created"].dt.day_name()
    df["hour"] = df["date_created"].dt.hour
    df["order_id"] = df.get("order_id", pd.Series(index=df.index, dtype="object")).astype(str)
    df["item_id"] = df.get("item_id", pd.Series(index=df.index, dtype="object")).astype(str)
    df["SKU"] = df.get("SKU", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["produto"] = df.get("produto", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["Marca"] = df.get("Marca", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["Nome da Categoria"] = df.get("Nome da Categoria", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["FULL"] = df.get("FULL", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["Flex"] = df.get("Flex", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["Status"] = df.get("Status", pd.Series(index=df.index, dtype="object")).fillna("N/D").astype(str)
    df["financial_source"] = (
        df.get("financial_source", pd.Series(index=df.index, dtype="object"))
        .fillna("N/D")
        .astype(str)
    )
    for period_column in ["seconds_period_start", "seconds_period_end"]:
        if period_column in df.columns:
            df[period_column] = pd.to_datetime(df[period_column], errors="coerce").dt.date
        else:
            df[period_column] = pd.NaT

    if "listing_type_id" not in df.columns:
        df["listing_type_id"] = "N/D"
    else:
        df["listing_type_id"] = df["listing_type_id"].fillna("N/D").astype(str)

    df["is_full"] = df["FULL"].str.upper().isin(["SIM", "YES", "TRUE", "1", "FULL"])
    df["full_label"] = df["is_full"].map({True: "FULL", False: "Nao FULL"})
    df["has_cmv"] = df["cmv_seconds"].notna()
    df["negative_margin"] = df["margem_liquida_estimada"].fillna(0) < 0
    return df


@st.cache_data(show_spinner="Carregando financeiro oficial Seconds...")
def load_seconds_official_data(path: str) -> pd.DataFrame:
    """Carrega o snapshot oficial da Seconds em granularidade de anuncio."""

    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    df = apply_seconds_column_compatibility(df)
    df = safe_numeric(
        df,
        [
            "quantity",
            "vendidos",
            "preco_venda_seconds",
            "faturamento_seconds",
            "comissao_seconds",
            "frete_seconds",
            "cmv_seconds",
            "custo_fixo_seconds",
            "imposto_seconds",
            "lucro_bruto_seconds",
            "lucro_liquido_seconds",
            "margem_seconds",
        ],
    )

    period_start, period_end = get_official_seconds_period_from_columns(df)
    if period_start is None or period_end is None:
        period_start, period_end = SECONDS_OFFICIAL_FALLBACK_PERIOD

    df["quantity"] = df.get("vendidos", pd.Series(0, index=df.index)).fillna(0)
    df["unit_price"] = df.get("preco_venda_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["receita"] = df.get("faturamento_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["sale_fee"] = df.get("comissao_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["CMV total"] = df.get("cmv_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["custo_frete_final"] = df.get("frete_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["imposto"] = df.get("imposto_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["custo_fixo"] = df.get("custo_fixo_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["extra"] = 0.0
    df["lucro_bruto"] = df.get("lucro_bruto_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["lucro_liquido_estimado"] = df.get("lucro_liquido_seconds", pd.Series(0, index=df.index)).fillna(0)
    df["lucro_operacional"] = df["lucro_liquido_estimado"]
    df["margem_liquida_estimada"] = df.get("margem_seconds", pd.Series(pd.NA, index=df.index))
    df["margem_operacional"] = df["margem_liquida_estimada"]
    df["margem_bruta"] = df["margem_liquida_estimada"]
    df["seconds_period_start"] = period_start
    df["seconds_period_end"] = period_end
    df["date_created"] = pd.Timestamp(period_start).tz_localize(APP_TIMEZONE)
    df["data_ref"] = period_start
    df["date"] = period_start
    df["month"] = f"{period_start:%Y-%m}"
    df["weekday"] = pd.Timestamp(period_start).day_name()
    df["hour"] = 0
    df["order_id"] = df.get("item_id", pd.Series(index=df.index, dtype="object")).astype(str)
    df["item_id"] = df.get("item_id", pd.Series(index=df.index, dtype="object")).astype(str)
    df["SKU"] = df.get("sku", df.get("SKU", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    df["produto"] = df.get("produto", pd.Series("N/D", index=df.index)).fillna("N/D").astype(str)
    df["Marca"] = df.get("marca", df.get("Marca", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    df["Nome da Categoria"] = (
        df.get("categoria", df.get("Nome da Categoria", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    )
    df["FULL"] = df.get("full", df.get("FULL", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    df["Flex"] = df.get("flex", df.get("Flex", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    df["Status"] = df.get("status", df.get("Status", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    df["LinkAnuncio"] = (
        df.get("link_anuncio", df.get("LinkAnuncio", pd.Series("N/D", index=df.index))).fillna("N/D").astype(str)
    )
    df["listing_type_id"] = "N/D"
    df["financial_source"] = "seconds_official"
    df["is_full"] = df["FULL"].str.upper().isin(["SIM", "YES", "TRUE", "1", "FULL"])
    df["full_label"] = df["is_full"].map({True: "FULL", False: "Nao FULL"})
    df["has_cmv"] = df["cmv_seconds"].fillna(0) > 0
    df["negative_margin"] = df["margem_liquida_estimada"].fillna(0) < 0
    return df


@st.cache_data(show_spinner="Carregando base de estoque...")
def load_inventory_data(path: str) -> pd.DataFrame:
    """Carrega detalhes dos anuncios usados na visao de estoque."""

    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    df = ensure_columns(
        df,
        {
            "id": pd.NA,
            "title": "N/D",
            "category_name": "N/D",
            "brand": "N/D",
            "seller_custom_field": "N/D",
            "permalink": "N/D",
            "listing_type_id": "N/D",
            "shipping_logistic_type": "N/D",
            "estoque_atual": pd.NA,
            "vendidos_total": pd.NA,
            "giro_estimado": pd.NA,
            "status_estoque": "N/D",
            "status": "N/D",
        },
    )
    df = safe_numeric(df, ["estoque_atual", "vendidos_total", "giro_estimado"])
    df["item_id"] = df["id"].fillna("").astype(str)
    df["produto_estoque"] = df["title"].fillna("N/D").astype(str)
    df["Marca_estoque"] = df["brand"].fillna("N/D").astype(str)
    df["Categoria_estoque"] = df["category_name"].fillna("N/D").astype(str)
    df["SKU_estoque"] = df["seller_custom_field"].fillna("N/D").astype(str)
    df["Link_estoque"] = df["permalink"].fillna("N/D").astype(str)
    df["status_estoque"] = df["status_estoque"].fillna("N/D").astype(str)
    df["FULL_estoque"] = df["shipping_logistic_type"].fillna("").astype(str).str.lower().eq("fulfillment").map(
        {True: "Sim", False: "N/D"}
    )
    df["full_label_estoque"] = df["FULL_estoque"].map({"Sim": "FULL", "N/D": "Nao FULL"})
    return df.drop_duplicates(subset=["item_id"], keep="last")


@st.cache_data(show_spinner="Carregando metricas de Ads...")
def load_ads_metrics(path: str) -> pd.DataFrame:
    """Carrega metricas de campanhas Ads com defaults seguros."""

    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    df = ensure_columns(
        df,
        {
            "campaign_id": pd.NA,
            "campaign_name": "N/D",
            "impressions": pd.NA,
            "clicks": pd.NA,
            "cost": pd.NA,
            "cpc": pd.NA,
            "ctr": pd.NA,
            "revenue": pd.NA,
            "orders": pd.NA,
            "units": pd.NA,
            "acos": pd.NA,
            "roas": pd.NA,
            "conversion_rate": pd.NA,
            "data_ref": pd.NaT,
            "date_from": pd.NaT,
            "date_to": pd.NaT,
        },
    )
    df = safe_numeric(
        df,
        [
            "campaign_id",
            "impressions",
            "clicks",
            "cost",
            "cpc",
            "ctr",
            "revenue",
            "orders",
            "units",
            "acos",
            "roas",
            "conversion_rate",
        ],
    )
    df["campaign_name"] = df["campaign_name"].fillna("N/D").astype(str)

    for column in ["data_ref", "date_from", "date_to"]:
        df[column] = parse_ads_datetime_series(df[column])

    date_column = next(
        (
            column
            for column in ["ads_date", "date", "data", "data_ref", "metric_date", "day"]
            if column in df.columns
        ),
        None,
    )
    if date_column:
        df["ads_data_ref"] = df[date_column].map(local_date_from_value)
    else:
        df["ads_data_ref"] = pd.NaT

    period_start_column = next(
        (column for column in ["date_from", "period_start", "data_inicial"] if column in df.columns),
        None,
    )
    period_end_column = next(
        (column for column in ["date_to", "period_end", "data_final"] if column in df.columns),
        None,
    )
    df["ads_period_start"] = (
        df[period_start_column].map(local_date_from_value) if period_start_column else pd.NaT
    )
    df["ads_period_end"] = (
        df[period_end_column].map(local_date_from_value) if period_end_column else pd.NaT
    )

    df = df.dropna(subset=["campaign_id"])
    if df["ads_data_ref"].notna().any():
        return df.drop_duplicates(subset=["campaign_id", "ads_data_ref"], keep="last")
    if df["ads_period_start"].notna().any() and df["ads_period_end"].notna().any():
        return df.drop_duplicates(
            subset=["campaign_id", "ads_period_start", "ads_period_end"],
            keep="last",
        )
    return df.drop_duplicates(subset=["campaign_id"], keep="last")


def parse_ads_datetime_series(series: pd.Series) -> pd.Series:
    """Converte colunas temporais de Ads para o timezone local do app."""

    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert(APP_TIMEZONE)


def local_date_from_value(value: object) -> date | pd.NaT:
    """Converte datas simples ou timestamps com timezone para a data local do app."""

    if pd.isna(value):
        return pd.NaT

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.NaT
    if getattr(parsed, "tzinfo", None) is not None:
        parsed = parsed.tz_convert(APP_TIMEZONE)
    return parsed.date()


def log_ads_load_debug(ads_df: pd.DataFrame) -> None:
    """Imprime debug temporario da carga bruta de Ads."""

    if ads_df.empty:
        period_text = "sem periodo valido"
        cost_total = 0.0
    else:
        valid_dates = ads_df["ads_data_ref"].dropna() if "ads_data_ref" in ads_df.columns else pd.Series(dtype="object")
        period_text = (
            f"{valid_dates.min():%d/%m/%Y} a {valid_dates.max():%d/%m/%Y}"
            if not valid_dates.empty
            else "sem periodo valido"
        )
        cost_total = float(ads_df["cost"].fillna(0).sum()) if "cost" in ads_df.columns else 0.0



def first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def ads_audit_match_debug(
    raw_ads_df: pd.DataFrame,
    filtered_ads_df: pd.DataFrame,
    financial_df: pd.DataFrame,
    selected_period: tuple[date, date],
    ads_filter_info: dict[str, object],
) -> None:
    """Imprime auditoria de Ads para validar gasto, receita atribuida e match."""

    ads = filtered_ads_df.copy()
    raw_ads = raw_ads_df.copy()
    start_date, end_date = selected_period

    total_ads_spend = float(ads["cost"].fillna(0).sum()) if "cost" in ads.columns and not ads.empty else 0.0
    total_ads_revenue = float(ads["revenue"].fillna(0).sum()) if "revenue" in ads.columns and not ads.empty else 0.0
    acos_real = (total_ads_spend / total_ads_revenue * 100) if total_ads_revenue else 0.0
    roas_real = (total_ads_revenue / total_ads_spend) if total_ads_spend else 0.0
    faturamento_total = first_existing_numeric_sum(financial_df, ["receita", "faturamento", "faturamento_seconds"])
    ads_percentual_operacional = (total_ads_spend / faturamento_total * 100) if faturamento_total else 0.0

    campanhas_total = int(ads["campaign_id"].nunique()) if "campaign_id" in ads.columns and not ads.empty else 0
    raw_campanhas_total = int(raw_ads["campaign_id"].nunique()) if "campaign_id" in raw_ads.columns and not raw_ads.empty else 0
    raw_linhas_total = int(len(raw_ads))
    linhas_filtradas = int(len(ads))
    raw_total_ads_spend = float(raw_ads["cost"].fillna(0).sum()) if "cost" in raw_ads.columns and not raw_ads.empty else 0.0
    raw_total_ads_revenue = float(raw_ads["revenue"].fillna(0).sum()) if "revenue" in raw_ads.columns and not raw_ads.empty else 0.0

    ads_item_column = first_existing_column(raw_ads, ["item_id", "MLB", "mlb", "itemId", "item_id_ads"])
    financial_item_column = first_existing_column(financial_df, ["item_id", "MLB", "mlb"])
    if ads_item_column and financial_item_column and not ads.empty:
        ads_item_ids = set(ads[ads_item_column].dropna().astype(str))
        financial_item_ids = set(financial_df[financial_item_column].dropna().astype(str))
        item_ids_ads_unicos = len(ads_item_ids)
        item_ids_com_match_financeiro = len(ads_item_ids & financial_item_ids)
    else:
        ads_item_ids = set()
        item_ids_ads_unicos = 0
        item_ids_com_match_financeiro = 0

    if ads_item_column and item_ids_ads_unicos:
        matched_mask = ads[ads_item_column].astype(str).isin(financial_df[financial_item_column].dropna().astype(str))
        campanhas_com_match = int(ads.loc[matched_mask, "campaign_id"].nunique()) if "campaign_id" in ads.columns else 0
    else:
        campanhas_com_match = 0
    campanhas_sem_match = max(campanhas_total - campanhas_com_match, 0)

    duplicated_keys = 0
    if "campaign_id" in raw_ads.columns and "ads_data_ref" in raw_ads.columns:
        duplicated_keys = int(raw_ads.duplicated(subset=["campaign_id", "ads_data_ref"]).sum())
    elif "campaign_id" in raw_ads.columns:
        duplicated_keys = int(raw_ads.duplicated(subset=["campaign_id"]).sum())

    raw_dates = raw_ads["ads_data_ref"].dropna() if "ads_data_ref" in raw_ads.columns and not raw_ads.empty else pd.Series(dtype="object")
    raw_period = (
        f"{raw_dates.min():%d/%m/%Y} a {raw_dates.max():%d/%m/%Y}"
        if not raw_dates.empty
        else "sem periodo valido"
    )
    ads_parcial_periodo = False
    if not raw_dates.empty:
        ads_parcial_periodo = bool(raw_dates.min() > start_date or raw_dates.max() < end_date)

    if not ads_item_column:
        pass  # item_id indisponivel nos dados de Ads; match financeiro nao e possivel


def filter_ads_by_period(
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aplica ao Ads o mesmo periodo global usado nas vendas."""

    start_date, end_date = selected_period
    info: dict[str, object] = {
        "status": "empty",
        "period": None,
        "message": "Base de Ads vazia.",
    }
    if ads_df.empty:
        return ads_df.copy(), info

    has_period_bounds = (
        "ads_period_start" in ads_df.columns
        and "ads_period_end" in ads_df.columns
        and ads_df["ads_period_start"].notna().any()
        and ads_df["ads_period_end"].notna().any()
    )
    looks_aggregated_by_period = (
        has_period_bounds
        and "ads_data_ref" in ads_df.columns
        and ads_df["ads_data_ref"].notna().any()
        and bool(
            (
                ads_df["ads_data_ref"].fillna(pd.NaT)
                == ads_df["ads_period_end"].fillna(pd.NaT)
            ).all()
        )
        and bool((ads_df["ads_period_start"] != ads_df["ads_period_end"]).any())
    )

    if "ads_data_ref" in ads_df.columns and ads_df["ads_data_ref"].notna().any() and not looks_aggregated_by_period:
        filtered = ads_df[
            (ads_df["ads_data_ref"] >= start_date)
            & (ads_df["ads_data_ref"] <= end_date)
        ].copy()
        valid_dates = filtered["ads_data_ref"].dropna()
        info = {
            "status": "daily_dates",
            "period": (
                valid_dates.min(),
                valid_dates.max(),
            ) if not valid_dates.empty else None,
            "message": None if not filtered.empty else "Sem dados de Ads no periodo selecionado.",
        }
        return filtered, info

    if has_period_bounds:
        exact_period = ads_df[
            (ads_df["ads_period_start"] == start_date)
            & (ads_df["ads_period_end"] == end_date)
        ].copy()
        if not exact_period.empty:
            info = {
                "status": "exact_period",
                "period": (start_date, end_date),
                "message": None,
            }
            return exact_period, info

        available_periods = (
            ads_df[["ads_period_start", "ads_period_end"]]
            .dropna()
            .drop_duplicates()
            .sort_values(["ads_period_start", "ads_period_end"])
        )
        info = {
            "status": "period_mismatch",
            "period": None,
            "message": (
                "Ads possui apenas periodos agregados diferentes do filtro atual; "
                "o custo foi ignorado para nao misturar periodos."
            ),
            "available_periods": available_periods,
        }
        return ads_df.iloc[0:0].copy(), info

    info = {
        "status": "no_valid_dates",
        "period": None,
        "message": (
            "ml_ads_metrics.csv nao possui data valida para recorte temporal; "
            "o custo Ads foi ignorado para nao misturar periodos."
        ),
    }
    return ads_df.iloc[0:0].copy(), info


def calculate_post_ads_values(filtered_sales: pd.DataFrame, filtered_ads: pd.DataFrame) -> dict[str, float]:
    """Calcula pos Ads somente com o Ads ja filtrado pelo periodo global."""

    faturamento = float(filtered_sales["receita"].sum()) if not filtered_sales.empty else 0.0
    lucro_liquido_estimado = (
        float(filtered_sales["lucro_liquido_estimado"].sum())
        if not filtered_sales.empty
        else 0.0
    )
    ads_filtrado_periodo = (
        float(filtered_ads["cost"].fillna(0).sum())
        if not filtered_ads.empty and "cost" in filtered_ads.columns
        else 0.0
    )
    lucro_pos_ads = lucro_liquido_estimado - ads_filtrado_periodo
    margem_pos_ads = (lucro_pos_ads / faturamento * 100) if faturamento else 0.0
    return {
        "faturamento": faturamento,
        "lucro_liquido_estimado": lucro_liquido_estimado,
        "ads_filtrado_periodo": ads_filtrado_periodo,
        "lucro_pos_ads": lucro_pos_ads,
        "margem_pos_ads": margem_pos_ads,
    }


def first_existing_numeric_sum(df: pd.DataFrame, candidates: Iterable[str]) -> float:
    """Soma a primeira coluna numerica disponivel entre nomes equivalentes."""

    for column in candidates:
        if column in df.columns:
            return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
    return 0.0


def first_explicit_other_fee_column(df: pd.DataFrame) -> str | None:
    """Identifica tarifa operacional explicita, ignorando o alias extra vazio criado pelo app."""

    for column in OTHER_OPERATIONAL_FEE_COLUMNS:
        if column not in df.columns:
            continue
        total = float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
        if column == "extra" and total == 0:
            continue
        return column
    return None


def first_existing_numeric_series(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    """Retorna a primeira serie numerica disponivel entre nomes equivalentes."""

    for column in candidates:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce").fillna(0)
    return pd.Series(0.0, index=df.index)


def numeric_sum_if_exists(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def commercial_return_mask(df: pd.DataFrame) -> pd.Series:
    """Identifica linhas com cancelamento, devolucao ou reembolso quando houver status."""

    mask = pd.Series(False, index=df.index)
    patterns = "cancel|devol|refund|return|estorn|charged|chargeback|charged_back"
    for column in ["status_pedido", "Status", "status", "shipping_status", "shipping_substatus"]:
        if column in df.columns:
            mask = mask | df[column].astype(str).str.contains(patterns, case=False, na=False)
    return mask


def commercial_full_mask(df: pd.DataFrame) -> pd.Series:
    """Identifica vendas/anuncios em FULL ou fulfillment."""

    mask = pd.Series(False, index=df.index)
    for column in ["FULL", "full", "FULL_final"]:
        if column in df.columns:
            normalized = df[column].astype(str).str.strip().str.upper()
            mask = mask | normalized.isin(["SIM", "FULL", "FULFILLMENT"])
    if "full_label" in df.columns:
        mask = mask | df["full_label"].astype(str).str.strip().str.upper().eq("FULL")
    if "logistic_type" in df.columns:
        mask = mask | df["logistic_type"].astype(str).str.contains("fulfillment", case=False, na=False)
    return mask


def result_operational_status(result_percent: float) -> str:
    if result_percent > 12:
        return "saudavel"
    if result_percent >= 7:
        return "atencao"
    return "risco"


def ads_available_period(ads_df: pd.DataFrame) -> tuple[date | None, date | None]:
    if ads_df.empty or "ads_data_ref" not in ads_df.columns:
        return None, None

    dates = pd.to_datetime(ads_df["ads_data_ref"], errors="coerce").dropna()
    if dates.empty:
        return None, None
    return dates.min().date(), dates.max().date()


def is_ads_partial_for_period(ads_df: pd.DataFrame, selected_period: tuple[date, date] | None) -> bool:
    if not selected_period:
        return False

    ads_min_date, ads_max_date = ads_available_period(ads_df)
    if not ads_min_date or not ads_max_date:
        return False

    start_date, end_date = selected_period
    return bool(ads_min_date > start_date or ads_max_date < end_date)


def ads_period_label(ads_min_date: date | None, ads_max_date: date | None) -> str:
    if not ads_min_date or not ads_max_date:
        return "sem periodo valido"
    return f"{ads_min_date:%d/%m/%Y} a {ads_max_date:%d/%m/%Y}"


def ads_daily_costs(ads_df: pd.DataFrame) -> pd.DataFrame:
    """Consolida Ads por dia para medir cobertura e estimar lacunas."""

    columns = ["ads_data_ref", "cost"]
    if ads_df.empty or "ads_data_ref" not in ads_df.columns or "cost" not in ads_df.columns:
        return pd.DataFrame(columns=columns)

    work = ads_df.copy()
    work["ads_data_ref"] = pd.to_datetime(work["ads_data_ref"], errors="coerce").dt.date
    work["cost"] = pd.to_numeric(work["cost"], errors="coerce").fillna(0)
    work = work.dropna(subset=["ads_data_ref"])
    if work.empty:
        return pd.DataFrame(columns=columns)
    return work.groupby("ads_data_ref", as_index=False)["cost"].sum()


def estimate_ads_for_period(
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None,
    historical_ads_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Calcula Ads real, estimado e cobertura para o periodo executivo."""

    real_value = float(ads_df["cost"].fillna(0).sum()) if not ads_df.empty and "cost" in ads_df.columns else 0.0
    if not selected_period:
        return {
            "ads_real_value": real_value,
            "ads_estimado_value": 0.0,
            "ads_total_value": real_value,
            "ads_cobertura_pct": 100.0 if real_value else 0.0,
            "ads_dias_cobertos": 0,
            "ads_dias_periodo": 0,
            "ads_fonte": "API Mercado Livre",
            "ads_nivel_cobertura": "Ads reais completos do periodo" if real_value else "Sem dados de Ads",
        }

    start_date, end_date = selected_period
    period_days = max((end_date - start_date).days + 1, 1)
    expected_days = {start_date + timedelta(days=offset) for offset in range(period_days)}
    actual_daily = ads_daily_costs(ads_df)
    covered_days = set(actual_daily["ads_data_ref"]) & expected_days if not actual_daily.empty else set()
    coverage_pct = len(covered_days) / period_days * 100 if period_days else 0.0

    estimated_value = 0.0
    source = "API Mercado Livre"
    level = "Ads reais completos do periodo"
    if coverage_pct < 100:
        missing_days = max(period_days - len(covered_days), 0)
        observed_average = float(actual_daily["cost"].mean()) if not actual_daily.empty else 0.0
        historical_daily = ads_daily_costs(historical_ads_df if historical_ads_df is not None else pd.DataFrame())
        historical_average = float(historical_daily["cost"].mean()) if not historical_daily.empty else 0.0
        daily_average = observed_average if observed_average > 0 else historical_average
        estimated_value = daily_average * missing_days
        if real_value > 0:
            source = "API Mercado Livre + reconstrucao temporal"
            level = "Ads reais parciais + reconstrução histórica"
        elif estimated_value > 0:
            source = "Rateio temporal baseado na media diaria observada"
            level = "Rateio temporal baseado na media diaria observada"
        else:
            source = "Sem dados suficientes para estimativa"
            level = "Sem dados de Ads"

    return {
        "ads_real_value": real_value,
        "ads_estimado_value": estimated_value,
        "ads_total_value": real_value + estimated_value,
        "ads_cobertura_pct": coverage_pct,
        "ads_dias_cobertos": len(covered_days),
        "ads_dias_periodo": period_days,
        "ads_fonte": source,
        "ads_nivel_cobertura": level,
    }


def frete_extrema_value(financial_df: pd.DataFrame) -> tuple[float, str]:
    explicit_column = first_existing_column(financial_df, FRETE_EXTREMA_COLUMNS)
    if explicit_column:
        return abs(first_existing_numeric_sum(financial_df, [explicit_column])), explicit_column

    text_columns = [column for column in FRETE_EXTREMA_TEXT_COLUMNS if column in financial_df.columns]
    if not text_columns or financial_df.empty:
        return 0.0, "indisponivel"

    text = financial_df[text_columns].fillna("").astype(str).agg(" ".join, axis=1)
    extrema_rows = financial_df[text.str.contains("extrema", case=False, na=False)]
    value = first_existing_numeric_sum(
        extrema_rows,
        ["custo_frete_final", "frete_total", "frete_seconds", "shipping_option_cost", "shipping_option_list_cost", "sender_cost"],
    )
    return abs(value), "texto_logistico_extrema" if value else "indisponivel"


def build_full_impact_orders(
    financial_df: pd.DataFrame,
    financials: dict[str, float | bool | date | None],
    top_n: int = 20,
) -> pd.DataFrame:
    """Tabela temporaria para auditar pedidos que mais pesam no componente FULL."""

    columns = ["order_id", "item_id", "shipping_cost", "full_cost", "receita", "percentual_impacto"]
    if financial_df.empty:
        return pd.DataFrame(columns=columns)

    full_rows = financial_df[commercial_full_mask(financial_df)].copy()
    if full_rows.empty:
        return pd.DataFrame(columns=columns)

    full_rows["order_id"] = (
        full_rows["order_id"].astype(str)
        if "order_id" in full_rows.columns
        else pd.Series("sem_order_id", index=full_rows.index)
    )
    full_rows["item_id"] = (
        full_rows["item_id"].astype(str)
        if "item_id" in full_rows.columns
        else pd.Series("sem_item_id", index=full_rows.index)
    )
    full_rows["shipping_cost_debug"] = first_existing_numeric_series(
        full_rows,
        ["shipping_cost", "shipment_cost", "shipping_option_cost", "shipping_option_list_cost", "sender_cost"],
    )
    full_rows["full_cost_debug"] = first_existing_numeric_series(
        full_rows,
        ["custo_frete_final", "frete_total", "frete_seconds", "shipping_option_list_cost"],
    )
    full_rows["receita_debug"] = first_existing_numeric_series(full_rows, ["receita", "faturamento", "faturamento_seconds"])

    grouped = (
        full_rows.groupby(["order_id", "item_id"], dropna=False)
        .agg(
            shipping_cost=("shipping_cost_debug", "sum"),
            full_cost=("full_cost_debug", "sum"),
            receita=("receita_debug", "sum"),
        )
        .reset_index()
    )
    receita_total = float(financials.get("receita") or 0.0)
    grouped["percentual_impacto"] = grouped["full_cost"].div(receita_total).mul(100) if receita_total else 0.0
    return grouped.sort_values("full_cost", ascending=False).head(top_n)[columns]


def format_full_impact_orders_table(full_impact: pd.DataFrame) -> pd.DataFrame:
    display = full_impact.copy()
    if display.empty:
        return display
    for column in ["shipping_cost", "full_cost", "receita"]:
        display[column] = display[column].map(br_money)
    display["percentual_impacto"] = display["percentual_impacto"].map(lambda value: br_percent(value, 4))
    return display


def log_commercial_costs_debug(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    financials: dict[str, float | bool | date | None],
    selected_period: tuple[date, date],
) -> None:
    """Imprime auditoria dos componentes de Custos Comerciais Reais."""

    start_date, end_date = selected_period
    faturamento_total = float(financials.get("receita") or 0.0)
    total_ads = float(financials.get("ads_value") or 0.0)
    total_full = float(financials.get("full_value") or 0.0)
    total_devolucoes = float(financials.get("devolucao_value") or 0.0)
    total_outras_taxas = float(financials.get("outras_taxas_value") or 0.0)
    custo_operacional_total_sem_full = float(financials.get("custo_operacional_total_sem_full") or 0.0)
    resultado_final_corrigido = float(financials.get("resultado_operacional_valor") or 0.0)
    devolucoes_venda_monitorado = float(financials.get("devolucao_valor_venda_monitorado") or 0.0)

    ads_percentual = (total_ads / faturamento_total * 100) if faturamento_total else 0.0
    full_percentual = (total_full / faturamento_total * 100) if faturamento_total else 0.0
    devolucoes_percentual = (total_devolucoes / faturamento_total * 100) if faturamento_total else 0.0
    outras_taxas_percentual = (total_outras_taxas / faturamento_total * 100) if faturamento_total else 0.0

    full_rows = financial_df[commercial_full_mask(financial_df)] if not financial_df.empty else financial_df
    return_rows = financial_df[commercial_return_mask(financial_df)] if not financial_df.empty else financial_df
    full_cost_column = first_existing_column(
        full_rows,
        ["custo_frete_final", "frete_total", "frete_seconds", "shipping_option_list_cost"],
    )

    print(
        "[DEBUG CUSTOS COMERCIAIS] devolucao_custo_real_disponivel="
        f"{financials.get('devolucao_custo_real_disponivel')}"
    )
    for column in [
        "shipping_cost",
        "shipment_cost",
        "shipping_option_cost",
        "shipping_option_list_cost",
        "custo_frete_final",
        "frete_total",
        "custo_frete",
        "frete_seconds",
        "sender_cost",
        "receiver_cost",
    ]:
        value = numeric_sum_if_exists(full_rows, column)
        if value is not None:
            pass  # valor calculado; log removido para producao = first_existing_column(financial_df, ["order_id", "id_pedido", "pedido_id"])
    if SHIPMENTS_PATH.exists() and order_column:
        try:
            shipments = pd.read_csv(SHIPMENTS_PATH)
            shipments["order_id"] = shipments["order_id"].astype(str) if "order_id" in shipments.columns else ""
            order_ids = set(financial_df[order_column].dropna().astype(str))
            shipments_match = shipments[shipments["order_id"].isin(order_ids)].copy()
            if "logistic_type" in shipments_match.columns:
                shipments_full = shipments_match[
                    shipments_match["logistic_type"].astype(str).str.contains("fulfillment", case=False, na=False)
                ]
            else:
                shipments_full = shipments_match
            print(
                "[DEBUG CUSTOS COMERCIAIS] ml_shipments_order_ids_unicos="
                f"{shipments_match['order_id'].nunique() if 'order_id' in shipments_match.columns else 0}"
            )
            for column in ["shipping_option_cost", "shipping_option_list_cost", "sender_cost", "receiver_cost"]:
                value = numeric_sum_if_exists(shipments_full, column)
                if value is not None:
                    pass
        except Exception as exc:
            pass
    else:
        pass  # ml_shipments nao disponivel para conciliacao no periodo

    status_columns = [
        column
        for column in ["status_pedido", "Status", "status", "shipping_status", "shipping_substatus"]
        if column in financial_df.columns
    ]
    status_text = (
        financial_df[status_columns].fillna("").astype(str).agg(" ".join, axis=1)
        if status_columns
        else pd.Series("", index=financial_df.index)
    )
    if order_column and not return_rows.empty:
        pass  # contagens de devolucao; log removido para producao

    full_impact = build_full_impact_orders(financial_df, financials, 20)


def calculate_executive_financials(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None = None,
    historical_ads_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Modelo executivo: resultado final da margem apos custos comerciais."""

    receita = first_existing_numeric_sum(financial_df, ["receita", "faturamento", "faturamento_seconds"])
    cmv = first_existing_numeric_sum(financial_df, ["CMV total", "cmv_total", "cmv_seconds"])
    comissao = first_existing_numeric_sum(financial_df, ["sale_fee", "comissao_ml", "comissao_total", "comissao_seconds"])
    frete = first_existing_numeric_sum(financial_df, ["custo_frete_final", "frete_total", "frete_seconds"])
    impostos = first_existing_numeric_sum(financial_df, ["imposto_total", "imposto", "imposto_seconds"])
    custo_fixo = first_existing_numeric_sum(financial_df, ["custo_fixo_total", "custo_fixo", "custo_fixo_seconds"])
    outras_taxas_coluna = first_explicit_other_fee_column(financial_df)
    outras_taxas_explicita = outras_taxas_coluna is not None
    outras_taxas = (
        first_existing_numeric_sum(financial_df, [outras_taxas_coluna])
        if outras_taxas_coluna
        else 0.0
    )

    margem_operacional_valor = receita - cmv - comissao - frete - impostos - custo_fixo
    margem_operacional_pct = (margem_operacional_valor / receita * 100) if receita else 0.0

    ads_estimate = estimate_ads_for_period(ads_df, selected_period, historical_ads_df)
    ads_value = float(ads_estimate["ads_total_value"] or 0.0)
    ads_min_date, ads_max_date = ads_available_period(ads_df)
    ads_parcial_por_periodo = is_ads_partial_for_period(ads_df, selected_period)
    full_rows = financial_df[commercial_full_mask(financial_df)] if not financial_df.empty else financial_df
    full_value = first_existing_numeric_sum(full_rows, ["custo_frete_final", "frete_total", "frete_seconds", "shipping_option_list_cost"])
    return_rows = financial_df[commercial_return_mask(financial_df)] if not financial_df.empty else financial_df
    devolucao_valor_venda_monitorado = abs(first_existing_numeric_sum(return_rows, ["receita", "faturamento", "faturamento_seconds"]))
    devolucao_custo_coluna = first_existing_column(financial_df, RETURN_COST_COLUMNS)
    devolucao_custo_real_disponivel = devolucao_custo_coluna is not None
    devolucao_base = return_rows if devolucao_custo_real_disponivel and not return_rows.empty else financial_df
    devolucao_value = (
        abs(first_existing_numeric_sum(devolucao_base, [devolucao_custo_coluna]))
        if devolucao_custo_coluna
        else 0.0
    )
    frete_extrema, frete_extrema_origem = frete_extrema_value(financial_df)
    papelaria_embalagens_value = receita * PAPELARIA_EMBALAGENS_PERCENTUAL / 100

    ads_pct = (ads_value / receita * 100) if receita else 0.0
    ads_real_pct = (float(ads_estimate["ads_real_value"] or 0.0) / receita * 100) if receita else 0.0
    ads_estimado_pct = (float(ads_estimate["ads_estimado_value"] or 0.0) / receita * 100) if receita else 0.0
    ads_pct_considerado = ads_pct
    full_pct = (full_value / receita * 100) if receita else 0.0
    full_pct_considerado = 0.0
    devolucao_pct = (devolucao_value / receita * 100) if receita else 0.0
    devolucao_pct_considerado = devolucao_pct
    devolucao_valor_venda_monitorado_pct = (
        devolucao_valor_venda_monitorado / receita * 100
        if receita
        else 0.0
    )
    outras_taxas_pct = (outras_taxas / receita * 100) if receita else 0.0
    outras_taxas_pct_considerado = outras_taxas_pct if outras_taxas_explicita else 0.0
    frete_extrema_pct = (frete_extrema / receita * 100) if receita else 0.0
    papelaria_embalagens_pct = PAPELARIA_EMBALAGENS_PERCENTUAL if receita else 0.0
    custos_operacionais_comerciais_valor = (
        ads_value
        + devolucao_value
        + outras_taxas
        + papelaria_embalagens_value
    )
    impacto_total_pct = (custos_operacionais_comerciais_valor / receita * 100) if receita else 0.0
    meta_operacional_pct = META_OPERACIONAL_TOTAL_PERCENTUAL
    desvio_operacional_pct = impacto_total_pct - meta_operacional_pct
    excesso_operacional_pct = max(0.0, desvio_operacional_pct)
    excesso_operacional_valor = receita * excesso_operacional_pct / 100
    impacto_desvio_valor = receita * desvio_operacional_pct / 100
    resultado_legado_pct = margem_operacional_pct + AJUSTE_OPERACIONAL_PADRAO_PERCENTUAL - impacto_total_pct
    resultado_legado_valor = receita * resultado_legado_pct / 100
    resultado_valor = margem_operacional_valor - custos_operacionais_comerciais_valor
    resultado_pct = (resultado_valor / receita * 100) if receita else 0.0
    custos_extras_operacionais = devolucao_value + outras_taxas

    return {
        "receita": receita,
        "cmv": cmv,
        "comissao": comissao,
        "frete": frete,
        "impostos": impostos,
        "custo_fixo": custo_fixo,
        "margem_operacional_valor": margem_operacional_valor,
        "margem_operacional_pct": margem_operacional_pct,
        "ajuste_operacional_padrao_pct": meta_operacional_pct,
        "meta_operacional_total_pct": meta_operacional_pct,
        "meta_operacional_ads_pct": META_OPERACIONAL_ADS_PERCENTUAL,
        "meta_operacional_full_pct": META_OPERACIONAL_FULL_PERCENTUAL,
        "meta_operacional_devolucoes_pct": META_OPERACIONAL_DEVOLUCOES_PERCENTUAL,
        "meta_operacional_outras_tarifas_pct": META_OPERACIONAL_OUTRAS_TARIFAS_PERCENTUAL,
        "ads_value": ads_value,
        "ads_real_value": float(ads_estimate["ads_real_value"] or 0.0),
        "ads_estimado_value": float(ads_estimate["ads_estimado_value"] or 0.0),
        "ads_pct": ads_pct,
        "ads_real_pct": ads_real_pct,
        "ads_estimado_pct": ads_estimado_pct,
        "ads_pct_considerado": ads_pct_considerado,
        "ads_parcial_por_periodo": ads_parcial_por_periodo,
        "ads_min_date": ads_min_date,
        "ads_max_date": ads_max_date,
        "ads_cobertura_pct": float(ads_estimate["ads_cobertura_pct"] or 0.0),
        "ads_dias_cobertos": int(ads_estimate["ads_dias_cobertos"] or 0),
        "ads_dias_periodo": int(ads_estimate["ads_dias_periodo"] or 0),
        "ads_fonte": ads_estimate["ads_fonte"],
        "ads_nivel_cobertura": ads_estimate["ads_nivel_cobertura"],
        "full_value": full_value,
        "full_pct": full_pct,
        "full_pct_considerado": full_pct_considerado,
        "full_considered_in_total": False,
        "devolucao_value": devolucao_value,
        "devolucao_pct": devolucao_pct,
        "devolucao_pct_considerado": devolucao_pct_considerado,
        "devolucao_custo_real_disponivel": devolucao_custo_real_disponivel,
        "devolucao_custo_coluna": devolucao_custo_coluna,
        "devolucao_valor_venda_monitorado": devolucao_valor_venda_monitorado,
        "devolucao_valor_venda_monitorado_pct": devolucao_valor_venda_monitorado_pct,
        "outras_taxas_value": outras_taxas,
        "outras_taxas_pct": outras_taxas_pct,
        "outras_taxas_pct_considerado": outras_taxas_pct_considerado,
        "outras_taxas_explicita": outras_taxas_explicita,
        "outras_taxas_coluna": outras_taxas_coluna,
        "frete_extrema_value": frete_extrema,
        "frete_extrema_pct": frete_extrema_pct,
        "frete_extrema_origem": frete_extrema_origem,
        "papelaria_embalagens_value": papelaria_embalagens_value,
        "papelaria_embalagens_pct": papelaria_embalagens_pct,
        "custos_operacionais_comerciais_valor": custos_operacionais_comerciais_valor,
        "custo_operacional_total_sem_full": custos_operacionais_comerciais_valor,
        "custos_operacionais_comerciais_pct": impacto_total_pct,
        "custos_extras_operacionais": custos_extras_operacionais,
        "impacto_comercial_total_pct": impacto_total_pct,
        "custos_operacionais_reais_considerados_pct": impacto_total_pct,
        "desvio_operacional_pct": desvio_operacional_pct,
        "impacto_desvio_operacional_valor": impacto_desvio_valor,
        "excesso_operacional_pct": excesso_operacional_pct,
        "excesso_operacional_valor": excesso_operacional_valor,
        "resultado_operacional_legado_pct": resultado_legado_pct,
        "resultado_operacional_legado_valor": resultado_legado_valor,
        "resultado_operacional_pct": resultado_pct,
        "resultado_operacional_valor": resultado_valor,
    }


def executive_cost_composition(financials: dict[str, object]) -> pd.DataFrame:
    devolucao_disponivel = bool(financials["devolucao_custo_real_disponivel"])
    return pd.DataFrame(
        [
            (
                "Ads %",
                financials["ads_pct"],
                financials["ads_pct_considerado"],
                financials["ads_value"],
                "N/D - periodo parcial" if financials["ads_parcial_por_periodo"] else "Incluido no total",
            ),
            (
                "FULL % (informativo)",
                financials["full_pct"],
                financials["full_pct_considerado"],
                financials["full_value"],
                "FULL nao entra no total para evitar dupla contagem de frete.",
            ),
            (
                "Devolucoes %",
                financials["devolucao_pct"] if devolucao_disponivel else None,
                financials["devolucao_pct_considerado"],
                financials["devolucao_value"] if devolucao_disponivel else None,
                "Incluido no total" if devolucao_disponivel else "N/D - custo real nao disponivel",
            ),
            (
                "Outras taxas %",
                financials["outras_taxas_pct"],
                financials["outras_taxas_pct"],
                financials["outras_taxas_value"],
                "Incluido no total",
            ),
        ],
        columns=["componente", "percentual", "percentual_total", "valor", "observacao"],
    )


def format_executive_cost_composition(composition: pd.DataFrame) -> pd.DataFrame:
    display = composition.copy()
    display["percentual"] = display.apply(
        lambda row: "N/D - periodo parcial"
        if row["componente"] == "Ads %" and row["observacao"] == "N/D - periodo parcial"
        else "N/D - custo real nao disponivel"
        if row["componente"] == "Devolucoes %" and row["observacao"] == "N/D - custo real nao disponivel"
        else br_percent(row["percentual"]),
        axis=1,
    )
    display["valor"] = display["valor"].map(br_money)
    return display[["componente", "percentual", "valor", "observacao"]]


def build_commercial_operational_costs(financials: dict[str, object]) -> pd.DataFrame:
    receita = float(financials.get("receita") or 0.0)
    total = float(financials.get("custos_operacionais_comerciais_valor") or 0.0)
    rows = [
        ("Publicidade Mercado Livre", float(financials.get("ads_value") or 0.0), "Incluido no total", True),
        (
            "FULL informativo",
            float(financials.get("full_value") or 0.0),
            "Informativo — ja incluido em Frete",
            False,
        ),
        ("Tarifas de Devolucao", float(financials.get("devolucao_value") or 0.0), "Incluido no total", True),
        ("Outras Tarifas", float(financials.get("outras_taxas_value") or 0.0), "Incluido no total", True),
        ("Papelaria / Embalagens", float(financials.get("papelaria_embalagens_value") or 0.0), "Incluido no total", True),
    ]
    records = []
    for component, value, status, include_in_total in rows:
        records.append(
            {
                "Componente": component,
                "Valor R$": value,
                "% da Receita": percent_of_revenue(value, receita),
                "Participacao": percent_of_revenue(value, total) if include_in_total else 0.0,
                "Status": status,
                "Inclui no Total": include_in_total,
            }
        )
    records.append(
        {
            "Componente": "TOTAL CUSTOS OPERACIONAIS COMERCIAIS",
            "Valor R$": total,
            "% da Receita": percent_of_revenue(total, receita),
            "Participacao": 100.0 if total else 0.0,
            "Status": "Total sem FULL",
            "Inclui no Total": True,
        }
    )
    return pd.DataFrame(records)


def render_commercial_operational_costs(financials: dict[str, object]) -> None:
    costs = build_commercial_operational_costs(financials)

    def commercial_component_label(component: str) -> str:
        tooltip = COMMERCIAL_COST_TOOLTIPS.get(component)
        component_html = html.escape(component)
        if not tooltip:
            return component_html
        tooltip_html = html.escape(tooltip, quote=True)
        return (
            f'<span class="commercial-tooltip" title="{tooltip_html}">'
            f"{component_html}"
            f'<span class="kpi-help" title="{tooltip_html}" aria-label="Explicacao do custo comercial">&#8505;</span>'
            f"</span>"
        )

    rows: list[str] = []
    for _, row in costs.iterrows():
        component = safe_text(row["Componente"])
        value = float(row["Valor R$"] or 0.0)
        revenue_pct = float(row["% da Receita"] or 0.0)
        share_pct = float(row["Participacao"] or 0.0)
        status = safe_text(row.get("Status"))
        is_total = component == "TOTAL CUSTOS OPERACIONAIS COMERCIAIS"
        row_class = "commercial-total-row" if is_total else ""
        rows.append(
            f'<tr class="{row_class}">'
            f"<td>{commercial_component_label(component)}</td>"
            f"<td>{html.escape(br_money(value))}</td>"
            f"<td>{html.escape(br_percent(revenue_pct, 2))}</td>"
            "<td>"
            '<div class="commercial-share-line">'
            f"<span>{html.escape(br_percent(share_pct, 2))}</span>"
            '<div class="commercial-share-track">'
            f'<div class="commercial-share-fill" style="width:{min(share_pct, 100):.2f}%;"></div>'
            "</div>"
            "</div>"
            "</td>"
            f"<td>{html.escape(status)}</td>"
            "</tr>"
        )

    ads_source = safe_text(financials.get("ads_fonte"))
    ads_level = safe_text(financials.get("ads_nivel_cobertura"))
    ads_coverage = float(financials.get("ads_cobertura_pct") or 0.0)
    ads_detail = (
        f"Ads Real: {br_money(float(financials.get('ads_real_value') or 0.0))} | "
        f"Ads Estimado: {br_money(float(financials.get('ads_estimado_value') or 0.0))} | "
        f"Cobertura: {br_percent(ads_coverage, 0)} | Fonte: {ads_source}"
    )

    table_html = f"""
<style>
.commercial-cost-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 .38rem;
}}
.commercial-cost-table th {{
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: 0;
    color: rgba(148,163,184,.92);
    text-align: left;
    padding: 0 .78rem .12rem .78rem;
}}
.commercial-cost-table td {{
    border-top: 1px solid rgba(148,163,184,.16);
    border-bottom: 1px solid rgba(148,163,184,.16);
    padding: .68rem .78rem;
    background: rgba(15,23,42,.20);
    font-weight: 790;
}}
.commercial-cost-table td:first-child {{
    border-left: 1px solid rgba(148,163,184,.16);
    border-radius: 8px 0 0 8px;
    font-weight: 900;
}}
.commercial-cost-table td:last-child {{
    border-right: 1px solid rgba(148,163,184,.16);
    border-radius: 0 8px 8px 0;
}}
.commercial-total-row td {{
    background: rgba(217,119,6,.18);
    border-color: rgba(217,119,6,.36);
    color: #D97706;
}}
.commercial-tooltip {{
    display: inline-flex;
    align-items: center;
}}
.commercial-share-line {{
    display: grid;
    grid-template-columns: 76px minmax(120px, 1fr);
    gap: .7rem;
    align-items: center;
}}
.commercial-share-track {{
    height: .46rem;
    border-radius: 999px;
    background: rgba(148,163,184,.18);
    overflow: hidden;
}}
.commercial-share-fill {{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(217,119,6,.42), #D97706);
}}
.ads-coverage-note {{
    border: 1px solid rgba(148,163,184,.16);
    border-left: 4px solid #D97706;
    border-radius: 8px;
    padding: .72rem .85rem;
    margin-bottom: .7rem;
    background: rgba(217,119,6,.08);
    color: rgba(226,232,240,.94);
    font-weight: 760;
}}
.ads-coverage-note span {{
    display:block;
    color:#D97706;
    font-size:.75rem;
    text-transform:uppercase;
    font-weight:900;
    margin-bottom:.18rem;
}}
</style>
<div class="section-title">CUSTOS OPERACIONAIS COMERCIAIS</div>
<div class="ads-coverage-note"><span>{html.escape(ads_level)}</span>{html.escape(ads_detail)}</div>
<table class="commercial-cost-table">
<thead>
<tr>
<th>Componente</th>
<th>Valor R$</th>
<th>% da Receita</th>
<th>Part. no Total</th>
<th>Status</th>
</tr>
</thead>
<tbody>{''.join(rows)}</tbody>
</table>
"""
    st.markdown(table_html.strip(), unsafe_allow_html=True)
    st.markdown('<div class="section-title">Insights Automaticos</div>', unsafe_allow_html=True)
    for insight in commercial_operational_insights(financials):
        st.markdown(f"- {html.escape(insight)}")


def commercial_operational_insights(financials: dict[str, object]) -> list[str]:
    ads_pct = float(financials.get("ads_pct") or 0.0)
    full_pct = float(financials.get("full_pct") or 0.0)
    devolucao_pct = float(financials.get("devolucao_pct") or 0.0)
    papelaria_value = float(financials.get("papelaria_embalagens_value") or 0.0)
    total_pct = float(financials.get("custos_operacionais_comerciais_pct") or 0.0)
    insights = [
        f"A publicidade representa {br_percent(ads_pct)} da receita"
        + (" e esta acima da meta historica de 3%." if ads_pct > META_OPERACIONAL_ADS_PERCENTUAL else "."),
        f"O Mercado Envios FULL representa {br_percent(full_pct)} da receita.",
        "Mercado Envios FULL e exibido como informativo porque ja esta considerado em Frete, evitando dupla contagem.",
        f"As devolucoes representam {br_percent(devolucao_pct)} da receita.",
        f"A papelaria consumiu {br_money(papelaria_value)} ({br_percent(PAPELARIA_EMBALAGENS_PERCENTUAL)} da receita).",
        f"Os custos operacionais comerciais consumiram {br_percent(total_pct)} da receita.",
    ]
    if float(financials.get("ads_estimado_value") or 0.0) > 0:
        insights.append(
            "Ads contem estimativa temporal: "
            f"{br_percent(float(financials.get('ads_cobertura_pct') or 0.0), 0)} de cobertura real."
        )
    return insights[:7]


def ml_cost_audit_rows(financial_df: pd.DataFrame, ads_df: pd.DataFrame, financials: dict[str, object]) -> pd.DataFrame:
    def status_collected(condition: bool) -> str:
        return "Coletado" if condition else "Nao identificado"

    return pd.DataFrame(
        [
            {
                "Componente API ML": "Investimento em campanha de publicidade",
                "Situacao": status_collected(not ads_df.empty and "cost" in ads_df.columns),
                "Uso atual": "Publicidade Mercado Livre nos custos comerciais",
                "Campo/Fonte": "data/ml_ads_metrics.csv: cost",
                "Pode incorporar": "Ja incorporado; usa estimativa temporal quando a cobertura e parcial.",
            },
            {
                "Componente API ML": "Tarifas de venda",
                "Situacao": status_collected(any(column in financial_df.columns for column in ["sale_fee", "comissao_ml", "comissao_total"])),
                "Uso atual": "Linha Comissao ML da DRE",
                "Campo/Fonte": "sale_fee, comissao_ml, comissao_total",
                "Pode incorporar": "Ja incorporado na DRE.",
            },
            {
                "Componente API ML": "Tarifas de envio",
                "Situacao": status_collected(any(column in financial_df.columns for column in ["custo_frete_final", "frete_total", "frete_seconds"])),
                "Uso atual": "Linha Frete da DRE",
                "Campo/Fonte": "custo_frete_final, frete_total, frete_seconds",
                "Pode incorporar": "Ja incorporado na DRE.",
            },
            {
                "Componente API ML": "Custos Mercado Envios FULL",
                "Situacao": status_collected(any(column in financial_df.columns for column in ["FULL", "full", "logistic_type"])),
                "Uso atual": "Mercado Envios FULL nos custos comerciais",
                "Campo/Fonte": "FULL/full/logistic_type + custo de frete",
                "Pode incorporar": "Ja incorporado ao bloco comercial.",
            },
            {
                "Componente API ML": "Tarifas de devolucao",
                "Situacao": status_collected(bool(financials.get("devolucao_custo_real_disponivel"))),
                "Uso atual": "Tarifas de Devolucao quando ha coluna explicita; caso contrario fica zerado",
                "Campo/Fonte": safe_text(financials.get("devolucao_custo_coluna") or "coluna explicita ausente"),
                "Pode incorporar": "Buscar detalhe financeiro de refunds/claims caso a API exponha o custo real por pedido.",
            },
            {
                "Componente API ML": "Outras tarifas, outros servicos e taxas extras",
                "Situacao": status_collected(bool(financials.get("outras_taxas_explicita"))),
                "Uso atual": "Outras Tarifas nos custos comerciais",
                "Campo/Fonte": safe_text(financials.get("outras_taxas_coluna") or "coluna explicita ausente"),
                "Pode incorporar": "Colunas novas com nomes equivalentes ja entram automaticamente no modelo.",
            },
            {
                "Componente API ML": "Frete para Extrema",
                "Situacao": status_collected(float(financials.get("frete_extrema_value") or 0.0) > 0),
                "Uso atual": "Frete para Extrema nos custos comerciais",
                "Campo/Fonte": safe_text(financials.get("frete_extrema_origem") or "indisponivel"),
                "Pode incorporar": "Usa coluna explicita ou texto logistico contendo Extrema.",
            },
            {
                "Componente API ML": "Componentes presentes nos detalhes financeiros dos pedidos",
                "Situacao": "Parcial",
                "Uso atual": "Pedido, item, sale_fee e shipment sao persistidos; breakdown financeiro completo nao aparece no CSV atual",
                "Campo/Fonte": "orders/search, /orders/{id}, /shipments/{id}",
                "Pode incorporar": "Persistir financial details/charges quando disponiveis na API ML para separar servicos, ajustes e estornos.",
            },
        ]
    )


def render_ml_cost_audit(financial_df: pd.DataFrame, ads_df: pd.DataFrame, financials: dict[str, object]) -> None:
    st.markdown('<div class="section-title">Auditoria dos Custos Mercado Livre</div>', unsafe_allow_html=True)
    audit = ml_cost_audit_rows(financial_df, ads_df, financials)
    st.dataframe(audit, use_container_width=True, hide_index=True, height=320)
    st.info(
        "Auditoria concluida na camada financeira: o dashboard usa os campos ja persistidos em CSV, "
        "sem alterar endpoints, coleta ou merges. Campos futuros equivalentes de outras tarifas, devolucoes "
        "e frete Extrema entram no modelo quando aparecerem na base."
    )


def calculate_financial_audit_summary(financial_df: pd.DataFrame) -> dict[str, object]:
    """Resume a cobertura financeira ML x Seconds sem alterar a DRE."""

    if financial_df.empty:
        return {
            "total_orders": 0,
            "orders_with_cmv": 0,
            "orders_without_cmv": 0,
            "cmv_coverage_pct": 0.0,
            "total_revenue": 0.0,
            "reconciled_revenue": 0.0,
            "unreconciled_revenue": 0.0,
            "reconciled_revenue_pct": 0.0,
            "total_skus": 0,
            "matched_skus": 0,
            "sku_coverage_pct": 0.0,
            "rentability_coverage_pct": 0.0,
            "score": 0.0,
            "score_label": "Critica",
            "components": {},
        }

    active = financial_df.copy()
    order_column = first_existing_column(active, ["order_id", "Pedido", "pedido"])
    item_column = first_existing_column(active, ["item_id", "MLB", "mlb"])
    sku_column = first_existing_column(active, ["sku", "SKU"])

    receita = pd.to_numeric(
        active.get("receita", active.get("faturamento", active.get("faturamento_seconds", 0))),
        errors="coerce",
    ).fillna(0)
    cmv = pd.to_numeric(
        active.get("CMV total", active.get("cmv_total", active.get("cmv_seconds", 0))),
        errors="coerce",
    ).fillna(0)
    cmv_unit = pd.to_numeric(active.get("cmv_unitario_seconds", cmv), errors="coerce").fillna(0)

    if "parametro_confiavel" in active.columns:
        reliable = active["parametro_confiavel"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
    else:
        reliable = cmv > 0

    if "match_seconds" in active.columns:
        matched = active["match_seconds"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
    else:
        matched = cmv > 0

    valid_cmv = reliable & (cmv > 0) & (cmv_unit > 0)

    def count_entities(mask: pd.Series | None = None) -> int:
        if order_column:
            values = active[order_column].fillna("").astype(str).str.strip()
            valid_values = values != ""
            if mask is not None:
                valid_values = valid_values & mask
            return int(values[valid_values].nunique())
        if mask is None:
            return int(len(active))
        return int(mask.sum())

    total_orders = count_entities()
    orders_with_cmv = count_entities(valid_cmv)
    orders_without_cmv = max(total_orders - orders_with_cmv, 0)
    total_revenue = float(receita.sum())
    reconciled_revenue = float(receita[valid_cmv].sum())
    unreconciled_revenue = total_revenue - reconciled_revenue

    sku_base_column = item_column or sku_column
    if sku_base_column:
        sku_values = active[sku_base_column].fillna("").astype(str).str.strip()
        valid_skus = sku_values != ""
        total_skus = int(sku_values[valid_skus].nunique())
        matched_skus = int(sku_values[valid_skus & matched].nunique())
    else:
        total_skus = 0
        matched_skus = 0

    margin = pd.to_numeric(active.get("margem_liquida_estimada", pd.Series(index=active.index)), errors="coerce")
    profit = pd.to_numeric(active.get("lucro_liquido_estimado", pd.Series(index=active.index)), errors="coerce")
    rentability_valid = valid_cmv & receita.gt(0) & margin.notna() & profit.notna()
    orders_with_rentability = count_entities(rentability_valid)

    cmv_coverage_pct = (orders_with_cmv / total_orders * 100) if total_orders else 0.0
    sku_coverage_pct = (matched_skus / total_skus * 100) if total_skus else 0.0
    rentability_coverage_pct = (orders_with_rentability / total_orders * 100) if total_orders else 0.0
    reconciled_revenue_pct = (reconciled_revenue / total_revenue * 100) if total_revenue else 0.0

    components = {
        "Cobertura CMV": cmv_coverage_pct,
        "Cobertura SKU": sku_coverage_pct,
        "Cobertura Rentabilidade": rentability_coverage_pct,
        "Pedidos conciliados": cmv_coverage_pct,
        "Receita conciliada": reconciled_revenue_pct,
    }
    score = sum(components.values()) / len(components) if components else 0.0
    if score >= 90:
        score_label = "Excelente"
    elif score >= 80:
        score_label = "Boa"
    elif score >= 70:
        score_label = "Atencao"
    else:
        score_label = "Critica"

    return {
        "total_orders": total_orders,
        "orders_with_cmv": orders_with_cmv,
        "orders_without_cmv": orders_without_cmv,
        "cmv_coverage_pct": cmv_coverage_pct,
        "total_revenue": total_revenue,
        "reconciled_revenue": reconciled_revenue,
        "unreconciled_revenue": unreconciled_revenue,
        "reconciled_revenue_pct": reconciled_revenue_pct,
        "total_skus": total_skus,
        "matched_skus": matched_skus,
        "sku_coverage_pct": sku_coverage_pct,
        "rentability_coverage_pct": rentability_coverage_pct,
        "score": score,
        "score_label": score_label,
        "components": components,
    }


def render_financial_audit_expander(financial_df: pd.DataFrame) -> None:
    audit = calculate_financial_audit_summary(financial_df)
    with st.expander("Auditoria Financeira", expanded=False):
        st.caption("Conciliacao tecnica ML x Seconds calculada sobre o periodo e filtros atuais.")
        cols = st.columns(5)
        cols[0].metric("Cobertura CMV", br_percent(audit["cmv_coverage_pct"]))
        cols[1].metric("Cobertura SKU", br_percent(audit["sku_coverage_pct"]))
        cols[2].metric("Receita conciliada", br_money(audit["reconciled_revenue"]))
        cols[3].metric("Pedidos conciliados", br_number(audit["orders_with_cmv"], 0))
        cols[4].metric("Score integridade", f"{br_number(audit['score'], 1)}/100")

        details = pd.DataFrame(
            [
                ("Pedidos/registros totais", br_number(audit["total_orders"], 0)),
                ("Pedidos/registros com CMV valido", br_number(audit["orders_with_cmv"], 0)),
                ("Pedidos/registros sem CMV valido", br_number(audit["orders_without_cmv"], 0)),
                ("Receita total", br_money(audit["total_revenue"])),
                ("Receita sem CMV valido", br_money(audit["unreconciled_revenue"])),
                ("SKUs/item_id unicos", br_number(audit["total_skus"], 0)),
                ("SKUs/item_id encontrados", br_number(audit["matched_skus"], 0)),
                ("Cobertura de rentabilidade", br_percent(audit["rentability_coverage_pct"])),
                ("Classificacao", str(audit["score_label"])),
            ],
            columns=["Indicador", "Valor"],
        )
        st.dataframe(details, use_container_width=True, hide_index=True)
        if float(audit["cmv_coverage_pct"]) < 99:
            st.warning(
                "Cobertura CMV abaixo de 99%. A receita permanece na DRE, mas pedidos sem CMV valido "
                "ficam com custos Seconds incompletos."
            )


def classify_missing_cmv_reason(financial_df: pd.DataFrame) -> pd.Series:
    if financial_df.empty:
        return pd.Series(dtype="object")

    active = financial_df.copy()
    item_column = first_existing_column(active, ["item_id", "MLB", "mlb"])
    sku_column = first_existing_column(active, ["sku", "SKU"])
    item_id = (
        active[item_column].fillna("").astype(str).str.strip()
        if item_column
        else pd.Series("", index=active.index, dtype="object")
    )
    sku = (
        active[sku_column].fillna("").astype(str).str.strip()
        if sku_column
        else pd.Series("", index=active.index, dtype="object")
    )

    if "match_seconds" in active.columns:
        matched = active["match_seconds"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
    else:
        matched = pd.to_numeric(
            active.get("CMV total", active.get("cmv_total", active.get("cmv_seconds", 0))),
            errors="coerce",
        ).fillna(0) > 0

    if "parametro_confiavel" in active.columns:
        reliable = active["parametro_confiavel"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
    else:
        reliable = matched

    cmv_total = pd.to_numeric(
        active.get("CMV total", active.get("cmv_total", active.get("cmv_seconds", pd.Series(index=active.index)))),
        errors="coerce",
    )
    cmv_unit = pd.to_numeric(active.get("cmv_unitario_seconds", cmv_total), errors="coerce")

    reason = pd.Series("OUTRO", index=active.index, dtype="object")
    reason.loc[item_id.eq("")] = "ERRO_MERGE"
    reason.loc[item_id.ne("") & ~matched] = "SEM_MATCH_SECONDS"
    reason.loc[item_id.ne("") & matched & sku.isin(["", "N/D", "nan", "None"])] = "SKU_NAO_ENCONTRADO"
    reason.loc[item_id.ne("") & matched & ~reliable] = "PARAMETRO_NAO_CONFIAVEL"
    reason.loc[item_id.ne("") & matched & reliable & cmv_unit.isna()] = "CMV_NULO"
    reason.loc[item_id.ne("") & matched & reliable & cmv_total.isna()] = "CMV_NULO"
    reason.loc[item_id.ne("") & matched & reliable & (cmv_unit.fillna(0) <= 0)] = "CMV_ZERADO"
    reason.loc[item_id.ne("") & matched & reliable & (cmv_total.fillna(0) <= 0)] = "CMV_ZERADO"
    return reason


def missing_cmv_items_table(financial_df: pd.DataFrame) -> pd.DataFrame:
    if financial_df.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "sku",
                "produto",
                "marca",
                "categoria",
                "receita_total",
                "pedidos",
                "unidades",
                "motivo_sem_cmv",
            ]
        )

    active = financial_df.copy()
    order_column = first_existing_column(active, ["order_id", "Pedido", "pedido"])
    item_column = first_existing_column(active, ["item_id", "MLB", "mlb"])
    sku_column = first_existing_column(active, ["sku", "SKU"])
    product_column = first_existing_column(active, ["produto", "Produto", "item_title"])
    brand_column = first_existing_column(active, ["marca", "Marca"])
    category_column = first_existing_column(active, ["categoria", "Nome da Categoria", "category"])

    receita = pd.to_numeric(
        active.get("receita", active.get("faturamento", active.get("faturamento_seconds", 0))),
        errors="coerce",
    ).fillna(0)
    cmv_total = pd.to_numeric(
        active.get("CMV total", active.get("cmv_total", active.get("cmv_seconds", 0))),
        errors="coerce",
    ).fillna(0)
    cmv_unit = pd.to_numeric(active.get("cmv_unitario_seconds", cmv_total), errors="coerce").fillna(0)
    reliable = (
        active["parametro_confiavel"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
        if "parametro_confiavel" in active.columns
        else cmv_total > 0
    )
    matched = (
        active["match_seconds"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
        if "match_seconds" in active.columns
        else cmv_total > 0
    )
    missing = ~(matched & reliable & (cmv_total > 0) & (cmv_unit > 0))

    rows = active.loc[missing].copy()
    if rows.empty:
        return pd.DataFrame(
            columns=["item_id", "sku", "produto", "marca", "categoria", "receita_total", "pedidos", "unidades", "motivo_sem_cmv"]
        )

    rows["item_id"] = rows[item_column].fillna("").astype(str).str.strip() if item_column else "N/D"
    rows["sku"] = rows[sku_column].fillna("").astype(str).str.strip() if sku_column else "N/D"
    rows["sku"] = rows["sku"].replace("", "N/D")
    rows["produto"] = rows[product_column].fillna("").astype(str).str.strip() if product_column else "N/D"
    rows["produto"] = rows["produto"].replace("", "N/D")
    rows["marca"] = rows[brand_column].fillna("").astype(str).str.strip() if brand_column else "N/D"
    rows["marca"] = rows["marca"].replace("", "N/D")
    rows["categoria"] = rows[category_column].fillna("").astype(str).str.strip() if category_column else "N/D"
    rows["categoria"] = rows["categoria"].replace("", "N/D")
    rows["receita_num"] = receita.loc[rows.index]
    rows["unidades_num"] = pd.to_numeric(rows.get("quantity", 1), errors="coerce").fillna(0)
    rows["pedido_ref"] = rows[order_column].fillna("").astype(str).str.strip() if order_column else rows.index.astype(str)
    rows["motivo_sem_cmv"] = classify_missing_cmv_reason(rows)

    return (
        rows.groupby(["item_id", "sku", "produto", "marca", "categoria", "motivo_sem_cmv"], dropna=False)
        .agg(receita_total=("receita_num", "sum"), pedidos=("pedido_ref", "nunique"), unidades=("unidades_num", "sum"))
        .reset_index()
        .sort_values(["receita_total", "pedidos"], ascending=[False, False])
    )


def potential_cmv_coverage_after_fix(financial_df: pd.DataFrame, items: pd.DataFrame, top_n: int) -> dict[str, float]:
    if financial_df.empty or items.empty:
        return {"top_n": top_n, "pedidos_recuperados": 0, "receita_recuperada": 0.0, "cobertura_pedidos": 0.0}

    active = financial_df.copy()
    order_column = first_existing_column(active, ["order_id", "Pedido", "pedido"])
    item_column = first_existing_column(active, ["item_id", "MLB", "mlb"])
    if not item_column:
        return {"top_n": top_n, "pedidos_recuperados": 0, "receita_recuperada": 0.0, "cobertura_pedidos": 0.0}

    cmv_total = pd.to_numeric(
        active.get("CMV total", active.get("cmv_total", active.get("cmv_seconds", 0))),
        errors="coerce",
    ).fillna(0)
    cmv_unit = pd.to_numeric(active.get("cmv_unitario_seconds", cmv_total), errors="coerce").fillna(0)
    reliable = (
        active["parametro_confiavel"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
        if "parametro_confiavel" in active.columns
        else cmv_total > 0
    )
    matched = (
        active["match_seconds"].astype(str).str.lower().isin({"true", "1", "sim", "yes"})
        if "match_seconds" in active.columns
        else cmv_total > 0
    )
    valid = matched & reliable & (cmv_total > 0) & (cmv_unit > 0)
    item_values = active[item_column].fillna("").astype(str).str.strip()
    order_values = active[order_column].fillna("").astype(str).str.strip() if order_column else pd.Series(active.index.astype(str), index=active.index)
    receita = pd.to_numeric(
        active.get("receita", active.get("faturamento", active.get("faturamento_seconds", 0))),
        errors="coerce",
    ).fillna(0)

    total_orders = int(order_values[order_values != ""].nunique())
    valid_orders = int(order_values[valid & order_values.ne("")].nunique())
    top_items = set(items.head(top_n)["item_id"].astype(str))
    recovered_mask = ~valid & item_values.isin(top_items)
    recovered_orders = int(order_values[recovered_mask & order_values.ne("")].nunique())
    recovered_revenue = float(receita[recovered_mask].sum())
    coverage = ((valid_orders + recovered_orders) / total_orders * 100) if total_orders else 0.0
    return {
        "top_n": top_n,
        "pedidos_recuperados": recovered_orders,
        "receita_recuperada": recovered_revenue,
        "cobertura_pedidos": coverage,
    }


def render_missing_cmv_products_expander(financial_df: pd.DataFrame) -> None:
    audit = calculate_financial_audit_summary(financial_df)
    items = missing_cmv_items_table(financial_df)
    with st.expander("Produtos sem CMV Confiável", expanded=False):
        st.caption("Lista tecnica para correcao de parametros na Seconds; nao altera a DRE.")
        cols = st.columns(4)
        cols[0].metric("Cobertura CMV", br_percent(audit["cmv_coverage_pct"]))
        cols[1].metric("Receita sem CMV", br_money(audit["unreconciled_revenue"]))
        cols[2].metric("Pedidos sem CMV", br_number(audit["orders_without_cmv"], 0))
        cols[3].metric("Itens afetados", br_number(len(items), 0))

        if items.empty:
            st.success("Nenhum produto sem CMV confiavel no filtro atual.")
            return

        display = items.head(20).copy()
        display["receita_total"] = display["receita_total"].map(br_money)
        display["unidades"] = display["unidades"].map(lambda value: br_number(value, 0))
        st.dataframe(
            display[["item_id", "sku", "produto", "marca", "receita_total", "pedidos", "unidades", "motivo_sem_cmv"]],
            use_container_width=True,
            hide_index=True,
            height=420,
        )

        potential = pd.DataFrame(
            [potential_cmv_coverage_after_fix(financial_df, items, top_n) for top_n in [20, 50, 100]]
        )
        potential["Cenario"] = potential["top_n"].map(lambda value: f"Corrigir Top {int(value)}")
        potential["Pedidos recuperados"] = potential["pedidos_recuperados"].map(lambda value: br_number(value, 0))
        potential["Receita recuperada"] = potential["receita_recuperada"].map(br_money)
        potential["Cobertura apos correcao"] = potential["cobertura_pedidos"].map(br_percent)
        st.dataframe(
            potential[["Cenario", "Pedidos recuperados", "Receita recuperada", "Cobertura apos correcao"]],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download CSV - produtos sem CMV confiavel",
            data=items.to_csv(index=False, encoding="utf-8-sig"),
            file_name="itens_sem_cmv_filtrado.csv",
            mime="text/csv",
        )


def render_matching_inteligente_expander(financial_df: pd.DataFrame) -> None:
    """Painel de visibilidade do matching inteligente ML x Seconds."""
    if financial_df.empty or "match_type" not in financial_df.columns:
        return

    receita_total = float(
        pd.to_numeric(financial_df.get("receita", 0), errors="coerce").fillna(0).sum()
    )
    if receita_total <= 0:
        return

    with st.expander("Matching Inteligente ML x Seconds", expanded=False):
        st.caption(
            "Rastreabilidade do pipeline de correspondencia entre anuncios ML e parametros Seconds. "
            "Somente leitura — nao altera DRE nem calculos financeiros."
        )

        # --- Metricas por tipo de match ---
        mt_col = financial_df["match_type"].fillna("SEM_MATCH")
        r_exact = float(financial_df.loc[mt_col == "EXACT", "receita"].sum() if "receita" in financial_df.columns else 0)
        r_fuzzy = float(financial_df.loc[mt_col == "FUZZY_AUTO", "receita"].sum() if "receita" in financial_df.columns else 0)
        r_ctrl = float(financial_df.loc[mt_col == "FUZZY_AUTO_CONTROLLED", "receita"].sum() if "receita" in financial_df.columns else 0)
        r_prov = float(financial_df.loc[mt_col == "MATCH_PROVAVEL", "receita"].sum() if "receita" in financial_df.columns else 0)
        r_sem = float(financial_df.loc[mt_col == "SEM_MATCH", "receita"].sum() if "receita" in financial_df.columns else 0)

        n_exact = int(financial_df.loc[mt_col == "EXACT", "item_id"].nunique() if "item_id" in financial_df.columns else 0)
        n_fuzzy = int(financial_df.loc[mt_col == "FUZZY_AUTO", "item_id"].nunique() if "item_id" in financial_df.columns else 0)
        n_ctrl = int(financial_df.loc[mt_col == "FUZZY_AUTO_CONTROLLED", "item_id"].nunique() if "item_id" in financial_df.columns else 0)
        n_prov = int(financial_df.loc[mt_col == "MATCH_PROVAVEL", "item_id"].nunique() if "item_id" in financial_df.columns else 0)
        n_sem = int(financial_df.loc[mt_col == "SEM_MATCH", "item_id"].nunique() if "item_id" in financial_df.columns else 0)

        cobertura_exact = r_exact / receita_total * 100 if receita_total else 0
        cobertura_fuzzy = (r_exact + r_fuzzy) / receita_total * 100 if receita_total else 0
        cobertura_ctrl = (r_exact + r_fuzzy + r_ctrl) / receita_total * 100 if receita_total else 0

        cols = st.columns(4)
        cols[0].metric("Cobertura EXACT", br_percent(cobertura_exact), help="Match direto por item_id")
        cols[1].metric(
            "Ganho FUZZY_AUTO",
            br_percent(cobertura_fuzzy - cobertura_exact),
            delta=f"+{br_percent(cobertura_fuzzy - cobertura_exact)}",
            help="Score >= 85 automaticamente aprovado",
        )
        cols[2].metric(
            "Ganho CONTROLLED",
            br_percent(cobertura_ctrl - cobertura_fuzzy),
            delta=f"+{br_percent(cobertura_ctrl - cobertura_fuzzy)}",
            help="Score 80-84 com filtros: keywords, comprimento, marca, gap",
        )
        cols[3].metric("Cobertura Total CMV", br_percent(cobertura_ctrl))

        st.markdown("---")

        # --- Tabela de breakdown ---
        breakdown_data = [
            {
                "Tipo": "EXACT",
                "CMV Aplicado": "Sim",
                "Itens": n_exact,
                "Receita": br_money(r_exact),
                "% Receita": br_percent(r_exact / receita_total * 100 if receita_total else 0),
            },
            {
                "Tipo": "FUZZY_AUTO (score ≥ 85)",
                "CMV Aplicado": "Sim",
                "Itens": n_fuzzy,
                "Receita": br_money(r_fuzzy),
                "% Receita": br_percent(r_fuzzy / receita_total * 100 if receita_total else 0),
            },
            {
                "Tipo": "FUZZY_AUTO_CONTROLLED (80-84 + filtros)",
                "CMV Aplicado": "Sim",
                "Itens": n_ctrl,
                "Receita": br_money(r_ctrl),
                "% Receita": br_percent(r_ctrl / receita_total * 100 if receita_total else 0),
            },
            {
                "Tipo": "MATCH_PROVAVEL (75-79 ou reprovado)",
                "CMV Aplicado": "Não",
                "Itens": n_prov,
                "Receita": br_money(r_prov),
                "% Receita": br_percent(r_prov / receita_total * 100 if receita_total else 0),
            },
            {
                "Tipo": "SEM_MATCH (score < 75)",
                "CMV Aplicado": "Não",
                "Itens": n_sem,
                "Receita": br_money(r_sem),
                "% Receita": br_percent(r_sem / receita_total * 100 if receita_total else 0),
            },
        ]
        st.dataframe(
            pd.DataFrame(breakdown_data),
            use_container_width=True,
            hide_index=True,
        )

        # --- Confiança ---
        if "match_confidence" in financial_df.columns:
            st.markdown("**Distribuição por confiança:**")
            conf_data = []
            for conf in ["ALTA", "MEDIA", "BAIXA"]:
                mask_c = financial_df["match_confidence"].fillna("BAIXA") == conf
                n_c = int(financial_df.loc[mask_c, "item_id"].nunique() if "item_id" in financial_df.columns else 0)
                r_c = float(financial_df.loc[mask_c, "receita"].sum() if "receita" in financial_df.columns else 0)
                conf_data.append({
                    "Confiança": conf,
                    "Itens": n_c,
                    "Receita": br_money(r_c),
                    "% Receita": br_percent(r_c / receita_total * 100 if receita_total else 0),
                })
            st.dataframe(pd.DataFrame(conf_data), use_container_width=True, hide_index=True)

        # --- MATCH_PROVAVEL: lista para revisao ---
        if n_prov > 0:
            st.markdown("**Itens MATCH_PROVAVEL — aguardando revisao manual:**")
            prov_rows = (
                financial_df[mt_col == "MATCH_PROVAVEL"]
                .drop_duplicates("item_id" if "item_id" in financial_df.columns else financial_df.columns[0])
                .copy()
            )
            display_cols = [c for c in [
                "item_id", "produto", "marca", "match_score",
                "matched_item_seconds", "match_confidence"
            ] if c in prov_rows.columns]
            if "receita" in prov_rows.columns:
                prov_summary = (
                    financial_df[mt_col == "MATCH_PROVAVEL"]
                    .groupby("item_id")["receita"]
                    .sum()
                    .reset_index()
                    .rename(columns={"receita": "receita_total"})
                )
                prov_rows = prov_rows[display_cols].merge(prov_summary, on="item_id", how="left")
                prov_rows["receita_total"] = prov_rows["receita_total"].map(br_money)
                prov_rows = prov_rows.sort_values("match_score", ascending=False)
            st.dataframe(prov_rows, use_container_width=True, hide_index=True, height=300)
            st.caption(
                "Para aprovar um MATCH_PROVAVEL: confirmar candidato, "
                "cadastrar item_id correto em parametros_financeiros_seconds.csv e regenerar a base."
            )


def commercial_costs_insight(financials: dict[str, object]) -> str:
    full_pct = float(financials.get("full_pct") or 0.0)
    impacto_pct = float(financials.get("impacto_comercial_total_pct") or 0.0)
    resultado_pct = float(financials.get("resultado_operacional_pct") or 0.0)
    devolucao_venda_pct = float(financials.get("devolucao_valor_venda_monitorado_pct") or 0.0)

    if bool(financials.get("ads_parcial_por_periodo")):
        return "Ads parcial nao entrou no calculo executivo."
    if full_pct >= 7:
        return "FULL representa custo elevado no periodo."
    if resultado_pct < 7 and full_pct >= 4:
        return "Margem pressionada por FULL."
    if devolucao_venda_pct >= 5 and not bool(financials.get("devolucao_custo_real_disponivel")):
        return "Devolucoes relevantes, mas sem custo real disponivel."
    if impacto_pct <= META_OPERACIONAL_TOTAL_PERCENTUAL:
        return "Custos operacionais comerciais sob controle no periodo."
    return "Custos operacionais comerciais exigem acompanhamento no periodo."


def render_commercial_costs_summary(financials: dict[str, object], title: str = "Custos Operacionais Comerciais") -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)

    ads_status = "Parcial" if bool(financials["ads_parcial_por_periodo"]) else "Considerado"
    devolucao_disponivel = bool(financials["devolucao_custo_real_disponivel"])
    cards = [
        {
            "label": "Ads",
            "percent": br_percent(financials["ads_pct"]),
            "value": br_money(financials["ads_value"]),
            "status": ads_status,
            "color": "#D97706" if ads_status == "Parcial" else "#0F766E",
        },
        {
            "label": "FULL",
            "percent": br_percent(financials["full_pct"]),
            "value": br_money(financials["full_value"]),
            "status": "Informativo",
            "color": "#2563EB",
        },
        {
            "label": "Devolucoes",
            "percent": br_percent(financials["devolucao_pct"]) if devolucao_disponivel else "N/D",
            "value": br_money(financials["devolucao_value"]) if devolucao_disponivel else "N/D",
            "status": "Considerado" if devolucao_disponivel else "Custo real indisponivel",
            "color": "#0F766E" if devolucao_disponivel else "#64748B",
        },
    ]

    cols = st.columns(3)
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card" style="border-top: 4px solid {card['color']};">
                    <div class="kpi-label">{html.escape(card['label'])}</div>
                    <div class="kpi-value">{html.escape(card['percent'])}</div>
                    <div style="font-size:.9rem;font-weight:750;margin-top:.25rem;">{html.escape(card['value'])}</div>
                    <div style="font-size:.78rem;color:rgba(125,125,125,.96);margin-top:.35rem;">Status: {html.escape(card['status'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-title">Insight Automatico</div>', unsafe_allow_html=True)
    st.info(commercial_costs_insight(financials))


def br_pp(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    numeric = float(value)
    sign = "+" if numeric > 0 else ""
    return f"{sign}{numeric:.2f} pp".replace(".", ",")


def efficiency_status_color(status: str) -> str:
    if "Acima" in status or "Penaliza" in status:
        return "#DC2626"
    if "Parcial" in status or "Informativo" in status or "N/D" in status:
        return "#D97706" if "Parcial" in status else "#64748B"
    return "#0F766E"


def operational_efficiency_rows(financials: dict[str, object]) -> list[dict[str, object]]:
    receita = float(financials["receita"] or 0.0)
    ads_partial = bool(financials["ads_parcial_por_periodo"])
    devolucao_real = bool(financials["devolucao_custo_real_disponivel"])
    outras_explicita = bool(financials["outras_taxas_explicita"])
    real_considerado = float(financials["impacto_comercial_total_pct"] or 0.0)
    meta_total = float(financials["meta_operacional_total_pct"] or 0.0)
    desvio_total = float(financials["desvio_operacional_pct"] or 0.0)
    excesso_pct = float(financials["excesso_operacional_pct"] or 0.0)

    def impact_from_pp(desvio_pp: float | None) -> float | None:
        return None if desvio_pp is None else receita * desvio_pp / 100

    def component(
        name: str,
        meta_pct: float | None,
        real_pct: float | None,
        status: str,
        considered: bool = False,
    ) -> dict[str, object]:
        desvio_pp = None if meta_pct is None or real_pct is None else real_pct - meta_pct
        return {
            "Componente": name,
            "Meta %": meta_pct,
            "Real %": real_pct,
            "Desvio pp": desvio_pp,
            "Impacto R$": impact_from_pp(desvio_pp),
            "Status": status,
            "considered": considered,
        }

    rows = [
        component(
            "Ads",
            float(financials["meta_operacional_ads_pct"] or 0.0),
            float(financials["ads_pct"] or 0.0),
            "Parcial - informativo" if ads_partial else "Considerado",
            considered=not ads_partial,
        ),
        component(
            "FULL",
            float(financials["meta_operacional_full_pct"] or 0.0),
            float(financials["full_pct"] or 0.0),
            "Informativo",
        ),
        component(
            "Devolucoes",
            float(financials["meta_operacional_devolucoes_pct"] or 0.0),
            float(financials["devolucao_valor_venda_monitorado_pct"] or 0.0),
            "Informativo" if not devolucao_real else "Informativo; tarifa real considerada no total",
            considered=devolucao_real,
        ),
        component(
            "Outras tarifas",
            float(financials["meta_operacional_outras_tarifas_pct"] or 0.0),
            float(financials["outras_taxas_pct"] or 0.0) if outras_explicita else None,
            "Considerado" if outras_explicita else "N/D - coluna explicita ausente",
            considered=outras_explicita,
        ),
        component(
            "Total Operacional Real",
            meta_total,
            real_considerado,
            "Acima da meta" if desvio_total > 0 else "Dentro da meta",
            considered=True,
        ),
        {
            "Componente": "Meta Operacional Total",
            "Meta %": meta_total,
            "Real %": meta_total,
            "Desvio pp": 0.0,
            "Impacto R$": receita * meta_total / 100,
            "Status": "Budget gerencial",
            "considered": False,
        },
        {
            "Componente": "Desvio Operacional",
            "Meta %": meta_total,
            "Real %": real_considerado,
            "Desvio pp": desvio_total,
            "Impacto R$": impact_from_pp(desvio_total),
            "Status": "Acima da meta" if desvio_total > 0 else "Dentro da meta",
            "considered": True,
        },
        {
            "Componente": "Impacto Financeiro do Desvio",
            "Meta %": 0.0,
            "Real %": excesso_pct,
            "Desvio pp": excesso_pct,
            "Impacto R$": float(financials["excesso_operacional_valor"] or 0.0),
            "Status": "Penaliza resultado" if excesso_pct > 0 else "Sem penalizacao",
            "considered": True,
        },
    ]
    return rows


def operational_efficiency_insights(financials: dict[str, object]) -> list[str]:
    real_pct = float(financials["impacto_comercial_total_pct"] or 0.0)
    desvio_pct = float(financials["desvio_operacional_pct"] or 0.0)
    excesso_valor = float(financials["excesso_operacional_valor"] or 0.0)
    insights: list[str] = []
    if real_pct > META_OPERACIONAL_TOTAL_PERCENTUAL:
        insights.append(
            "Custos operacionais comerciais estao acima da referencia em "
            f"{br_pp(desvio_pct)}, impacto estimado de {br_money(excesso_valor)}."
        )
    else:
        insights.append("Custos operacionais comerciais estao dentro da referencia de 5%.")
    if bool(financials["ads_parcial_por_periodo"]):
        insights.append("Ads esta parcial no periodo e foi exibido apenas como informativo.")
    insights.append(
        "FULL e devolucoes por valor de venda sao monitorados, mas nao descontados para evitar dupla contagem."
    )
    return insights


def render_operational_efficiency(financials: dict[str, object]) -> None:
    rows = operational_efficiency_rows(financials)
    html_rows: list[str] = []
    for row in rows:
        status = safe_text(row["Status"])
        color = efficiency_status_color(status)
        meta_text = br_percent(row["Meta %"], 2) if row["Meta %"] is not None else "N/D"
        real_text = br_percent(row["Real %"], 2) if row["Real %"] is not None else "N/D"
        desvio_text = br_pp(row["Desvio pp"]) if row["Desvio pp"] is not None else "N/D"
        impact_text = br_money(row["Impacto R$"]) if row["Impacto R$"] is not None else "N/D"
        html_rows.append(
            "<tr>"
            f"<td>{html.escape(safe_text(row['Componente']))}</td>"
            f"<td>{html.escape(meta_text)}</td>"
            f"<td>{html.escape(real_text)}</td>"
            f"<td>{html.escape(desvio_text)}</td>"
            f"<td>{html.escape(impact_text)}</td>"
            f'<td><span class="eff-badge" style="--eff-color:{color};">{html.escape(status)}</span></td>'
            "</tr>"
        )

    real_pct = float(financials["impacto_comercial_total_pct"] or 0.0)
    desvio_pct = float(financials["desvio_operacional_pct"] or 0.0)
    impacto_valor = float(financials["excesso_operacional_valor"] or 0.0)
    if real_pct > META_OPERACIONAL_TOTAL_PERCENTUAL:
        headline = (
            f"O custo operacional esta {br_pp(desvio_pct)} acima da meta, "
            f"consumindo {br_money(impacto_valor)} de margem."
        )
    else:
        headline = "O custo operacional comercial esta dentro da referencia de 5%."

    table_html = f"""
<style>
.eff-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 .38rem;
}}
.eff-table th {{
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: 0;
    color: rgba(148,163,184,.92);
    text-align: left;
    padding: 0 .72rem .1rem .72rem;
}}
.eff-table td {{
    border-top: 1px solid rgba(148,163,184,.16);
    border-bottom: 1px solid rgba(148,163,184,.16);
    padding: .68rem .72rem;
    background: rgba(15,23,42,.18);
    font-weight: 760;
}}
.eff-table td:first-child {{
    border-left: 1px solid rgba(148,163,184,.16);
    border-radius: 8px 0 0 8px;
}}
.eff-table td:last-child {{
    border-right: 1px solid rgba(148,163,184,.16);
    border-radius: 0 8px 8px 0;
}}
.eff-badge {{
    display: inline-flex;
    align-items: center;
    border: 1px solid color-mix(in srgb, var(--eff-color) 54%, transparent);
    color: var(--eff-color);
    background: color-mix(in srgb, var(--eff-color) 13%, transparent);
    border-radius: 999px;
    padding: .16rem .46rem;
    font-size: .68rem;
    font-weight: 850;
    white-space: nowrap;
}}
</style>
<div class="section-title">Eficiencia Operacional</div>
<table class="eff-table">
<thead>
<tr>
<th>Componente</th>
<th>Meta %</th>
<th>Real %</th>
<th>Desvio pp</th>
<th>Impacto R$</th>
<th>Status</th>
</tr>
</thead>
<tbody>{''.join(html_rows)}</tbody>
</table>
"""
    st.markdown(table_html.strip(), unsafe_allow_html=True)
    st.info(headline)
    st.markdown('<div class="section-title">Insight Automatico</div>', unsafe_allow_html=True)
    for insight in operational_efficiency_insights(financials):
        st.markdown(f"- {html.escape(insight)}")


def executive_financials_timeseries(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    period_column: str,
    ads_period_column: str = "ads_data_ref",
) -> pd.DataFrame:
    """Calcula o modelo executivo por periodo para evolucoes."""

    if financial_df.empty or period_column not in financial_df.columns:
        return pd.DataFrame()

    ads_work = ads_df.copy()
    if not ads_work.empty and ads_period_column in ads_work.columns:
        ads_work[ads_period_column] = pd.to_datetime(ads_work[ads_period_column], errors="coerce")

    rows: list[dict[str, object]] = []
    for period, group in financial_df.groupby(period_column, dropna=True):
        if pd.isna(period):
            continue
        if not ads_work.empty and ads_period_column in ads_work.columns:
            if period_column == "month":
                ads_period = ads_work[ads_work[ads_period_column].dt.to_period("M").astype(str) == str(period)]
            else:
                period_date = pd.to_datetime(period, errors="coerce")
                ads_period = ads_work[ads_work[ads_period_column].dt.date == period_date.date()] if pd.notna(period_date) else ads_work.iloc[0:0]
        else:
            ads_period = ads_work.iloc[0:0]
        metrics = calculate_executive_financials(group, ads_period)
        rows.append(
            {
                period_column: period,
                "receita": metrics["receita"],
                "cmv": metrics["cmv"],
                "comissao": metrics["comissao"],
                "frete": metrics["frete"],
                "impostos": metrics["impostos"],
                "custo_fixo": metrics["custo_fixo"],
                "margem_operacional_pct": metrics["margem_operacional_pct"],
                "ajuste_operacional_padrao_pct": metrics["ajuste_operacional_padrao_pct"],
                "impacto_comercial_total_pct": metrics["impacto_comercial_total_pct"],
                "custos_operacionais_comerciais_valor": metrics["custos_operacionais_comerciais_valor"],
                "custos_operacionais_comerciais_pct": metrics["custos_operacionais_comerciais_pct"],
                "resultado_operacional_pct": metrics["resultado_operacional_pct"],
                "resultado_operacional_valor": metrics["resultado_operacional_valor"],
                "ads_value": metrics["ads_value"],
                "ads_pct": metrics["ads_pct"],
                "full_pct": metrics["full_pct"],
                "devolucao_pct": metrics["devolucao_pct"],
                "outras_taxas_pct": metrics["outras_taxas_pct"],
                "pedidos": group["order_id"].nunique() if "order_id" in group.columns else len(group),
            }
        )
    return pd.DataFrame(rows).sort_values(period_column)


def percent_of_revenue(value: float, revenue: float) -> float:
    return (value / revenue * 100) if revenue else 0.0


def signed_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    numeric = float(value)
    prefix = "-" if numeric < 0 else ""
    return f"{prefix}{br_money(abs(numeric))}"


def dre_status(label: str, financials: dict[str, object]) -> str:
    if label == "Custos Operacionais Comerciais":
        return "Consolidado"
    if label == "Resultado Final da Margem":
        return {"saudavel": "Saudavel", "atencao": "Atencao", "risco": "Risco"}[
            result_operational_status(float(financials["resultado_operacional_pct"]))
        ]
    return "Base"


def build_dre_executiva(financials: dict[str, object]) -> pd.DataFrame:
    receita = float(financials["receita"] or 0.0)
    custos_operacionais_valor = float(financials["custos_operacionais_comerciais_valor"] or 0.0)
    rows = [
        ("Receita Bruta", receita, 100.0),
        ("(-) Comissao ML", -float(financials["comissao"] or 0.0), -percent_of_revenue(float(financials["comissao"] or 0.0), receita)),
        ("(-) CMV", -float(financials["cmv"] or 0.0), -percent_of_revenue(float(financials["cmv"] or 0.0), receita)),
        ("(-) Frete", -float(financials["frete"] or 0.0), -percent_of_revenue(float(financials["frete"] or 0.0), receita)),
        ("(-) Impostos", -float(financials["impostos"] or 0.0), -percent_of_revenue(float(financials["impostos"] or 0.0), receita)),
        ("(-) Rateio Operacional Seconds", -float(financials["custo_fixo"] or 0.0), -percent_of_revenue(float(financials["custo_fixo"] or 0.0), receita)),
        ("Resultado Base", float(financials["margem_operacional_valor"] or 0.0), float(financials["margem_operacional_pct"] or 0.0)),
        ("(-) Custos Operacionais Comerciais", -custos_operacionais_valor, -percent_of_revenue(custos_operacionais_valor, receita)),
        (
            "Resultado Final da Margem",
            float(financials["resultado_operacional_valor"] or 0.0),
            float(financials["resultado_operacional_pct"] or 0.0),
        ),
    ]
    return pd.DataFrame(
        [
            {
                "Indicador": label,
                "Valor R$": value,
                "% da Receita": percent,
                "Status": dre_status(label, financials),
            }
            for label, value, percent in rows
        ]
    )


def style_dre_executiva(df: pd.DataFrame):
    display = df.copy()
    display["Valor R$"] = display["Valor R$"].map(signed_money)
    display["% da Receita"] = display["% da Receita"].map(lambda value: br_percent(value, 2))

    def color_row(row: pd.Series) -> list[str]:
        indicator = safe_text(row.get("Indicador"))
        status = safe_text(row.get("Status"))
        if indicator == "Resultado Final da Margem":
            color = (
                "background-color: rgba(15, 118, 110, .24); color: #065F46; "
                "font-weight: 850; border-top: 2px solid rgba(15, 118, 110, .55); "
                "border-bottom: 2px solid rgba(15, 118, 110, .55);"
            )
        elif indicator == "Resultado Base":
            color = (
                "background-color: rgba(37, 99, 235, .18); color: #1D4ED8; "
                "font-weight: 850; border-top: 1px solid rgba(37, 99, 235, .38); "
                "border-bottom: 1px solid rgba(37, 99, 235, .38);"
            )
        elif indicator == "Receita Bruta":
            color = "background-color: rgba(37, 99, 235, .14); color: #1D4ED8; font-weight: 800;"
        elif "Parcial" in status:
            color = "background-color: rgba(217, 119, 6, .16); color: #92400E; font-weight: 700;"
        else:
            color = "background-color: rgba(220, 38, 38, .10); color: #991B1B; font-weight: 700;"
        return [color] * len(row)

    return display.style.apply(color_row, axis=1)


def render_dre_executiva(financials: dict[str, object]) -> None:
    dre = build_dre_executiva(financials)

    def dre_indicator_label(indicator: str) -> str:
        tooltip = DRE_TOOLTIPS.get(indicator)
        indicator_html = html.escape(indicator)
        if not tooltip:
            return indicator_html
        tooltip_html = html.escape(tooltip, quote=True)
        return (
            f'<span class="dre-tooltip" title="{tooltip_html}">'
            f"{indicator_html}"
            f'<span class="kpi-help" title="{tooltip_html}" aria-label="Explicacao da linha DRE">&#8505;</span>'
            f"</span>"
        )

    def row_visual(indicator: str, status: str, value: float) -> tuple[str, str, str]:
        if indicator == "Receita Bruta":
            return "#0F4C5C", "Receita", "dre-row-feature"
        if indicator == "Resultado Final da Margem":
            return financial_result_color(float(financials["resultado_operacional_pct"] or 0.0)), "Final", "dre-row-final"
        if indicator == "Resultado Base":
            return "#2563EB", "Resultado Base", "dre-row-base"
        if indicator == "(-) Custos Operacionais Comerciais":
            return "#D97706", "Comercial", ""
        if "Parcial" in status:
            return "#D97706", "Parcial", ""
        if value < 0:
            return "#DC2626", "Custo", ""
        return "#0F766E", "Base", ""

    rows: list[str] = []
    for _, row in dre.iterrows():
        indicator = safe_text(row.get("Indicador"))
        status = safe_text(row.get("Status"))
        value = float(row.get("Valor R$") or 0.0)
        percent = float(row.get("% da Receita") or 0.0)
        color, badge, feature_class = row_visual(indicator, status, value)
        bar_width = min(abs(percent), 100.0)
        rows.append(
            f'<tr class="{feature_class}">'
            "<td>"
            f'<div class="dre-indicator">{dre_indicator_label(indicator)}</div>'
            f'<span class="dre-badge" style="--dre-color:{color};">{html.escape(badge)}</span>'
            "</td>"
            f'<td class="dre-money">{html.escape(signed_money(value))}</td>'
            "<td>"
            '<div class="dre-percent-line">'
            f"<span>{html.escape(br_percent(percent, 2))}</span>"
            '<div class="dre-bar-track">'
            f'<div class="dre-bar-fill" style="width:{bar_width:.2f}%; --dre-color:{color};"></div>'
            "</div>"
            "</div>"
            "</td>"
            "</tr>"
        )

    dre_html = f"""
<style>
.dre-exec-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 .42rem;
}}
.dre-exec-table th {{
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: 0;
    color: rgba(148,163,184,.92);
    text-align: left;
    padding: 0 .85rem .15rem .85rem;
}}
.dre-exec-table td {{
    border-top: 1px solid rgba(148,163,184,.16);
    border-bottom: 1px solid rgba(148,163,184,.16);
    padding: .76rem .85rem;
    background: rgba(15,23,42,.22);
    vertical-align: middle;
}}
.dre-exec-table td:first-child {{
    border-left: 1px solid rgba(148,163,184,.16);
    border-radius: 8px 0 0 8px;
}}
.dre-exec-table td:last-child {{
    border-right: 1px solid rgba(148,163,184,.16);
    border-radius: 0 8px 8px 0;
}}
.dre-row-feature td {{
    background: rgba(15,76,92,.22);
    border-color: rgba(14,116,144,.34);
}}
.dre-row-base td {{
    background: rgba(37,99,235,.16);
    border-color: rgba(37,99,235,.32);
}}
.dre-row-final td {{
    background: rgba(15,118,110,.20);
    border-color: rgba(34,197,94,.40);
    box-shadow: inset 3px 0 0 rgba(34,197,94,.84);
}}
.dre-row-info td {{
    background: rgba(100,116,139,.12);
}}
.dre-indicator {{
    font-weight: 850;
    line-height: 1.15;
    margin-bottom: .35rem;
}}
.dre-tooltip {{
    display: inline-flex;
    align-items: center;
}}
.dre-badge {{
    display: inline-flex;
    align-items: center;
    border: 1px solid color-mix(in srgb, var(--dre-color) 54%, transparent);
    color: var(--dre-color);
    background: color-mix(in srgb, var(--dre-color) 13%, transparent);
    border-radius: 999px;
    padding: .16rem .46rem;
    font-size: .68rem;
    font-weight: 850;
    text-transform: uppercase;
}}
.dre-money {{
    font-weight: 850;
    white-space: nowrap;
}}
.dre-percent-line {{
    display: grid;
    grid-template-columns: 86px minmax(120px, 1fr);
    gap: .7rem;
    align-items: center;
    font-weight: 820;
}}
.dre-bar-track {{
    height: .48rem;
    border-radius: 999px;
    background: rgba(148,163,184,.18);
    overflow: hidden;
}}
.dre-bar-fill {{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, color-mix(in srgb, var(--dre-color) 72%, transparent), var(--dre-color));
}}
</style>
<div class="section-title">DRE Executiva</div>
<table class="dre-exec-table">
<thead>
<tr>
<th>Indicador</th>
<th>Valor R$</th>
<th>% da Receita</th>
</tr>
</thead>
<tbody>{''.join(rows)}</tbody>
</table>
"""
    st.markdown(dre_html.strip(), unsafe_allow_html=True)


def filter_financial_period(df: pd.DataFrame, period: tuple[date, date]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    start_date, end_date = period
    work = df.copy()
    if "data_ref" in work.columns:
        dates = pd.to_datetime(work["data_ref"], errors="coerce").dt.date
    elif "date" in work.columns:
        dates = pd.to_datetime(work["date"], errors="coerce").dt.date
    else:
        return work.iloc[0:0].copy()
    return work[(dates >= start_date) & (dates <= end_date)].copy()


def previous_period(selected_period: tuple[date, date] | None) -> tuple[date, date] | None:
    if not selected_period:
        return None
    start_date, end_date = selected_period
    days = max((end_date - start_date).days + 1, 1)
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start, prev_end


def financial_period_summary(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    period: tuple[date, date] | None,
    historical_ads_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    metrics = calculate_executive_financials(financial_df, ads_df, period, historical_ads_df)
    pedidos = int(financial_df["order_id"].nunique()) if "order_id" in financial_df.columns and not financial_df.empty else 0
    ticket = float(metrics["receita"]) / pedidos if pedidos else 0.0
    receita = float(metrics["receita"] or 0.0)
    return {
        **metrics,
        "pedidos": pedidos,
        "ticket_medio": ticket,
        "cmv_pct": percent_of_revenue(float(metrics["cmv"] or 0.0), receita),
        "frete_pct": percent_of_revenue(float(metrics["frete"] or 0.0), receita),
    }


def compare_delta(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current / previous - 1) * 100


def render_comparison_card(label: str, current_text: str, delta: float | None, higher_is_better: bool = True) -> None:
    if delta is None:
        color = "#64748B"
        delta_text = "N/D vs periodo anterior"
    else:
        improved = delta >= 0 if higher_is_better else delta <= 0
        color = "#0F766E" if improved else "#DC2626"
        sign = "+" if delta > 0 else ""
        arrow = "\u2191" if improved else "\u2193"
        delta_text = f"{arrow} {sign}{br_percent(delta)} vs periodo anterior"
    st.markdown(
        f"""
        <div class="kpi-card" style="border-top: 4px solid {color};">
            <div class="kpi-label">{html.escape(label)}</div>
            <div class="kpi-value">{html.escape(current_text)}</div>
            <div style="font-size:.82rem;color:{color};font-weight:800;margin-top:.45rem;">{html.escape(delta_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_comparativo_periodo(
    current_summary: dict[str, object],
    previous_summary: dict[str, object] | None,
) -> None:
    st.markdown('<div class="section-title">Comparativo do Periodo</div>', unsafe_allow_html=True)
    items = [
        ("Faturamento", "receita", br_money, True),
        ("Pedidos", "pedidos", lambda value: br_number(value, 0), True),
        ("Ticket Medio", "ticket_medio", br_money, True),
        ("Margem Base", "margem_operacional_pct", br_percent, True),
        ("Resultado Final da Margem", "resultado_operacional_pct", br_percent, True),
        ("CMV %", "cmv_pct", br_percent, False),
        ("Frete %", "frete_pct", br_percent, False),
        ("Ads %", "ads_pct", br_percent, False),
    ]
    for start in range(0, len(items), 4):
        cols = st.columns(4)
        for col, (label, key, formatter, higher_is_better) in zip(cols, items[start : start + 4]):
            current_value = float(current_summary.get(key) or 0.0)
            previous_value = float(previous_summary.get(key) or 0.0) if previous_summary else 0.0
            delta = compare_delta(current_value, previous_value) if previous_summary else None
            with col:
                render_comparison_card(label, formatter(current_value), delta, higher_is_better)


def prepare_financial_daily_series(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty or "date" not in daily.columns:
        return pd.DataFrame()
    work = daily.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date"]).sort_values("date")
    if work.empty:
        return pd.DataFrame()
    numeric_columns = [
        "receita",
        "resultado_operacional_valor",
        "pedidos",
        "cmv",
        "frete",
        "ads_value",
        "ads_pct",
    ]
    for column in numeric_columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0)
    if "receita" in work.columns:
        receita = work["receita"].replace(0, pd.NA)
        work["cmv_pct_calc"] = (work["cmv"] / receita * 100).fillna(0) if "cmv" in work.columns else 0.0
        work["frete_pct_calc"] = (work["frete"] / receita * 100).fillna(0) if "frete" in work.columns else 0.0
        if "ads_pct" not in work.columns and "ads_value" in work.columns:
            work["ads_pct"] = (work["ads_value"] / receita * 100).fillna(0)
    if len(work) >= 7:
        rolling_columns = [
            "receita",
            "resultado_operacional_valor",
            "pedidos",
            "cmv_pct_calc",
            "frete_pct_calc",
            "ads_pct",
        ]
        for column in rolling_columns:
            if column in work.columns:
                work[column] = work[column].rolling(3, min_periods=1).mean()
    return work


def financial_revenue_result_chart(daily: pd.DataFrame) -> go.Figure:
    work = prepare_financial_daily_series(daily)
    if work.empty:
        return empty_fig("Receita x Resultado")

    fig = go.Figure()
    series = {
        "Receita": ("receita", "#0F4C5C"),
        "Resultado Final": ("resultado_operacional_valor", "#22C55E"),
    }
    for label, (column, color) in series.items():
        if column not in work.columns:
            continue
        values = pd.to_numeric(work[column], errors="coerce").fillna(0)
        is_revenue = label == "Receita"
        fig.add_trace(
            go.Scatter(
                x=work["date"],
                y=values,
                mode="lines",
                name=label,
                line=dict(color=color, width=2.4 if is_revenue else 4.6, shape="spline"),
                fill="tozeroy" if is_revenue else None,
                fillcolor="rgba(15, 76, 92, .18)" if is_revenue else None,
                hovertemplate=f"{label}: %{{customdata}}<extra></extra>",
                customdata=values.map(br_money),
            )
        )
    if "pedidos" in work.columns:
        pedidos = pd.to_numeric(work["pedidos"], errors="coerce").fillna(0)
        fig.add_trace(
            go.Scatter(
                x=work["date"],
                y=pedidos,
                mode="lines",
                name="Pedidos",
                opacity=.62,
                line=dict(color="#94A3B8", width=1.5, dash="dot", shape="spline"),
                yaxis="y2",
                hovertemplate="Pedidos: %{customdata}<extra></extra>",
                customdata=pedidos.map(lambda value: br_number(value, 0)),
            )
        )
    fig.update_layout(
        title=dict(text="Receita x Resultado", x=0.01, xanchor="left", font=dict(size=15)),
        height=380,
        margin=dict(l=20, r=20, t=44, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title=None, tickfont=dict(color="#94A3B8")),
        font=dict(family="Inter, Segoe UI, Arial", size=12),
    )
    fig.update_xaxes(showgrid=False, tickformat="%d/%m")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.18)", zeroline=False, title=None)
    return fig


def financial_cost_pressure_chart(daily: pd.DataFrame) -> go.Figure:
    work = prepare_financial_daily_series(daily)
    if work.empty:
        return empty_fig("Pressao de Custos")

    fig = go.Figure()
    series = {
        "CMV %": ("cmv_pct_calc", "#DC2626"),
        "Frete %": ("frete_pct_calc", "#F97316"),
        "Ads %": ("ads_pct", "#7C3AED"),
    }
    for label, (column, color) in series.items():
        if column not in work.columns:
            continue
        values = pd.to_numeric(work[column], errors="coerce").fillna(0)
        fig.add_trace(
            go.Scatter(
                x=work["date"],
                y=values,
                mode="lines",
                name=label,
                line=dict(color=color, width=3, shape="spline"),
                hovertemplate=f"{label}: %{{customdata}}<extra></extra>",
                customdata=values.map(lambda value: br_percent(value, 2)),
            )
        )
    targets = [
        ("Meta CMV 45%", 45, "#DC2626"),
        ("Meta Frete 8%", 8, "#F97316"),
        ("Meta Ads 3%", META_OPERACIONAL_ADS_PERCENTUAL, "#7C3AED"),
    ]
    for label, target, color in targets:
        fig.add_hline(
            y=target,
            line_dash="dash",
            line_color=color,
            opacity=.48,
            annotation_text=label,
            annotation_position="top right",
            annotation_font=dict(size=10, color=color),
        )
    fig.update_layout(
        title=dict(text="Pressao de Custos", x=0.01, xanchor="left", font=dict(size=15)),
        height=360,
        margin=dict(l=20, r=20, t=44, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, Segoe UI, Arial", size=12),
    )
    fig.update_xaxes(showgrid=False, tickformat="%d/%m")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.18)", zeroline=False, title=None, ticksuffix="%")
    return fig


def financial_result_color(result_pct: float) -> str:
    if result_pct > 12:
        return "#0F766E"
    if result_pct >= 7:
        return "#D97706"
    return "#DC2626"


def render_horizontal_financial_funnel(financials: dict[str, object]) -> None:
    receita = float(financials["receita"] or 0.0)
    result_pct = float(financials["resultado_operacional_pct"] or 0.0)
    result_color = financial_result_color(result_pct)
    steps = [
        {
            "label": "Receita",
            "value": receita,
            "pct": 100.0 if receita else 0.0,
            "impact": "Base de faturamento",
            "color": "#0F4C5C",
            "kind": "positive",
        },
        {
            "label": "Comissao",
            "value": -float(financials["comissao"] or 0.0),
            "pct": -percent_of_revenue(float(financials["comissao"] or 0.0), receita),
            "impact": "Custo de venda",
            "color": "#DC2626",
            "kind": "cost",
        },
        {
            "label": "CMV",
            "value": -float(financials["cmv"] or 0.0),
            "pct": -percent_of_revenue(float(financials["cmv"] or 0.0), receita),
            "impact": "Custo do produto",
            "color": "#DC2626",
            "kind": "cost",
        },
        {
            "label": "Frete",
            "value": -float(financials["frete"] or 0.0),
            "pct": -percent_of_revenue(float(financials["frete"] or 0.0), receita),
            "impact": "Pressao operacional",
            "color": "#DC2626",
            "kind": "cost",
        },
        {
            "label": "Impostos",
            "value": -float(financials["impostos"] or 0.0),
            "pct": -percent_of_revenue(float(financials["impostos"] or 0.0), receita),
            "impact": "Carga tributaria",
            "color": "#DC2626",
            "kind": "cost",
        },
        {
            "label": "Resultado Final",
            "value": float(financials["resultado_operacional_valor"] or 0.0),
            "pct": result_pct,
            "impact": "Saudavel" if result_pct > 12 else "Atencao" if result_pct >= 7 else "Risco",
            "color": result_color,
            "kind": "result",
        },
    ]
    cards: list[str] = []
    for index, step in enumerate(steps):
        pct_abs = min(abs(float(step["pct"])), 100.0)
        grow = 1.0 + pct_abs / 25.0
        arrow = '<div class="finance-funnel-arrow">&rarr;</div>' if index < len(steps) - 1 else ""
        cards.append(
            f'<div class="finance-funnel-card finance-funnel-{step["kind"]}" style="--funnel-color:{step["color"]}; --funnel-grow:{grow:.2f};">'
            f'<div class="finance-funnel-label">{html.escape(step["label"])}</div>'
            f'<div class="finance-funnel-value">{html.escape(signed_money(float(step["value"])))}</div>'
            '<div class="finance-funnel-meta">'
            f'<span>{html.escape(br_percent(float(step["pct"]), 2))}</span>'
            f'<span>{html.escape(step["impact"])}</span>'
            "</div>"
            "</div>"
            f"{arrow}"
        )
    funnel_html = f"""
<style>
.finance-funnel-wrap {{
    display: flex;
    gap: .58rem;
    align-items: stretch;
    overflow-x: auto;
    padding: .12rem .05rem .86rem .05rem;
    margin-bottom: .8rem;
}}
.finance-funnel-card {{
    min-width: 138px;
    flex: var(--funnel-grow) 1 138px;
    border: 1px solid rgba(148,163,184,.18);
    border-left: 4px solid var(--funnel-color);
    border-radius: 8px;
    padding: .86rem .9rem;
    background: linear-gradient(180deg, color-mix(in srgb, var(--funnel-color) 13%, transparent), rgba(15,23,42,.12));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
}}
.finance-funnel-cost {{
    background: linear-gradient(180deg, rgba(220,38,38,.13), rgba(15,23,42,.12));
}}
.finance-funnel-result {{
    background: linear-gradient(180deg, color-mix(in srgb, var(--funnel-color) 17%, transparent), rgba(15,23,42,.12));
}}
.finance-funnel-label {{
    font-size: .72rem;
    text-transform: uppercase;
    color: rgba(148,163,184,.96);
    font-weight: 880;
    margin-bottom: .5rem;
}}
.finance-funnel-value {{
    color: var(--funnel-color);
    font-size: clamp(1rem, 1.1vw, 1.28rem);
    line-height: 1.1;
    font-weight: 900;
    word-break: break-word;
}}
.finance-funnel-meta {{
    margin-top: .55rem;
    display: flex;
    flex-direction: column;
    gap: .18rem;
    color: rgba(148,163,184,.96);
    font-size: .76rem;
    font-weight: 780;
}}
.finance-funnel-arrow {{
    display: flex;
    align-items: center;
    color: rgba(148,163,184,.62);
    font-size: 1.14rem;
    font-weight: 900;
    flex: 0 0 auto;
}}
</style>
<div class="section-title">Como a Receita vira Resultado</div>
<div class="finance-funnel-wrap">
{''.join(cards)}
</div>
"""
    st.markdown(funnel_html.strip(), unsafe_allow_html=True)


def format_pp_delta(current: float, target: float, lower_is_better: bool = False) -> str:
    diff = current - target
    if lower_is_better:
        if diff > 0:
            return f"Acima da meta: +{br_number(diff, 2)}pp"
        return f"Folga: {br_number(abs(diff), 2)}pp"
    if diff >= 0:
        return f"Acima da meta: +{br_number(diff, 2)}pp"
    return f"Faltam: {br_number(abs(diff), 2)}pp"


def status_card(label: str, value: str, status: str, reference: str, difference: str) -> None:
    colors = {"verde": "#0F766E", "amarelo": "#D97706", "vermelho": "#DC2626", "cinza": "#64748B"}
    color = colors.get(status, "#64748B")
    st.markdown(
        f"""
        <div class="kpi-card" style="border-top: 4px solid {color};">
            <div class="kpi-label">{html.escape(label)}</div>
            <div class="kpi-value">{html.escape(value)}</div>
            <div style="font-size:.78rem;color:rgba(125,125,125,.96);font-weight:750;margin-top:.45rem;">{html.escape(reference)}</div>
            <div style="font-size:.82rem;color:{color};font-weight:850;margin-top:.28rem;">{html.escape(difference)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def historical_cmv_pct(financial_base: pd.DataFrame | None) -> float | None:
    if financial_base is None or financial_base.empty:
        return None
    metrics = calculate_executive_financials(financial_base, pd.DataFrame())
    receita = float(metrics["receita"] or 0.0)
    return percent_of_revenue(float(metrics["cmv"] or 0.0), receita) if receita else None


def render_saude_financeira(
    current: dict[str, object],
    previous: dict[str, object] | None,
    financial_base: pd.DataFrame | None,
) -> None:
    st.markdown('<div class="section-title">Saude Financeira</div>', unsafe_allow_html=True)
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    result_status = "verde" if result_pct > 12 else "amarelo" if result_pct >= 7 else "vermelho"

    cmv_pct = float(current["cmv_pct"] or 0.0)
    hist_cmv = historical_cmv_pct(financial_base)
    if hist_cmv is None:
        cmv_status, cmv_detail = "cinza", "Sem media historica"
        cmv_diff = "Referencia indisponivel"
    elif cmv_pct <= hist_cmv * 0.95:
        cmv_status, cmv_detail = "verde", f"Abaixo da media historica ({br_percent(hist_cmv)})"
        cmv_diff = f"Abaixo da media: {br_number(abs(cmv_pct - hist_cmv), 2)}pp"
    elif cmv_pct <= hist_cmv * 1.05:
        cmv_status, cmv_detail = "amarelo", f"Proximo da media historica ({br_percent(hist_cmv)})"
        cmv_diff = f"Variacao: {br_number(cmv_pct - hist_cmv, 2)}pp"
    else:
        cmv_status, cmv_detail = "vermelho", f"Acima da media historica ({br_percent(hist_cmv)})"
        cmv_diff = f"Acima da media: +{br_number(cmv_pct - hist_cmv, 2)}pp"

    frete_pct = float(current["frete_pct"] or 0.0)
    frete_status = "verde" if frete_pct <= 8 else "amarelo" if frete_pct <= 12 else "vermelho"
    frete_diff = format_pp_delta(frete_pct, 8.0, lower_is_better=True)

    ads_pct = float(current["ads_pct"] or 0.0)
    if bool(current["ads_parcial_por_periodo"]):
        ads_status, ads_detail, ads_diff = "amarelo", "Periodo de Ads parcial", "Nao entra no resultado gerencial"
    elif ads_pct <= META_OPERACIONAL_ADS_PERCENTUAL:
        ads_status, ads_detail, ads_diff = "verde", "Meta: ate 3%", format_pp_delta(ads_pct, META_OPERACIONAL_ADS_PERCENTUAL, lower_is_better=True)
    elif ads_pct <= 5:
        ads_status, ads_detail, ads_diff = "amarelo", "Meta: ate 3%", format_pp_delta(ads_pct, META_OPERACIONAL_ADS_PERCENTUAL, lower_is_better=True)
    else:
        ads_status, ads_detail, ads_diff = "vermelho", "Meta: ate 3%", format_pp_delta(ads_pct, META_OPERACIONAL_ADS_PERCENTUAL, lower_is_better=True)

    ticket_delta = (
        compare_delta(float(current["ticket_medio"] or 0.0), float(previous["ticket_medio"] or 0.0))
        if previous
        else None
    )
    if ticket_delta is None:
        ticket_status, ticket_detail, ticket_diff = "cinza", "Referencia: periodo anterior", "Periodo anterior indisponivel"
    elif ticket_delta >= 0:
        ticket_status = "verde"
        ticket_detail = f"Referencia: {br_money(float(previous['ticket_medio'] or 0.0))}"
        ticket_diff = f"Subiu {br_percent(ticket_delta)}"
    else:
        ticket_status = "vermelho"
        ticket_detail = f"Referencia: {br_money(float(previous['ticket_medio'] or 0.0))}"
        ticket_diff = f"Caiu {br_percent(abs(ticket_delta))}"

    cards = [
        (
            "Resultado Final da Margem",
            br_percent(result_pct),
            result_status,
            "Meta verde: acima de 12%",
            format_pp_delta(result_pct, 12.0),
        ),
        ("CMV %", br_percent(cmv_pct), cmv_status, cmv_detail, cmv_diff),
        ("Frete %", br_percent(frete_pct), frete_status, "Meta: ate 8%", frete_diff),
        ("Ads %", br_percent(ads_pct), ads_status, ads_detail, ads_diff),
        (
            "Ticket Medio",
            br_money(float(current["ticket_medio"] or 0.0)),
            ticket_status,
            ticket_detail,
            ticket_diff,
        ),
    ]
    cols = st.columns(5)
    for col, (label, value, status, reference, difference) in zip(cols, cards):
        with col:
            status_card(label, value, status, reference, difference)


def financial_insights(current: dict[str, object], previous: dict[str, object] | None) -> list[str]:
    insights: list[str] = []
    frete_pct = float(current["frete_pct"] or 0.0)
    cmv_pct = float(current["cmv_pct"] or 0.0)
    ads_pct = float(current["ads_pct"] or 0.0)
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    costs = {
        "CMV": float(current["cmv"] or 0.0),
        "Frete": float(current["frete"] or 0.0),
        "Comissao ML": float(current["comissao"] or 0.0),
        "Impostos": float(current["impostos"] or 0.0),
        "Rateio Operacional Seconds": float(current["custo_fixo"] or 0.0),
    }
    if frete_pct > 12:
        insights.append(f"Frete representa {br_percent(frete_pct)} do faturamento e esta pressionando a margem.")
    if costs and max(costs.values()) > 0:
        biggest = max(costs, key=costs.get)
        insights.append(f"{biggest} e o maior componente de custo do periodo.")
    if bool(current["ads_parcial_por_periodo"]):
        insights.append("Ads esta parcial no periodo selecionado e foi reconstruido por media temporal.")
    elif ads_pct > META_OPERACIONAL_ADS_PERCENTUAL:
        insights.append(f"Ads representa {br_percent(ads_pct)} do faturamento e esta acima da meta.")
    if result_pct < 7:
        insights.append("Resultado Final da Margem esta abaixo da meta de 7%.")
    if cmv_pct > 45:
        insights.append(f"CMV consome {br_percent(cmv_pct)} do faturamento e merece revisao de custo/preco.")
    if previous:
        ticket_delta = compare_delta(float(current["ticket_medio"] or 0.0), float(previous["ticket_medio"] or 0.0))
        if ticket_delta is not None:
            verb = "subiu" if ticket_delta >= 0 else "caiu"
            insights.append(f"Ticket medio {verb} {br_percent(abs(ticket_delta))} vs periodo anterior.")
    if not insights:
        insights.append("Indicadores financeiros estao sem alerta relevante para o periodo selecionado.")
    return insights[:5]


def financial_diagnostics(current: dict[str, object], previous: dict[str, object] | None) -> list[dict[str, str]]:
    receita = float(current["receita"] or 0.0)
    frete_pct = float(current["frete_pct"] or 0.0)
    cmv_pct = float(current["cmv_pct"] or 0.0)
    ads_pct = float(current["ads_pct"] or 0.0)
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    diagnostics: list[dict[str, str]] = []

    if result_pct < 7:
        gap = max(7 - result_pct, 0) * receita / 100
        diagnostics.append(
            {
                "criticidade": "Critica",
                "tema": "Resultado final abaixo da meta minima",
                "impacto": br_money(gap),
                "recomendacao": "Priorizar revisao de CMV, frete, comissao e campanhas antes de escalar vendas.",
                "color": "#DC2626",
            }
        )
    elif result_pct < 12:
        gap = max(12 - result_pct, 0) * receita / 100
        diagnostics.append(
            {
                "criticidade": "Atencao",
                "tema": "Resultado final ainda abaixo da faixa verde",
                "impacto": br_money(gap),
                "recomendacao": "Buscar ganho incremental em precificacao, frete e mix de produtos.",
                "color": "#D97706",
            }
        )

    if cmv_pct > 45:
        excess = max(cmv_pct - 45, 0) * receita / 100
        diagnostics.append(
            {
                "criticidade": "Alta",
                "tema": f"CMV em {br_percent(cmv_pct)} da receita",
                "impacto": br_money(excess),
                "recomendacao": "Revisar custos de compra, kits, precificacao e margem minima por produto.",
                "color": "#DC2626",
            }
        )

    if frete_pct > 8:
        excess = max(frete_pct - 8, 0) * receita / 100
        diagnostics.append(
            {
                "criticidade": "Alta" if frete_pct > 12 else "Media",
                "tema": f"Frete acima da referencia ({br_percent(frete_pct)})",
                "impacto": br_money(excess),
                "recomendacao": "Avaliar FULL, regioes, politica de envio e itens com frete desproporcional.",
                "color": "#DC2626" if frete_pct > 12 else "#D97706",
            }
        )

    if bool(current["ads_parcial_por_periodo"]):
        diagnostics.append(
            {
                "criticidade": "Atencao",
                "tema": "Ads parcial no periodo selecionado",
                "impacto": "N/D",
                "recomendacao": "Comparar Ads apenas em periodos compativeis antes de tomar decisao de corte ou escala.",
                "color": "#D97706",
            }
        )
    elif ads_pct > 5:
        excess = max(ads_pct - 5, 0) * receita / 100
        diagnostics.append(
            {
                "criticidade": "Media" if ads_pct <= 10 else "Alta",
                "tema": f"Ads acima da meta ({br_percent(ads_pct)})",
                "impacto": br_money(excess),
                "recomendacao": "Revisar campanhas com baixo retorno e concentrar verba em produtos rentaveis.",
                "color": "#D97706" if ads_pct <= 10 else "#DC2626",
            }
        )

    costs = {
        "CMV": float(current["cmv"] or 0.0),
        "Frete": float(current["frete"] or 0.0),
        "Comissao ML": float(current["comissao"] or 0.0),
        "Impostos": float(current["impostos"] or 0.0),
        "Rateio Operacional Seconds": float(current["custo_fixo"] or 0.0),
    }
    if costs and max(costs.values()) > 0:
        biggest = max(costs, key=costs.get)
        diagnostics.append(
            {
                "criticidade": "Informativo",
                "tema": f"{biggest} e o maior componente de custo",
                "impacto": br_money(costs[biggest]),
                "recomendacao": "Usar este componente como primeira alavanca de controladoria do periodo.",
                "color": "#64748B",
            }
        )

    if previous:
        ticket_delta = compare_delta(float(current["ticket_medio"] or 0.0), float(previous["ticket_medio"] or 0.0))
        if ticket_delta is not None and ticket_delta < 0:
            ticket_gap = abs(float(current["ticket_medio"] or 0.0) - float(previous["ticket_medio"] or 0.0)) * float(current["pedidos"] or 0.0)
            diagnostics.append(
                {
                    "criticidade": "Media",
                    "tema": f"Ticket medio caiu {br_percent(abs(ticket_delta))}",
                    "impacto": br_money(ticket_gap),
                    "recomendacao": "Revisar mix, bundles e exposicao dos itens de maior valor agregado.",
                    "color": "#D97706",
                }
            )

    if not diagnostics:
        diagnostics.append(
            {
                "criticidade": "Saudavel",
                "tema": "Sem alerta financeiro relevante no periodo",
                "impacto": "N/D",
                "recomendacao": "Manter acompanhamento e preservar disciplina de margem.",
                "color": "#0F766E",
            }
        )
    return diagnostics[:5]


def render_financial_insights(current: dict[str, object], previous: dict[str, object] | None) -> None:
    cards = []
    for item in financial_diagnostics(current, previous):
        cards.append(
            f'<div class="finance-diagnostic-card" style="--diag-color:{item["color"]};">'
            '<div class="finance-diagnostic-top">'
            f'<span class="finance-diagnostic-badge">{html.escape(item["criticidade"])}</span>'
            f'<span class="finance-diagnostic-impact">Impacto: {html.escape(item["impacto"])}</span>'
            "</div>"
            f'<div class="finance-diagnostic-title">{html.escape(item["tema"])}</div>'
            f'<div class="finance-diagnostic-rec">{html.escape(item["recomendacao"])}</div>'
            "</div>"
        )
    diagnostic_html = f"""
<style>
.finance-diagnostic-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
    gap: .75rem;
    margin-bottom: .8rem;
}}
.finance-diagnostic-card {{
    border: 1px solid rgba(148,163,184,.18);
    border-left: 4px solid var(--diag-color);
    border-radius: 8px;
    padding: .9rem .95rem;
    background: linear-gradient(180deg, color-mix(in srgb, var(--diag-color) 10%, transparent), rgba(15,23,42,.12));
    min-height: 142px;
}}
.finance-diagnostic-top {{
    display: flex;
    justify-content: space-between;
    gap: .7rem;
    align-items: center;
    margin-bottom: .65rem;
}}
.finance-diagnostic-badge {{
    display: inline-flex;
    border: 1px solid color-mix(in srgb, var(--diag-color) 58%, transparent);
    color: var(--diag-color);
    background: color-mix(in srgb, var(--diag-color) 12%, transparent);
    border-radius: 999px;
    padding: .16rem .48rem;
    font-size: .68rem;
    font-weight: 900;
    text-transform: uppercase;
}}
.finance-diagnostic-impact {{
    color: rgba(148,163,184,.96);
    font-size: .76rem;
    font-weight: 820;
    text-align: right;
}}
.finance-diagnostic-title {{
    color: var(--diag-color);
    font-size: .98rem;
    line-height: 1.22;
    font-weight: 890;
    margin-bottom: .48rem;
}}
.finance-diagnostic-rec {{
    color: rgba(148,163,184,.98);
    font-size: .83rem;
    line-height: 1.38;
    font-weight: 650;
}}
</style>
<div class="section-title">Diagnostico Financeiro Automatico</div>
<div class="finance-diagnostic-grid">
{''.join(cards)}
</div>
"""
    st.markdown(diagnostic_html.strip(), unsafe_allow_html=True)


def bounded_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def score_from_thresholds(value: float, thresholds: list[tuple[float, float]], lower_is_better: bool = False) -> float:
    ordered = sorted(thresholds, key=lambda item: item[0], reverse=not lower_is_better)
    for threshold, score in ordered:
        if lower_is_better and value <= threshold:
            return score
        if not lower_is_better and value >= threshold:
            return score
    return thresholds[-1][1] if thresholds else 50.0


def delta_direction_score(delta: float | None) -> float:
    if delta is None:
        return 60.0
    if delta >= 12:
        return 100.0
    if delta >= 3:
        return 82.0
    if delta >= -3:
        return 65.0
    if delta >= -10:
        return 38.0
    return 15.0


def financial_health_score(
    current: dict[str, object],
    previous: dict[str, object] | None,
) -> dict[str, object]:
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    cmv_pct = float(current["cmv_pct"] or 0.0)
    frete_pct = float(current["frete_pct"] or 0.0)
    ads_pct = float(current["ads_pct"] or 0.0)
    growth_delta = (
        compare_delta(float(current["receita"] or 0.0), float(previous["receita"] or 0.0))
        if previous
        else None
    )
    ticket_delta = (
        compare_delta(float(current["ticket_medio"] or 0.0), float(previous["ticket_medio"] or 0.0))
        if previous
        else None
    )
    components = {
        "Resultado Final": score_from_thresholds(result_pct, [(15, 100), (12, 88), (7, 62), (0, 28), (-999, 8)]),
        "CMV": score_from_thresholds(cmv_pct, [(40, 100), (45, 82), (50, 50), (999, 18)], lower_is_better=True),
        "Frete": score_from_thresholds(frete_pct, [(8, 100), (12, 68), (16, 36), (999, 14)], lower_is_better=True),
        "Ads": 62.0
        if bool(current["ads_parcial_por_periodo"])
        else score_from_thresholds(ads_pct, [(3, 100), (5, 78), (8, 52), (999, 20)], lower_is_better=True),
        "Crescimento": delta_direction_score(growth_delta),
        "Ticket Medio": delta_direction_score(ticket_delta),
    }
    weights = {
        "Resultado Final": 0.30,
        "CMV": 0.20,
        "Frete": 0.15,
        "Ads": 0.10,
        "Crescimento": 0.15,
        "Ticket Medio": 0.10,
    }
    score = bounded_score(sum(components[key] * weights[key] for key in weights))
    if score >= 85:
        status, color = "Excelente", "#22C55E"
    elif score >= 70:
        status, color = "Saudavel", "#0F766E"
    elif score >= 50:
        status, color = "Atencao", "#D97706"
    else:
        status, color = "Critico", "#DC2626"
    return {"score": score, "status": status, "color": color, "components": components}


def financial_health_gauge(score_info: dict[str, object]) -> go.Figure:
    score = float(score_info["score"])
    color = str(score_info["color"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34, "color": color}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(148,163,184,.35)"},
                "bar": {"color": color, "thickness": .28},
                "bgcolor": "rgba(15,23,42,.16)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "rgba(220,38,38,.18)"},
                    {"range": [50, 70], "color": "rgba(217,119,6,.18)"},
                    {"range": [70, 85], "color": "rgba(15,118,110,.16)"},
                    {"range": [85, 100], "color": "rgba(34,197,94,.20)"},
                ],
                "threshold": {"line": {"color": color, "width": 4}, "thickness": .78, "value": score},
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=8, r=8, t=16, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
    )
    return fig


def selected_period_day_count(selected_period: tuple[date, date] | None, fallback_days: int = 1) -> int:
    if not selected_period:
        return max(fallback_days, 1)
    start_date, end_date = selected_period
    return max((end_date - start_date).days + 1, 1)


def projection_month_days(selected_period: tuple[date, date] | None) -> int:
    if not selected_period:
        return 30
    end_date = selected_period[1]
    return int(pd.Timestamp(end_date).days_in_month)


def projection_elapsed_month_days(selected_period: tuple[date, date] | None, daily: pd.DataFrame) -> int:
    if selected_period:
        end_date = selected_period[1]
        return max(1, min(int(end_date.day), projection_month_days(selected_period)))
    if not daily.empty and "date" in daily.columns:
        dates = pd.to_datetime(daily["date"], errors="coerce").dropna()
        if not dates.empty:
            return max(1, min(int(dates.max().day), int(dates.max().days_in_month)))
    return 1


def projection_confidence(elapsed_days: float, month_days: float) -> dict[str, str]:
    ratio = (elapsed_days / month_days) if month_days else 0.0
    if ratio >= 0.75:
        return {"label": "Alta", "color": "#0F766E"}
    if ratio >= 0.40:
        return {"label": "Media", "color": "#D97706"}
    return {"label": "Baixa", "color": "#EA580C"}


def build_month_projection(
    current: dict[str, object],
    selected_period: tuple[date, date] | None,
    daily: pd.DataFrame,
) -> dict[str, float]:
    month_days = projection_month_days(selected_period)
    elapsed_days = projection_elapsed_month_days(selected_period, daily)
    factor = month_days / elapsed_days if elapsed_days else 1.0
    receita = float(current["receita"] or 0.0)
    pedidos = float(current["pedidos"] or 0.0)
    resultado = float(current["resultado_operacional_valor"] or 0.0)
    projected_receita = receita * factor
    projected_result = resultado * factor
    projected_margin = percent_of_revenue(projected_result, projected_receita)
    return {
        "elapsed_days": float(elapsed_days),
        "month_days": float(month_days),
        "factor": float(factor),
        "receita": projected_receita,
        "pedidos": pedidos * factor,
        "resultado": projected_result,
        "margem": projected_margin,
        "impacto_receita": projected_receita - receita,
        "impacto_resultado": projected_result - resultado,
    }


def signed_br_number(value: float | int | None, decimals: int = 0, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/D"
    numeric = float(value)
    prefix = "+" if numeric > 0 else ""
    return f"{prefix}{br_number(numeric, decimals)}{suffix}"


def projection_comparison_text(
    label: str,
    projected: float,
    previous: dict[str, object] | None,
    key: str | None = None,
    formatter=br_money,
    target: float | None = None,
    suffix: str = "",
) -> str:
    if target is not None:
        diff = projected - target
        if suffix:
            return f"Diferenca para meta: {signed_br_number(diff, 2, suffix)}"
        return f"Diferenca para meta: {signed_money(diff)}"
    if previous and key:
        previous_value = float(previous.get(key) or 0.0)
        diff = projected - previous_value
        if formatter == br_number:
            return f"Vs periodo anterior: {signed_br_number(diff, 0, suffix)}"
        return f"Vs periodo anterior: {signed_money(diff)}"
    return "Sem meta configurada"


def projection_trend_text(daily: pd.DataFrame, selected_period: tuple[date, date] | None) -> dict[str, str]:
    work = prepare_financial_daily_series(daily)
    if work.empty or "date" not in work.columns or "receita" not in work.columns:
        return {"text": "Tendencia da projecao indisponivel", "color": "#64748B"}
    work = work.sort_values("date")
    if len(work) < 14:
        return {"text": "Tendencia da projecao indisponivel", "color": "#64748B"}
    month_days = projection_month_days(selected_period)
    receita = pd.to_numeric(work["receita"], errors="coerce").fillna(0)
    current_projection = float(receita.tail(7).mean()) * month_days
    previous_projection = float(receita.iloc[-14:-7].mean()) * month_days
    delta = compare_delta(current_projection, previous_projection)
    if delta is None:
        return {"text": "Tendencia da projecao indisponivel", "color": "#64748B"}
    sign = "+" if delta >= 0 else ""
    if delta >= 0:
        return {"text": f"Projecao melhorou {sign}{br_percent(delta)} nos ultimos 7 dias", "color": "#0F766E"}
    return {"text": f"Projecao piorou {br_percent(delta)} nos ultimos 7 dias", "color": "#DC2626"}


def render_projection_card(
    label: str,
    value: str,
    base_text: str,
    comparison_text: str,
    confidence_label: str,
    color: str,
) -> str:
    return (
        f'<div class="finance-projection-card" style="--projection-color:{color};">'
        f'<div class="finance-projection-label">{html.escape(label)}</div>'
        f'<div class="finance-projection-value">{html.escape(value)}</div>'
        f'<div class="finance-projection-base">{html.escape(base_text)}</div>'
        f'<div class="finance-projection-comparison">{html.escape(comparison_text)}</div>'
        f'<div class="finance-projection-confidence">Confianca: <span>{html.escape(confidence_label)}</span></div>'
        "</div>"
    )


def render_abrupt_dropoffs_methodology() -> None:
    """Documenta a regra atual do ranking sem alterar o calculo."""

    st.info(
        "Produtos com queda relevante de faturamento comparando os últimos 7 dias contra o histórico recente, "
        "ordenados pelo impacto financeiro estimado."
    )
    method_lines = [
        "**Janela analisada:** a data de referência é a maior data de venda disponível no período filtrado. "
        "Os últimos 7 dias vão dessa data menos 6 dias até a data de referência. O histórico recente considera "
        "os 30 dias imediatamente anteriores a essa janela.",
        "**Fórmula da queda:** média diária dos 30 dias anteriores = faturamento_30d_anteriores / 30; "
        "média diária dos últimos 7 dias = faturamento_ultimos_7d / 7; "
        "queda_percentual = (média_30d - média_7d) / média_30d * 100.",
        "**Impacto financeiro estimado:** impacto_faturamento_perdido = (média_30d - média_7d) * 7, "
        "limitado a zero quando não há perda.",
        "**Filtros mínimos:** faturamento nos 30 dias anteriores >= R$ 500; pedidos nos 30 dias anteriores >= 5; "
        "queda_percentual >= 50%; produto precisa existir no histórico anterior.",
        "**Produtos zerados:** se o produto teve faturamento no histórico anterior e faturamento zero nos últimos 7 dias, "
        "a queda calculada é 100%. Produtos sem histórico anterior não entram no ranking.",
        "**Ordenação:** maior impacto_faturamento_perdido primeiro; o gráfico exibe o Top 10 após os filtros selecionados.",
    ]
    if hasattr(st, "popover"):
        with st.popover("Como esse ranking é calculado?"):
            st.markdown("\n\n".join(method_lines))
    else:
        with st.expander("Como esse ranking é calculado?", expanded=False):
            st.markdown("\n\n".join(method_lines))


def financial_trend(daily: pd.DataFrame, current: dict[str, object], previous: dict[str, object] | None) -> dict[str, str]:
    work = prepare_financial_daily_series(daily)
    if len(work) >= 6 and "resultado_operacional_pct" in work.columns:
        values = pd.to_numeric(work["resultado_operacional_pct"], errors="coerce").fillna(0)
        last_avg = float(values.tail(3).mean())
        prior_avg = float(values.iloc[-6:-3].mean())
        diff = last_avg - prior_avg
        basis = "ultimos dias"
    else:
        diff = 0.0
        basis = "periodo anterior"
        if previous:
            diff = float(current["resultado_operacional_pct"] or 0.0) - float(previous["resultado_operacional_pct"] or 0.0)
    if diff > 1:
        return {"label": "Melhorando", "color": "#22C55E", "detail": f"+{br_number(diff, 2)}pp vs {basis}"}
    if diff < -1:
        return {"label": "Piorando", "color": "#DC2626", "detail": f"{br_number(diff, 2)}pp vs {basis}"}
    return {"label": "Estavel", "color": "#64748B", "detail": f"Variacao de {br_number(diff, 2)}pp vs {basis}"}


def automatic_financial_alerts(
    current: dict[str, object],
    previous: dict[str, object] | None,
    trend: dict[str, str],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    cmv_pct = float(current["cmv_pct"] or 0.0)
    frete_pct = float(current["frete_pct"] or 0.0)
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    if cmv_pct > 45:
        alerts.append({"severity": "critico" if cmv_pct > 50 else "alerta", "title": "CMV acima da meta", "detail": f"{br_percent(cmv_pct)} vs meta de 45%"})
    if frete_pct > 8:
        alerts.append({"severity": "critico" if frete_pct > 12 else "alerta", "title": "Frete elevado", "detail": f"{br_percent(frete_pct)} vs meta de 8%"})
    if str(trend["label"]) == "Piorando":
        alerts.append({"severity": "alerta", "title": "Margem em queda", "detail": trend["detail"]})
    if result_pct < 12:
        alerts.append({"severity": "critico" if result_pct < 7 else "alerta", "title": "Resultado abaixo da meta", "detail": f"{br_percent(result_pct)} vs meta verde de 12%"})
    if previous:
        ticket_delta = compare_delta(float(current["ticket_medio"] or 0.0), float(previous["ticket_medio"] or 0.0))
        if ticket_delta is not None and ticket_delta < 0:
            alerts.append({"severity": "alerta", "title": "Ticket medio caindo", "detail": f"-{br_percent(abs(ticket_delta))} vs periodo anterior"})
    if not alerts:
        alerts.append({"severity": "saudavel", "title": "Sem alerta financeiro relevante", "detail": "Indicadores dentro das faixas executivas."})
    return alerts[:5]


def historical_summary(
    financial_base: pd.DataFrame | None,
    all_ads_df: pd.DataFrame | None,
) -> dict[str, object] | None:
    if financial_base is None or financial_base.empty:
        return None
    return financial_period_summary(financial_base, all_ads_df if all_ads_df is not None else pd.DataFrame(), None)


def smart_comparison_rows(
    current: dict[str, object],
    previous: dict[str, object] | None,
    historical: dict[str, object] | None,
) -> list[dict[str, str]]:
    metrics = [
        ("Faturamento", "receita", br_money, "maior", None),
        ("Resultado Final", "resultado_operacional_pct", br_percent, "maior", 12.0),
        ("CMV", "cmv_pct", br_percent, "menor", 45.0),
        ("Frete", "frete_pct", br_percent, "menor", 8.0),
    ]
    rows: list[dict[str, str]] = []
    for label, key, formatter, direction, target in metrics:
        current_value = float(current.get(key) or 0.0)
        previous_value = float(previous.get(key) or 0.0) if previous else None
        historical_value = float(historical.get(key) or 0.0) if historical else None
        if previous_value is None or previous_value == 0:
            previous_text = "N/D"
        else:
            previous_delta = compare_delta(current_value, previous_value)
            previous_text = "N/D" if previous_delta is None else br_percent(previous_delta)
        if historical_value is None or historical_value == 0:
            historical_text = "N/D"
        else:
            hist_delta = compare_delta(current_value, historical_value)
            historical_text = "N/D" if hist_delta is None else br_percent(hist_delta)
        if target is None:
            target_text = "Periodo anterior"
            target_status = "Referencia"
        else:
            target_text = br_percent(target)
            ok = current_value >= target if direction == "maior" else current_value <= target
            target_status = "Dentro" if ok else "Fora"
        rows.append(
            {
                "metric": label,
                "current": formatter(current_value),
                "previous": previous_text,
                "historical": historical_text,
                "target": target_text,
                "status": target_status,
            }
        )
    return rows


def progress_width(value: float, target: float, lower_is_better: bool = False) -> float:
    if target <= 0:
        return 100.0
    ratio = target / value if lower_is_better and value > 0 else value / target
    return max(0.0, min(ratio * 100, 100.0))


def render_goal_progress_card(label: str, value: str, target: str, progress: float, color: str, detail: str) -> str:
    return (
        f'<div class="finance-goal-card" style="--goal-color:{color};">'
        f'<div class="finance-goal-label">{html.escape(label)}</div>'
        f'<div class="finance-goal-value">{html.escape(value)}</div>'
        f'<div class="finance-goal-target">Meta: {html.escape(target)}</div>'
        '<div class="finance-goal-track">'
        f'<div class="finance-goal-fill" style="width:{progress:.2f}%;"></div>'
        "</div>"
        f'<div class="finance-goal-detail">{html.escape(detail)}</div>'
        "</div>"
    )


def render_executive_strategy_layer(
    current: dict[str, object],
    previous: dict[str, object] | None,
    historical: dict[str, object] | None,
    selected_period: tuple[date, date] | None,
    daily: pd.DataFrame,
) -> None:
    st.markdown('<div class="section-title">Painel Estrategico Financeiro</div>', unsafe_allow_html=True)
    score_info = financial_health_score(current, previous)
    projection = build_month_projection(current, selected_period, daily)
    projection_conf = projection_confidence(projection["elapsed_days"], projection["month_days"])
    projection_trend = projection_trend_text(daily, selected_period)
    trend = financial_trend(daily, current, previous)
    alerts = automatic_financial_alerts(current, previous, trend)

    left, right = st.columns([1, 1.45])
    with left:
        st.plotly_chart(financial_health_gauge(score_info), use_container_width=True)
        st.markdown(
            f"""
            <div class="finance-score-caption" style="--score-color:{score_info['color']};">
                <span>{html.escape(str(score_info['status']))}</span>
                <small>Score composto por resultado, CMV, frete, Ads, crescimento e ticket medio.</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        base_text = f"Baseado em {br_number(projection['elapsed_days'], 0)} de {br_number(projection['month_days'], 0)} dias"
        projection_cards = [
            (
                "Faturamento projetado",
                br_money(projection["receita"]),
                projection_comparison_text("Faturamento", projection["receita"], previous, "receita"),
                "#0F4C5C",
            ),
            (
                "Pedidos projetados",
                br_number(projection["pedidos"], 0),
                projection_comparison_text("Pedidos", projection["pedidos"], previous, "pedidos", formatter=br_number, suffix=" pedidos"),
                "#2563EB",
            ),
            (
                "Resultado projetado",
                br_money(projection["resultado"]),
                projection_comparison_text("Resultado", projection["resultado"], previous, "resultado_operacional_valor"),
                financial_result_color(projection["margem"]),
            ),
            (
                "Margem projetada",
                br_percent(projection["margem"]),
                projection_comparison_text("Margem", projection["margem"], previous, target=12.0, suffix="pp"),
                financial_result_color(projection["margem"]),
            ),
        ]
        projection_cards_html = "".join(
            render_projection_card(
                label,
                value,
                base_text,
                detail,
                str(projection_conf["label"]),
                color,
            )
            for label, value, detail, color in projection_cards
        )
        projection_html = (
            "<style>"
            ".finance-projection-wrap{border:1px solid rgba(148,163,184,.16);border-radius:10px;padding:.95rem;background:linear-gradient(180deg,rgba(15,23,42,.24),rgba(15,23,42,.08));}"
            ".finance-projection-head{display:flex;justify-content:space-between;gap:.8rem;align-items:flex-start;margin-bottom:.7rem;}"
            ".finance-projection-title{font-size:.78rem;text-transform:uppercase;font-weight:900;color:rgba(226,232,240,.96);letter-spacing:.02em;}"
            ".finance-projection-help{color:rgba(148,163,184,.96);font-size:.76rem;font-weight:680;line-height:1.35;max-width:560px;}"
            ".finance-projection-chip{white-space:nowrap;border:1px solid color-mix(in srgb,var(--confidence-color) 48%,transparent);background:color-mix(in srgb,var(--confidence-color) 12%,transparent);color:var(--confidence-color);border-radius:999px;padding:.3rem .58rem;font-size:.72rem;font-weight:900;}"
            ".finance-projection-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.72rem;}"
            ".finance-projection-card{min-height:150px;border:1px solid rgba(148,163,184,.18);border-top:4px solid var(--projection-color);border-radius:9px;padding:.82rem .9rem;background:linear-gradient(180deg,color-mix(in srgb,var(--projection-color) 11%,transparent),rgba(15,23,42,.12));}"
            ".finance-projection-label{color:rgba(148,163,184,.96);font-size:.72rem;font-weight:880;text-transform:uppercase;margin-bottom:.42rem;}"
            ".finance-projection-value{color:var(--projection-color);font-size:1.24rem;line-height:1.08;font-weight:950;}"
            ".finance-projection-base{margin-top:.48rem;color:rgba(226,232,240,.94);font-size:.78rem;font-weight:800;}"
            ".finance-projection-comparison{margin-top:.32rem;color:rgba(148,163,184,.98);font-size:.77rem;font-weight:760;}"
            ".finance-projection-confidence{margin-top:.5rem;color:rgba(148,163,184,.96);font-size:.75rem;font-weight:760;}"
            ".finance-projection-confidence span{color:var(--confidence-color);font-weight:950;}"
            ".finance-projection-trend{margin-top:.75rem;border-left:3px solid var(--trend-color);background:color-mix(in srgb,var(--trend-color) 9%,transparent);border-radius:8px;padding:.62rem .72rem;color:var(--trend-color);font-size:.78rem;font-weight:900;}"
            "@media(max-width:760px){.finance-projection-head{display:block}.finance-projection-chip{display:inline-block;margin-top:.55rem}.finance-projection-grid{grid-template-columns:1fr}}"
            "</style>"
            f'<div class="finance-projection-wrap" style="--confidence-color:{projection_conf["color"]};--trend-color:{projection_trend["color"]};">'
            '<div class="finance-projection-head">'
            '<div><div class="finance-projection-title">Projecao do mes</div>'
            '<div class="finance-projection-help">Projecao calculada pela media diaria atual do periodo filtrado, extrapolada ate o final do mes.</div></div>'
            f'<div class="finance-projection-chip">Confianca da projecao: {html.escape(str(projection_conf["label"]))}</div>'
            "</div>"
            f'<div class="finance-projection-grid">{projection_cards_html}</div>'
            f'<div class="finance-projection-trend">{html.escape(str(projection_trend["text"]))}</div>'
            "</div>"
        )
        st.markdown(projection_html.strip(), unsafe_allow_html=True)

    st.markdown(
        f"""
<style>
.finance-score-caption {{
    border: 1px solid color-mix(in srgb, var(--score-color) 45%, transparent);
    border-left: 4px solid var(--score-color);
    border-radius: 8px;
    padding: .8rem .9rem;
    background: color-mix(in srgb, var(--score-color) 10%, transparent);
    margin-top: -.25rem;
}}
.finance-score-caption span {{
    display: block;
    color: var(--score-color);
    font-size: 1.05rem;
    font-weight: 900;
    margin-bottom: .18rem;
}}
.finance-score-caption small {{
    color: rgba(148,163,184,.96);
    font-weight: 680;
    line-height: 1.35;
}}
</style>
        """,
        unsafe_allow_html=True,
    )

    render_financial_alerts_and_trend(alerts, trend)
    render_smart_comparison(current, previous, historical)
    render_financial_goals(current, previous, projection)


def render_financial_alerts_and_trend(alerts: list[dict[str, str]], trend: dict[str, str]) -> None:
    severity_colors = {"critico": "#DC2626", "alerta": "#D97706", "saudavel": "#0F766E"}
    cards = "".join(
        (
            f'<div class="finance-alert-card" style="--alert-color:{severity_colors.get(alert["severity"], "#64748B")};">'
            f'<div class="finance-alert-severity">{html.escape(alert["severity"])}</div>'
            f'<div class="finance-alert-title">{html.escape(alert["title"])}</div>'
            f'<div class="finance-alert-detail">{html.escape(alert["detail"])}</div>'
            "</div>"
        )
        for alert in alerts
    )
    markup = f"""
<style>
.finance-trend-card {{
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    border: 1px solid color-mix(in srgb, var(--trend-color) 42%, transparent);
    border-left: 4px solid var(--trend-color);
    border-radius: 8px;
    padding: .85rem .95rem;
    margin: .35rem 0 .85rem 0;
    background: color-mix(in srgb, var(--trend-color) 9%, transparent);
}}
.finance-trend-label {{
    color: rgba(148,163,184,.96);
    font-size: .72rem;
    font-weight: 900;
    text-transform: uppercase;
}}
.finance-trend-value {{
    color: var(--trend-color);
    font-size: 1.18rem;
    font-weight: 900;
    margin-top: .12rem;
}}
.finance-trend-detail {{
    color: rgba(148,163,184,.98);
    font-weight: 760;
    text-align: right;
}}
.finance-alert-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: .7rem;
    margin-bottom: .95rem;
}}
.finance-alert-card {{
    border: 1px solid rgba(148,163,184,.18);
    border-left: 4px solid var(--alert-color);
    border-radius: 8px;
    padding: .82rem .9rem;
    background: color-mix(in srgb, var(--alert-color) 8%, transparent);
    min-height: 116px;
}}
.finance-alert-severity {{
    color: var(--alert-color);
    text-transform: uppercase;
    font-size: .68rem;
    font-weight: 900;
    margin-bottom: .42rem;
}}
.finance-alert-title {{
    color: var(--alert-color);
    font-weight: 900;
    line-height: 1.18;
    margin-bottom: .4rem;
}}
.finance-alert-detail {{
    color: rgba(148,163,184,.98);
    font-size: .8rem;
    line-height: 1.35;
    font-weight: 670;
}}
</style>
<div class="finance-trend-card" style="--trend-color:{trend['color']};">
<div>
<div class="finance-trend-label">Tendencia financeira</div>
<div class="finance-trend-value">{html.escape(trend['label'])}</div>
</div>
<div class="finance-trend-detail">{html.escape(trend['detail'])}</div>
</div>
<div class="finance-alert-grid">{cards}</div>
"""
    st.markdown(markup.strip(), unsafe_allow_html=True)


def render_smart_comparison(
    current: dict[str, object],
    previous: dict[str, object] | None,
    historical: dict[str, object] | None,
) -> None:
    rows = smart_comparison_rows(current, previous, historical)
    row_html = "".join(
        "<tr>"
        f"<td>{html.escape(row['metric'])}</td>"
        f"<td>{html.escape(row['current'])}</td>"
        f"<td>{html.escape(row['previous'])}</td>"
        f"<td>{html.escape(row['historical'])}</td>"
        f"<td>{html.escape(row['target'])}</td>"
        f"<td><span class=\"finance-smart-badge\">{html.escape(row['status'])}</span></td>"
        "</tr>"
        for row in rows
    )
    markup = f"""
<style>
.finance-smart-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 .38rem;
    margin-bottom: .95rem;
}}
.finance-smart-table th {{
    color: rgba(148,163,184,.92);
    font-size: .68rem;
    text-transform: uppercase;
    text-align: left;
    padding: 0 .65rem;
}}
.finance-smart-table td {{
    background: rgba(15,23,42,.20);
    border-top: 1px solid rgba(148,163,184,.14);
    border-bottom: 1px solid rgba(148,163,184,.14);
    padding: .62rem .65rem;
    font-weight: 760;
}}
.finance-smart-table td:first-child {{
    border-left: 1px solid rgba(148,163,184,.14);
    border-radius: 8px 0 0 8px;
    font-weight: 900;
}}
.finance-smart-table td:last-child {{
    border-right: 1px solid rgba(148,163,184,.14);
    border-radius: 0 8px 8px 0;
}}
.finance-smart-badge {{
    display: inline-flex;
    border: 1px solid rgba(148,163,184,.22);
    border-radius: 999px;
    padding: .14rem .44rem;
    font-size: .68rem;
    text-transform: uppercase;
    font-weight: 900;
    color: rgba(226,232,240,.92);
}}
</style>
<div class="finance-strategy-subtitle">Comparativo inteligente</div>
<table class="finance-smart-table">
<thead>
<tr>
<th>Indicador</th>
<th>Atual</th>
<th>Periodo anterior</th>
<th>Media historica</th>
<th>Meta interna</th>
<th>Status</th>
</tr>
</thead>
<tbody>{row_html}</tbody>
</table>
"""
    st.markdown(markup.strip(), unsafe_allow_html=True)


def render_financial_goals(
    current: dict[str, object],
    previous: dict[str, object] | None,
    projection: dict[str, float],
) -> None:
    receita = float(current["receita"] or 0.0)
    revenue_target = float(previous["receita"] or 0.0) if previous and float(previous["receita"] or 0.0) > 0 else max(receita, 1.0)
    result_pct = float(current["resultado_operacional_pct"] or 0.0)
    cmv_pct = float(current["cmv_pct"] or 0.0)
    frete_pct = float(current["frete_pct"] or 0.0)
    goal_cards = [
        render_goal_progress_card(
            "Faturamento",
            br_money(receita),
            br_money(revenue_target),
            progress_width(receita, revenue_target),
            "#0F4C5C",
            f"Projecao mensal: {br_money(projection['receita'])}",
        ),
        render_goal_progress_card(
            "Margem final",
            br_percent(result_pct),
            "12%",
            progress_width(result_pct, 12.0),
            financial_result_color(result_pct),
            format_pp_delta(result_pct, 12.0),
        ),
        render_goal_progress_card(
            "CMV",
            br_percent(cmv_pct),
            "45%",
            progress_width(cmv_pct, 45.0, lower_is_better=True),
            "#0F766E" if cmv_pct <= 45 else "#DC2626",
            format_pp_delta(cmv_pct, 45.0, lower_is_better=True),
        ),
        render_goal_progress_card(
            "Frete",
            br_percent(frete_pct),
            "8%",
            progress_width(frete_pct, 8.0, lower_is_better=True),
            "#0F766E" if frete_pct <= 8 else "#DC2626",
            format_pp_delta(frete_pct, 8.0, lower_is_better=True),
        ),
    ]
    goals_html = f"""
<style>
.finance-goal-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: .7rem;
    margin-bottom: 1rem;
}}
.finance-goal-card {{
    border: 1px solid rgba(148,163,184,.18);
    border-top: 4px solid var(--goal-color);
    border-radius: 8px;
    padding: .82rem .9rem;
    background: color-mix(in srgb, var(--goal-color) 8%, transparent);
}}
.finance-goal-label {{
    color: rgba(148,163,184,.96);
    font-size: .72rem;
    font-weight: 900;
    text-transform: uppercase;
    margin-bottom: .34rem;
}}
.finance-goal-value {{
    color: var(--goal-color);
    font-size: 1.15rem;
    line-height: 1.1;
    font-weight: 900;
}}
.finance-goal-target, .finance-goal-detail {{
    color: rgba(148,163,184,.96);
    font-size: .76rem;
    font-weight: 720;
    margin-top: .36rem;
}}
.finance-goal-track {{
    margin-top: .58rem;
    height: .48rem;
    border-radius: 999px;
    background: rgba(148,163,184,.18);
    overflow: hidden;
}}
.finance-goal-fill {{
    height: 100%;
    background: linear-gradient(90deg, color-mix(in srgb, var(--goal-color) 55%, transparent), var(--goal-color));
    border-radius: 999px;
}}
</style>
<div class="finance-strategy-subtitle">Metas financeiras</div>
<div class="finance-goal-grid">{''.join(goal_cards)}</div>
"""
    st.markdown(goals_html.strip(), unsafe_allow_html=True)


def format_period(period: tuple[date, date] | None) -> str:
    """Formata periodos para debug legivel."""

    if not period:
        return "sem periodo valido"
    start_date, end_date = period
    return f"{start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}"


def log_post_ads_debug(
    filtered_sales: pd.DataFrame,
    filtered_ads: pd.DataFrame,
    selected_period: tuple[date, date],
    ads_filter_info: dict[str, object],
    filter_state: dict[str, object],
) -> None:
    """Imprime debug temporario do recorte pos Ads no terminal/log."""

    values = calculate_post_ads_values(filtered_sales, filtered_ads)
    print(
        "[DEBUG POS ADS] "
        f"periodo_filtrado_vendas={format_period(selected_period)} "
        f"timezone={APP_TIMEZONE} "
        f"filtros_globais={filter_state}"
    )
    print(
        "[DEBUG POS ADS] "
        f"periodo_filtrado_ads={format_period(ads_filter_info.get('period'))} "
        f"status_ads={ads_filter_info.get('status')}"
    )
    print(
        "[DEBUG POS ADS] "
        f"custo_ads_considerado={values['ads_filtrado_periodo']:.2f} "
        f"lucro_liquido_antes_ads={values['lucro_liquido_estimado']:.2f} "
        f"lucro_pos_ads={values['lucro_pos_ads']:.2f}"
    )


@st.cache_data(show_spinner="Carregando historico...")
def load_historical_data(path: str) -> pd.DataFrame:
    """Le o DuckDB historico usando somente o ultimo snapshot de cada dia."""

    db_path = Path(path)
    if not db_path.exists():
        return pd.DataFrame()

    query = """
        WITH ultimo_snapshot_vendas AS (
            SELECT
                CAST(data_snapshot AS DATE) AS data,
                MAX(data_snapshot) AS data_snapshot
            FROM historico_vendas
            GROUP BY 1
        ),
        ultimo_snapshot_ads AS (
            SELECT
                CAST(data_snapshot AS DATE) AS data,
                MAX(data_snapshot) AS data_snapshot
            FROM historico_ads
            GROUP BY 1
        ),
        ultimo_snapshot_estoque AS (
            SELECT
                CAST(data_snapshot AS DATE) AS data,
                MAX(data_snapshot) AS data_snapshot
            FROM historico_estoque
            GROUP BY 1
        ),
        vendas AS (
            SELECT
                u.data,
                SUM(receita) AS faturamento,
                SUM(lucro_liquido_estimado) AS lucro_liquido_estimado,
                COUNT(DISTINCT order_id) AS pedidos
            FROM historico_vendas h
            INNER JOIN ultimo_snapshot_vendas u
                ON h.data_snapshot = u.data_snapshot
            GROUP BY 1
        ),
        ads AS (
            SELECT
                u.data,
                SUM(cost) AS investimento_ads,
                SUM(revenue) AS receita_ads
            FROM historico_ads h
            INNER JOIN ultimo_snapshot_ads u
                ON h.data_snapshot = u.data_snapshot
            GROUP BY 1
        ),
        estoque AS (
            SELECT
                u.data,
                SUM(estoque_atual) AS estoque_total
            FROM historico_estoque h
            INNER JOIN ultimo_snapshot_estoque u
                ON h.data_snapshot = u.data_snapshot
            GROUP BY 1
        )
        SELECT
            v.data,
            v.faturamento,
            v.lucro_liquido_estimado,
            CASE WHEN v.faturamento = 0 THEN NULL
                 ELSE v.lucro_liquido_estimado / v.faturamento * 100 END AS margem_liquida,
            COALESCE(a.investimento_ads, 0) AS investimento_ads,
            COALESCE(a.receita_ads, 0) AS receita_ads,
            CASE WHEN COALESCE(a.investimento_ads, 0) = 0 THEN NULL
                 ELSE a.receita_ads / a.investimento_ads END AS roas,
            CASE WHEN COALESCE(a.receita_ads, 0) = 0 THEN NULL
                 ELSE a.investimento_ads / a.receita_ads * 100 END AS acos,
            CASE WHEN v.faturamento = 0 THEN NULL
                 ELSE (v.lucro_liquido_estimado - COALESCE(a.investimento_ads, 0)) / v.faturamento * 100 END
                 AS margem_pos_ads,
            COALESCE(e.estoque_total, 0) AS estoque_total,
            v.pedidos,
            CASE WHEN v.pedidos = 0 THEN NULL
                 ELSE v.faturamento / v.pedidos END AS ticket_medio
        FROM vendas v
        LEFT JOIN ads a USING (data)
        LEFT JOIN estoque e USING (data)
        ORDER BY v.data
    """

    try:
        with duckdb.connect(str(db_path), read_only=True) as con:
            df = con.execute(query).df()
            snapshot_stats = con.execute(
                """
                SELECT
                    'historico_vendas' AS tabela,
                    COUNT(DISTINCT data_snapshot) AS quantidade_snapshots,
                    COUNT(DISTINCT CAST(data_snapshot AS DATE)) AS dias_unicos
                FROM historico_vendas
                UNION ALL
                SELECT
                    'historico_ads' AS tabela,
                    COUNT(DISTINCT data_snapshot) AS quantidade_snapshots,
                    COUNT(DISTINCT CAST(data_snapshot AS DATE)) AS dias_unicos
                FROM historico_ads
                UNION ALL
                SELECT
                    'historico_estoque' AS tabela,
                    COUNT(DISTINCT data_snapshot) AS quantidade_snapshots,
                    COUNT(DISTINCT CAST(data_snapshot AS DATE)) AS dias_unicos
                FROM historico_estoque
                """
            ).df()
            rows_per_snapshot = con.execute(
                """
                SELECT 'historico_vendas' AS tabela, data_snapshot, COUNT(*) AS linhas
                FROM historico_vendas
                GROUP BY 1, 2
                UNION ALL
                SELECT 'historico_ads' AS tabela, data_snapshot, COUNT(*) AS linhas
                FROM historico_ads
                GROUP BY 1, 2
                UNION ALL
                SELECT 'historico_estoque' AS tabela, data_snapshot, COUNT(*) AS linhas
                FROM historico_estoque
                GROUP BY 1, 2
                ORDER BY tabela, data_snapshot
                """
            ).df()
    except Exception:
        return pd.DataFrame()

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"]).dt.date
        log_historical_debug(snapshot_stats, rows_per_snapshot, df)
    return df


def log_historical_debug(
    snapshot_stats: pd.DataFrame,
    rows_per_snapshot: pd.DataFrame,
    history_df: pd.DataFrame,
) -> None:
    """Imprime debug temporario da consolidacao diaria do historico."""

    print(snapshot_stats.to_string(index=False))
    print(rows_per_snapshot.to_string(index=False))
    print(history_df[["data", "faturamento"]].to_string(index=False))


def enrich_sales_with_inventory(df: pd.DataFrame, inventory_df: pd.DataFrame) -> pd.DataFrame:
    """Leva status de estoque para a base de vendas sem alterar sua granularidade."""

    df = df.copy()
    if inventory_df.empty:
        df["status_estoque"] = "N/D"
        return df

    inventory_status = inventory_df[["item_id", "status_estoque"]].drop_duplicates("item_id")
    df = df.merge(inventory_status, on="item_id", how="left")
    df["status_estoque"] = df["status_estoque"].fillna("N/D").astype(str)
    return df


def apply_filters(
    df: pd.DataFrame,
    inventory_df: pd.DataFrame,
) -> tuple[pd.DataFrame, tuple[date, date], tuple[date, date], dict[str, object], str]:
    """Renderiza sidebar e aplica filtros globais."""

    with st.sidebar:
        st.markdown("### Jit Parts BI")
        st.caption("Mercado Livre + Seconds")
        st.caption(last_update_label(LAST_RUN_LOG_PATH))

        st.markdown('<div class="section-title">Atualizacao</div>', unsafe_allow_html=True)
        if _IS_CLOUD:
            st.caption("Atualizacao automatica — dados carregados do repositorio.")
            st.info("No ambiente cloud, os dados sao atualizados via pipeline de dados.", icon="☁️")
        else:
            st.caption("Atualiza pedidos, fretes, estoque, Ads e base consolidada.")
            if st.button("Atualizar Dashboard", use_container_width=True, type="primary"):
                with st.spinner("Atualizando dashboard..."):
                    result = run_dashboard_update()
                if result.returncode == 0:
                    st.success("Dashboard atualizado com sucesso.")
                    if result.stdout:
                        with st.expander("Ver saida da atualizacao"):
                            st.code(result.stdout)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Falha ao atualizar dashboard. Codigo: {result.returncode}")
                    if result.stdout:
                        with st.expander("stdout"):
                            st.code(result.stdout)
                    if result.stderr:
                        with st.expander("stderr"):
                            st.code(result.stderr)

        if st.button("Limpar filtros", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key.startswith("filter_"):
                    del st.session_state[key]
            st.rerun()

        st.divider()

        financial_mode = st.radio(
            "Fonte Financeira",
            [FINANCIAL_MODE_OFFICIAL, FINANCIAL_MODE_HYBRID],
            index=1,
            key="filter_financial_mode",
        )
        if financial_mode == FINANCIAL_MODE_OFFICIAL:
            st.info("Dados financeiros oficiais provenientes da Seconds.")
        else:
            st.info("Valores estimados utilizando pedidos ML enriquecidos com parâmetros financeiros da Seconds.")

        st.divider()

        valid_dates = df["data_ref"].dropna()
        if valid_dates.empty:
            st.error("A base nao possui datas validas em date_created.")
            today = date.today()
            return df.iloc[0:0].copy(), (today, today), (today, today), {}, financial_mode

        min_date = valid_dates.min()
        max_date = valid_dates.max()
        base_period = (min_date, max_date)

        # O valor inicial usa o intervalo real da base, mas o usuario pode
        # escolher janelas mais amplas para verificar periodos sem movimento.
        free_min_date = date(min_date.year - 5, 1, 1)
        free_max_date = max(max_date + timedelta(days=365), date.today() + timedelta(days=365))

        selected_period = st.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=free_min_date,
            max_value=free_max_date,
            key="filter_period",
        )

        if isinstance(selected_period, tuple) and len(selected_period) == 2:
            start_date, end_date = selected_period
        else:
            selected_date = selected_period[0] if isinstance(selected_period, tuple) else selected_period
            st.info("Selecione tambem a data final para aplicar um intervalo.")
            start_date, end_date = selected_date, selected_date

        requested_period = (start_date, end_date)

        if start_date > end_date:
            st.error("Periodo invalido: a data inicial deve ser menor ou igual a data final.")
            return df.iloc[0:0].copy(), requested_period, base_period, {}, financial_mode

        effective_start = max(start_date, min_date)
        effective_end = min(end_date, max_date)
        has_effective_overlap = effective_start <= effective_end
        period_limited_by_base = start_date < min_date or end_date > max_date
        current_period = (effective_start, effective_end) if has_effective_overlap else requested_period

        if period_limited_by_base:
            if has_effective_overlap:
                st.warning(
                    "Base disponivel somente ate "
                    f"{max_date:%d/%m/%Y}. O periodo filtrado foi limitado aos dados disponiveis."
                )
                st.caption(f"Periodo solicitado: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}")
                st.caption(f"Periodo efetivamente analisado: {effective_start:%d/%m/%Y} a {effective_end:%d/%m/%Y}")
            else:
                st.warning(
                    "O periodo solicitado nao possui dados na base disponivel "
                    f"({min_date:%d/%m/%Y} a {max_date:%d/%m/%Y})."
                )

        st.caption(f"Intervalo atual: {current_period[0]:%d/%m/%Y} a {current_period[1]:%d/%m/%Y}")
        st.caption(f"Base disponivel: {min_date:%d/%m/%Y} a {max_date:%d/%m/%Y}")

        marcas = st.multiselect("Marca", sorted(df["Marca"].dropna().unique()), key="filter_marca")
        categorias = st.multiselect(
            "Categoria",
            sorted(df["Nome da Categoria"].dropna().unique()),
            key="filter_categoria",
        )
        full_values = st.multiselect("FULL", sorted(df["FULL"].dropna().unique()), key="filter_full")
        flex_values = st.multiselect("Flex", sorted(df["Flex"].dropna().unique()), key="filter_flex")
        status_values = st.multiselect("Status anuncio", sorted(df["Status"].dropna().unique()), key="filter_status")
        stock_status_options = sorted(
            pd.concat(
                [
                    df["status_estoque"] if "status_estoque" in df.columns else pd.Series(dtype="object"),
                    inventory_df["status_estoque"] if "status_estoque" in inventory_df.columns else pd.Series(dtype="object"),
                ],
                ignore_index=True,
            )
            .dropna()
            .astype(str)
            .unique()
        )
        stock_status_values = st.multiselect(
            "Status estoque",
            stock_status_options,
            key="filter_status_estoque",
        )
        listing_values = st.multiselect(
            "Listing type",
            sorted(df["listing_type_id"].dropna().unique()),
            key="filter_listing",
        )
        produto = st.text_input("Produto", key="filter_produto", placeholder="Buscar no nome do produto")
        mlb = st.text_input("MLB", key="filter_mlb", placeholder="Buscar MLB")

        st.divider()
        st.caption(f"Linhas na base: {len(df):,}".replace(",", "."))

    analysis_start, analysis_end = current_period
    date_mask = (df["data_ref"] >= analysis_start) & (df["data_ref"] <= analysis_end)
    seconds_period = get_seconds_snapshot_period(df)
    seconds_mask = (
        df["financial_source"].astype(str).eq("seconds_snapshot")
        if "financial_source" in df.columns
        else pd.Series(False, index=df.index)
    )
    if selected_period_inside_seconds_snapshot(current_period, seconds_period):
        # Linhas de snapshot financeiro ja representam o periodo exportado.
        # Filtrar por date_created do ML seleciona apenas um subconjunto de anuncios
        # e distorce os totais financeiros da Seconds.
        date_mask = date_mask | seconds_mask

    filtered = df[date_mask].copy()
    if marcas:
        filtered = filtered[filtered["Marca"].isin(marcas)]
    if categorias:
        filtered = filtered[filtered["Nome da Categoria"].isin(categorias)]
    if full_values:
        filtered = filtered[filtered["FULL"].isin(full_values)]
    if flex_values:
        filtered = filtered[filtered["Flex"].isin(flex_values)]
    if status_values:
        filtered = filtered[filtered["Status"].isin(status_values)]
    if stock_status_values:
        filtered = filtered[filtered["status_estoque"].isin(stock_status_values)]
    if listing_values:
        filtered = filtered[filtered["listing_type_id"].isin(listing_values)]
    if produto:
        filtered = filtered[filtered["produto"].str.contains(produto, case=False, na=False)]
    if mlb:
        filtered = filtered[filtered["item_id"].str.contains(mlb, case=False, na=False)]

    if filtered.empty:
        st.sidebar.warning("Nenhum dado encontrado para o periodo/filtros selecionados.")

    filter_state = {
        "marcas": marcas,
        "categorias": categorias,
        "full_values": full_values,
        "flex_values": flex_values,
        "status_values": status_values,
        "stock_status_values": stock_status_values,
        "listing_values": listing_values,
        "produto": produto,
        "mlb": mlb,
        "financial_mode": financial_mode,
        "requested_period": requested_period,
        "effective_period": current_period,
        "period_limited_by_base": period_limited_by_base,
    }
    return filtered, current_period, base_period, filter_state, financial_mode


def get_official_seconds_period_from_columns(df: pd.DataFrame) -> tuple[date | None, date | None]:
    """Extrai periodo oficial da Seconds quando a base trouxer essas colunas."""

    if df.empty:
        return None, None

    starts = (
        pd.to_datetime(df.get("seconds_period_start", pd.Series(dtype="object")), errors="coerce")
        .dropna()
    )
    ends = (
        pd.to_datetime(df.get("seconds_period_end", pd.Series(dtype="object")), errors="coerce")
        .dropna()
    )
    if starts.empty or ends.empty:
        return None, None
    return starts.min().date(), ends.max().date()


def get_official_seconds_period(df: pd.DataFrame) -> tuple[date, date] | None:
    """Retorna o periodo do financeiro oficial, com fallback manual do snapshot atual."""

    start_date, end_date = get_official_seconds_period_from_columns(df)
    if start_date is not None and end_date is not None:
        return start_date, end_date
    if not df.empty:
        return SECONDS_OFFICIAL_FALLBACK_PERIOD
    return None


def apply_official_seconds_filters(
    seconds_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> pd.DataFrame:
    """Aplica somente filtros compativeis com o snapshot agregado da Seconds."""

    filtered = seconds_df.copy()
    if filtered.empty:
        return filtered

    marcas = filter_state.get("marcas") or []
    categorias = filter_state.get("categorias") or []
    full_values = filter_state.get("full_values") or []
    flex_values = filter_state.get("flex_values") or []
    status_values = filter_state.get("status_values") or []
    produto = safe_text(filter_state.get("produto"), "")
    mlb = safe_text(filter_state.get("mlb"), "")

    if marcas:
        filtered = filtered[filtered["Marca"].isin(marcas)]
    if categorias:
        filtered = filtered[filtered["Nome da Categoria"].isin(categorias)]
    if full_values:
        filtered = filtered[filtered["FULL"].isin(full_values)]
    if flex_values:
        filtered = filtered[filtered["Flex"].isin(flex_values)]
    if status_values:
        filtered = filtered[filtered["Status"].isin(status_values)]
    if produto:
        filtered = filtered[filtered["produto"].str.contains(produto, case=False, na=False)]
    if mlb:
        filtered = filtered[filtered["item_id"].str.contains(mlb, case=False, na=False)]
    return filtered


def use_hybrid_financial_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ativa os campos financeiros estimados da base transacional ML + Seconds."""

    active = df.copy()
    numeric_defaults = {
        "receita": 0.0,
        "lucro_liquido_estimado": 0.0,
        "CMV total": 0.0,
        "custo_frete_final": 0.0,
        "imposto": 0.0,
        "custo_fixo": 0.0,
        "sale_fee": 0.0,
        "lucro_bruto": 0.0,
        "lucro_operacional": 0.0,
        "extra": 0.0,
        "margem_liquida_estimada": pd.NA,
    }
    active = ensure_columns(active, numeric_defaults)
    source_map = {
        "CMV total": ["cmv_total", "CMV total"],
        "custo_frete_final": ["frete_total", "custo_frete_final"],
        "imposto": ["imposto_total", "imposto"],
        "custo_fixo": ["custo_fixo_total", "custo_fixo"],
        "sale_fee": ["comissao_total", "sale_fee"],
    }
    for target, sources in source_map.items():
        for source in sources:
            if source in active.columns:
                active[target] = pd.to_numeric(active[source], errors="coerce").fillna(0)
                break
    active["receita"] = pd.to_numeric(active["receita"], errors="coerce").fillna(0)
    active["lucro_liquido_estimado"] = pd.to_numeric(active["lucro_liquido_estimado"], errors="coerce").fillna(0)
    active["margem_liquida_estimada"] = (
        active["lucro_liquido_estimado"] / active["receita"].replace(0, pd.NA) * 100
    )
    active["financial_mode"] = FINANCIAL_MODE_HYBRID
    active.attrs["financial_mode"] = FINANCIAL_MODE_HYBRID
    active.attrs["financial_source_used"] = "ml_orders_seconds_params"
    return active


def use_official_seconds_financial_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ativa os campos financeiros oficiais agregados da Seconds."""

    active = df.copy()
    mappings = {
        "receita": "faturamento_seconds",
        "lucro_liquido_estimado": "lucro_liquido_seconds",
        "CMV total": "cmv_seconds",
        "custo_frete_final": "frete_seconds",
        "imposto": "imposto_seconds",
        "custo_fixo": "custo_fixo_seconds",
        "sale_fee": "comissao_seconds",
        "lucro_bruto": "lucro_bruto_seconds",
        "lucro_operacional": "lucro_liquido_seconds",
        "margem_liquida_estimada": "margem_seconds",
        "margem_operacional": "margem_seconds",
        "margem_bruta": "margem_seconds",
    }
    for target, source in mappings.items():
        if source in active.columns:
            active[target] = pd.to_numeric(active[source], errors="coerce")
        elif target not in active.columns:
            active[target] = 0.0
    active["extra"] = active.get("extra", pd.Series(0.0, index=active.index)).fillna(0)
    active["financial_mode"] = FINANCIAL_MODE_OFFICIAL
    active.attrs["financial_mode"] = FINANCIAL_MODE_OFFICIAL
    active.attrs["financial_source_used"] = "seconds_official"
    return active


def get_financial_metrics(filtered: pd.DataFrame, financial_mode: str) -> dict[str, float | str]:
    """Calcula os totais financeiros conforme a fonte selecionada."""

    if filtered.empty:
        source = "seconds_official" if financial_mode == FINANCIAL_MODE_OFFICIAL else "ml_orders_seconds_params"
        return {
            "financial_mode": financial_mode,
            "financial_source": source,
            "faturamento": 0.0,
            "lucro_liquido": 0.0,
            "margem_liquida": 0.0,
            "lucro_operacional": 0.0,
            "margem_operacional": 0.0,
            "cmv": 0.0,
            "frete": 0.0,
            "impostos": 0.0,
            "custo_fixo": 0.0,
            "comissao": 0.0,
        }

    source = filtered.attrs.get(
        "financial_source_used",
        "seconds_official" if financial_mode == FINANCIAL_MODE_OFFICIAL else "ml_orders_seconds_params",
    )

    def sum_column(column: str) -> float:
        if column not in filtered.columns:
            return 0.0
        return float(pd.to_numeric(filtered[column], errors="coerce").fillna(0).sum())

    faturamento = sum_column("receita")
    lucro_liquido = sum_column("lucro_liquido_estimado")
    lucro_operacional = sum_column("lucro_operacional")
    cmv = sum_column("CMV total")
    frete = sum_column("custo_frete_final")
    impostos = sum_column("imposto")
    custo_fixo = sum_column("custo_fixo")
    comissao = sum_column("sale_fee")
    margem_liquida = (lucro_liquido / faturamento * 100) if faturamento else 0.0
    margem_operacional = (lucro_operacional / faturamento * 100) if faturamento else 0.0
    return {
        "financial_mode": financial_mode,
        "financial_source": source,
        "faturamento": faturamento,
        "lucro_liquido": lucro_liquido,
        "margem_liquida": margem_liquida,
        "lucro_operacional": lucro_operacional,
        "margem_operacional": margem_operacional,
        "cmv": cmv,
        "frete": frete,
        "impostos": impostos,
        "custo_fixo": custo_fixo,
        "comissao": comissao,
    }


def log_financial_mode_debug(filtered: pd.DataFrame, financial_mode: str) -> None:
    """Imprime debug da fonte financeira ativa."""

    metrics = get_financial_metrics(filtered, financial_mode)
    print("[DEBUG FINANCIAL MODE]")
    print(f"modo selecionado={metrics['financial_mode']}")
    print(f"fonte utilizada={metrics['financial_source']}")
    print(
        "totais calculados "
        f"faturamento={metrics['faturamento']:.2f} "
        f"lucro={metrics['lucro_liquido']:.2f} "
        f"cmv={metrics['cmv']:.2f} "
        f"frete={metrics['frete']:.2f} "
        f"imposto={metrics['impostos']:.2f} "
        f"margem={metrics['margem_liquida']:.2f}"
    )


def prepare_financial_view(
    ml_filtered: pd.DataFrame,
    seconds_official_df: pd.DataFrame,
    selected_period: tuple[date, date],
    filter_state: dict[str, object],
    financial_mode: str,
) -> tuple[pd.DataFrame, str | None]:
    """Monta a base usada pelas metricas financeiras no modo selecionado."""

    if financial_mode == FINANCIAL_MODE_HYBRID:
        return use_hybrid_financial_columns(ml_filtered), None

    official_filtered = apply_official_seconds_filters(seconds_official_df, filter_state)
    return use_official_seconds_financial_columns(official_filtered), None


def apply_non_date_filters(df: pd.DataFrame, filter_state: dict[str, object]) -> pd.DataFrame:
    """Aplica filtros globais exceto periodo, para comparativos temporais."""

    filtered = df.copy()
    if filtered.empty:
        return filtered

    marcas = filter_state.get("marcas") or []
    categorias = filter_state.get("categorias") or []
    full_values = filter_state.get("full_values") or []
    flex_values = filter_state.get("flex_values") or []
    status_values = filter_state.get("status_values") or []
    stock_status_values = filter_state.get("stock_status_values") or []
    listing_values = filter_state.get("listing_values") or []
    produto = safe_text(filter_state.get("produto"), "")
    mlb = safe_text(filter_state.get("mlb"), "")

    if marcas and "Marca" in filtered.columns:
        filtered = filtered[filtered["Marca"].isin(marcas)]
    if categorias and "Nome da Categoria" in filtered.columns:
        filtered = filtered[filtered["Nome da Categoria"].isin(categorias)]
    if full_values and "FULL" in filtered.columns:
        filtered = filtered[filtered["FULL"].isin(full_values)]
    if flex_values and "Flex" in filtered.columns:
        filtered = filtered[filtered["Flex"].isin(flex_values)]
    if status_values and "Status" in filtered.columns:
        filtered = filtered[filtered["Status"].isin(status_values)]
    if stock_status_values and "status_estoque" in filtered.columns:
        filtered = filtered[filtered["status_estoque"].isin(stock_status_values)]
    if listing_values and "listing_type_id" in filtered.columns:
        filtered = filtered[filtered["listing_type_id"].isin(listing_values)]
    if produto and "produto" in filtered.columns:
        filtered = filtered[filtered["produto"].astype(str).str.contains(produto, case=False, na=False)]
    if mlb and "item_id" in filtered.columns:
        filtered = filtered[filtered["item_id"].astype(str).str.contains(mlb, case=False, na=False)]
    return filtered


def get_seconds_snapshot_period(df: pd.DataFrame) -> tuple[date, date] | None:
    """Retorna o periodo valido do snapshot financeiro da Seconds."""

    if df.empty or "financial_source" not in df.columns:
        return None

    seconds_rows = df[df["financial_source"].astype(str).eq("seconds_snapshot")]
    if seconds_rows.empty:
        return None

    starts = pd.to_datetime(seconds_rows.get("seconds_period_start"), errors="coerce").dropna()
    ends = pd.to_datetime(seconds_rows.get("seconds_period_end"), errors="coerce").dropna()
    if starts.empty or ends.empty:
        return None

    return starts.min().date(), ends.max().date()


def selected_period_inside_seconds_snapshot(
    selected_period: tuple[date, date],
    seconds_period: tuple[date, date] | None,
) -> bool:
    """Valida se o filtro global esta dentro do periodo exportado pela Seconds."""

    if seconds_period is None:
        return False

    selected_start, selected_end = selected_period
    seconds_start, seconds_end = seconds_period
    return selected_start >= seconds_start and selected_end <= seconds_end


def disable_seconds_snapshot_financials(df: pd.DataFrame) -> pd.DataFrame:
    """Remove metricas financeiras da Seconds quando o periodo nao e compativel."""

    protected = df.copy()
    zero_columns = [
        "receita",
        "faturamento",
        "faturamento_seconds",
        "unit_price",
        "sale_fee",
        "comissao_ml",
        "comissao_seconds",
        "custo_frete",
        "custo_frete_final",
        "frete_seconds",
        "CMV total",
        "CMV unitario",
        "CMV unit�rio",
        "CMV unitÃ¡rio",
        "cmv_seconds",
        "imposto",
        "imposto_seconds",
        "custo_fixo",
        "custo_fixo_seconds",
        "extra",
        "lucro_bruto",
        "lucro_bruto_seconds",
        "lucro_operacional",
        "lucro_liquido_estimado",
        "lucro_liquido_seconds",
        "Lucro Bruto",
        "Lucro Liquido Seconds",
    ]
    null_columns = [
        "margem_bruta",
        "margem_operacional",
        "margem_liquida_estimada",
        "margem_seconds",
        "Margem Seconds",
        "margem calculada",
    ]

    seconds_mask = protected["financial_source"].astype(str).eq("seconds_snapshot")
    for column in zero_columns:
        if column in protected.columns:
            protected.loc[seconds_mask, column] = 0
    for column in null_columns:
        if column in protected.columns:
            protected.loc[seconds_mask, column] = pd.NA

    return protected


def apply_seconds_snapshot_period_guard(
    filtered: pd.DataFrame,
    selected_period: tuple[date, date],
) -> tuple[pd.DataFrame, str | None]:
    """Usa o financeiro da Seconds somente quando o filtro global e compativel."""

    if filtered.empty or "financial_source" not in filtered.columns:
        return filtered, None

    has_seconds_snapshot = filtered["financial_source"].astype(str).eq("seconds_snapshot").any()
    if not has_seconds_snapshot:
        return filtered, None

    seconds_period = get_seconds_snapshot_period(filtered)
    if selected_period_inside_seconds_snapshot(selected_period, seconds_period):
        return filtered, None

    warning = "Período selecionado não compatível com snapshot financeiro da Seconds."
    return disable_seconds_snapshot_financials(filtered), warning


def calculate_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Calcula indicadores executivos principais."""

    financial_mode = str(df.attrs.get("financial_mode", FINANCIAL_MODE_HYBRID))
    metrics = get_financial_metrics(df, financial_mode)
    return {
        "faturamento": float(metrics["faturamento"]),
        "lucro_liquido": float(metrics["lucro_liquido"]),
        "margem_liquida": float(metrics["margem_liquida"]),
        "lucro_operacional": float(metrics["lucro_operacional"]),
        "margem_operacional": float(metrics["margem_operacional"]),
        "cmv": float(metrics["cmv"]),
        "frete": float(metrics["frete"]),
        "impostos": float(metrics["impostos"]),
    }


def layout_chart(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    """Padroniza visual Plotly."""

    fig.update_layout(
        title=title,
        height=height,
        colorway=COLORWAY,
        margin=dict(l=18, r=18, t=52, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.18)", zeroline=False)
    return fig


def empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text="N/D", x=0.5, y=0.5, showarrow=False, font_size=22)
    return layout_chart(fig, title)


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    daily = (
        df.groupby("date", as_index=False)
        .agg(
            receita=("receita", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
            lucro_operacional=("lucro_operacional", "sum"),
            lucro_bruto=("lucro_bruto", "sum"),
            pedidos=("order_id", "nunique"),
            cmv=("CMV total", "sum"),
            comissao=("sale_fee", "sum"),
            frete=("custo_frete_final", "sum"),
            imposto=("imposto", "sum"),
            custo_fixo=("custo_fixo", "sum"),
            extra=("extra", "sum"),
        )
        .sort_values("date")
    )
    daily["margem_liquida_estimada"] = (
        daily["lucro_liquido_estimado"] / daily["receita"].replace(0, pd.NA) * 100
    )
    daily["margem_operacional"] = daily["lucro_operacional"] / daily["receita"].replace(0, pd.NA) * 100
    daily["margem_bruta"] = daily["lucro_bruto"] / daily["receita"].replace(0, pd.NA) * 100
    daily["ticket_medio_dia"] = daily["receita"] / daily["pedidos"].replace(0, pd.NA)
    return daily


def ads_daily_summary(ads_df: pd.DataFrame) -> pd.DataFrame:
    if ads_df.empty or "ads_data_ref" not in ads_df.columns or not ads_df["ads_data_ref"].notna().any():
        return pd.DataFrame()

    daily = (
        ads_df.dropna(subset=["ads_data_ref"])
        .groupby("ads_data_ref", as_index=False)
        .agg(
            cost=("cost", "sum"),
            revenue=("revenue", "sum"),
        )
        .sort_values("ads_data_ref")
    )
    daily["roas"] = daily["revenue"] / daily["cost"].where(daily["cost"] > 0, pd.NA)
    daily["acos"] = daily["cost"] / daily["revenue"].where(daily["revenue"] > 0, pd.NA) * 100
    return daily


def dimension_summary(df: pd.DataFrame, dimension: str, top_n: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby(dimension, dropna=False, as_index=False)
        .agg(
            receita=("receita", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
            lucro_operacional=("lucro_operacional", "sum"),
            lucro_bruto=("lucro_bruto", "sum"),
            cmv=("CMV total", "sum"),
            pedidos=("order_id", "nunique"),
            quantidade=("quantity", "sum"),
            ticket=("receita", "mean"),
        )
        .sort_values("receita", ascending=False)
        .head(top_n)
    )
    grouped["margem_liquida_estimada"] = (
        grouped["lucro_liquido_estimado"] / grouped["receita"].replace(0, pd.NA) * 100
    )
    grouped["margem_operacional"] = grouped["lucro_operacional"] / grouped["receita"].replace(0, pd.NA) * 100
    grouped["margem_bruta"] = grouped["lucro_bruto"] / grouped["receita"].replace(0, pd.NA) * 100
    return grouped


def product_summary(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby(["item_id", "SKU", "produto", "Marca", "Nome da Categoria", "FULL", "Flex"], dropna=False, as_index=False)
        .agg(
            receita=("receita", "sum"),
            CMV=("CMV total", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
            lucro_operacional=("lucro_operacional", "sum"),
            lucro_bruto=("lucro_bruto", "sum"),
            quantidade=("quantity", "sum"),
            pedidos=("order_id", "nunique"),
            cmv_unitario=("cmv_seconds", "mean"),
        )
        .sort_values("receita", ascending=False)
        .head(top_n)
    )
    grouped["margem_liquida_estimada"] = (
        grouped["lucro_liquido_estimado"] / grouped["receita"].replace(0, pd.NA) * 100
    )
    grouped["margem_operacional"] = grouped["lucro_operacional"] / grouped["receita"].replace(0, pd.NA) * 100
    grouped["margem_bruta"] = grouped["lucro_bruto"] / grouped["receita"].replace(0, pd.NA) * 100
    return grouped


def stock_sales_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Resume vendas filtradas por anuncio para cruzar com estoque atual."""

    df = ensure_columns(
        df,
        {
            "item_id": "N/D",
            "SKU": "N/D",
            "produto": "N/D",
            "Marca": "N/D",
            "Nome da Categoria": "N/D",
            "FULL": "N/D",
            "Flex": "N/D",
            "Status": "N/D",
            "quantity": 0,
            "receita": 0,
            "lucro_liquido_estimado": pd.NA,
            "LinkAnuncio": "N/D",
        },
    )
    if df.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "SKU",
                "produto",
                "Marca",
                "Nome da Categoria",
                "FULL",
                "Flex",
                "Status",
                "LinkAnuncio",
                "quantidade_periodo",
                "receita",
                "lucro_liquido_estimado",
                "margem_liquida_estimada",
            ]
        )

    grouped = (
        df.groupby(
            ["item_id", "SKU", "produto", "Marca", "Nome da Categoria", "FULL", "Flex", "Status"],
            dropna=False,
            as_index=False,
        )
        .agg(
            quantidade_periodo=("quantity", "sum"),
            receita=("receita", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
            LinkAnuncio=("LinkAnuncio", "first"),
        )
    )
    grouped["margem_liquida_estimada"] = (
        grouped["lucro_liquido_estimado"] / grouped["receita"].replace(0, pd.NA) * 100
    )
    return grouped


def build_stock_view(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> pd.DataFrame:
    """Combina estoque atual com vendas do periodo e aplica filtros globais compativeis."""

    if inventory_df.empty:
        return pd.DataFrame()

    sales = stock_sales_summary(filtered_sales)
    stock = inventory_df.copy()
    stock = stock.merge(sales, on="item_id", how="left")
    stock = ensure_columns(
        stock,
        {
            "SKU": pd.NA,
            "produto": pd.NA,
            "Marca": pd.NA,
            "Nome da Categoria": pd.NA,
            "FULL": pd.NA,
            "Flex": pd.NA,
            "Status": pd.NA,
            "LinkAnuncio": pd.NA,
            "quantidade_periodo": 0,
            "receita": 0,
            "lucro_liquido_estimado": pd.NA,
            "margem_liquida_estimada": pd.NA,
        },
    )
    stock["MLB"] = stock["item_id"]
    stock["SKU_final"] = stock["SKU"].fillna(stock["SKU_estoque"]).fillna("N/D")
    stock["produto_final"] = stock["produto"].fillna(stock["produto_estoque"]).fillna("N/D")
    stock["marca_final"] = stock["Marca"].fillna(stock["Marca_estoque"]).fillna("N/D")
    stock["categoria_final"] = stock["Nome da Categoria"].fillna(stock["Categoria_estoque"]).fillna("N/D")
    stock["FULL_final"] = stock["FULL"].fillna(stock["FULL_estoque"]).fillna("N/D")
    stock["Flex_final"] = stock["Flex"].fillna("N/D")
    stock["Status_final"] = stock["Status"].fillna(stock["status"]).fillna("N/D")
    stock["Link_final"] = stock["LinkAnuncio"].fillna(stock["Link_estoque"]).fillna("N/D")
    stock["quantidade_periodo"] = pd.to_numeric(stock["quantidade_periodo"], errors="coerce").fillna(0)
    stock["estoque_atual"] = pd.to_numeric(stock["estoque_atual"], errors="coerce")
    stock["vendidos_total"] = pd.to_numeric(stock["vendidos_total"], errors="coerce")
    stock["margem_liquida_estimada"] = pd.to_numeric(stock["margem_liquida_estimada"], errors="coerce")
    stock["lucro_liquido_estimado"] = pd.to_numeric(stock["lucro_liquido_estimado"], errors="coerce")

    marcas = filter_state.get("marcas") or []
    categorias = filter_state.get("categorias") or []
    full_values = filter_state.get("full_values") or []
    flex_values = filter_state.get("flex_values") or []
    status_values = filter_state.get("status_values") or []
    stock_status_values = filter_state.get("stock_status_values") or []
    listing_values = filter_state.get("listing_values") or []
    produto = str(filter_state.get("produto") or "")
    mlb = str(filter_state.get("mlb") or "")

    if marcas:
        stock = stock[stock["marca_final"].isin(marcas)]
    if categorias:
        stock = stock[stock["categoria_final"].isin(categorias)]
    if full_values:
        stock = stock[stock["FULL_final"].isin(full_values)]
    if flex_values:
        stock = stock[stock["Flex_final"].isin(flex_values)]
    if status_values:
        stock = stock[stock["Status_final"].isin(status_values)]
    if stock_status_values:
        stock = stock[stock["status_estoque"].isin(stock_status_values)]
    if listing_values:
        stock = stock[stock["listing_type_id"].isin(listing_values)]
    if produto:
        stock = stock[stock["produto_final"].str.contains(produto, case=False, na=False)]
    if mlb:
        stock = stock[stock["MLB"].str.contains(mlb, case=False, na=False)]

    return stock


def calculate_stock_kpis(stock_df: pd.DataFrame, selected_period: tuple[date, date]) -> dict[str, float]:
    """Calcula KPIs executivos da visao de estoque."""

    if stock_df.empty:
        return {
            "estoque_total": 0.0,
            "sem_estoque": 0.0,
            "baixo": 0.0,
            "normal": 0.0,
            "excesso": 0.0,
            "vendidos_periodo": 0.0,
            "giro_estimado": 0.0,
            "cobertura_estimada": 0.0,
        }

    start_date, end_date = selected_period
    days = max((end_date - start_date).days + 1, 1)
    estoque_total = float(stock_df["estoque_atual"].fillna(0).sum())
    vendidos_periodo = float(stock_df["quantidade_periodo"].fillna(0).sum())
    vendas_diarias = vendidos_periodo / days if days else 0.0

    return {
        "estoque_total": estoque_total,
        "sem_estoque": float((stock_df["status_estoque"] == "estoque zerado").sum()),
        "baixo": float((stock_df["status_estoque"] == "estoque baixo").sum()),
        "normal": float((stock_df["status_estoque"] == "estoque normal").sum()),
        "excesso": float((stock_df["status_estoque"] == "excesso estoque").sum()),
        "vendidos_periodo": vendidos_periodo,
        "giro_estimado": (vendidos_periodo / estoque_total) if estoque_total else 0.0,
        "cobertura_estimada": (estoque_total / vendas_diarias) if vendas_diarias else 0.0,
    }


def calculate_ads_kpis(ads_df: pd.DataFrame) -> dict[str, float]:
    """Calcula KPIs executivos de Mercado Ads."""

    if ads_df.empty:
        return {
            "cost": 0.0,
            "revenue": 0.0,
            "roas": 0.0,
            "acos": 0.0,
            "ctr": 0.0,
            "cpc": 0.0,
            "conversion_rate": 0.0,
            "clicks": 0.0,
            "impressions": 0.0,
        }

    cost = float(ads_df["cost"].fillna(0).sum())
    revenue = float(ads_df["revenue"].fillna(0).sum())
    clicks = float(ads_df["clicks"].fillna(0).sum())
    impressions = float(ads_df["impressions"].fillna(0).sum())
    units = float(ads_df["units"].fillna(0).sum())

    return {
        "cost": cost,
        "revenue": revenue,
        "roas": (revenue / cost) if cost else 0.0,
        "acos": (cost / revenue * 100) if revenue else 0.0,
        "ctr": (clicks / impressions * 100) if impressions else 0.0,
        "cpc": (cost / clicks) if clicks else 0.0,
        "conversion_rate": (units / clicks * 100) if clicks else 0.0,
        "clicks": clicks,
        "impressions": impressions,
    }


def ads_temporal_coverage(
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None,
) -> dict[str, object]:
    """Mede cobertura real de Ads e estima lacunas somente quando ha dados reais no periodo."""

    real_value = float(ads_df["cost"].fillna(0).sum()) if not ads_df.empty and "cost" in ads_df.columns else 0.0
    if not selected_period:
        ads_min, ads_max = ads_available_period(ads_df)
        return {
            "ads_data_inicio": ads_min,
            "ads_data_fim": ads_max,
            "periodo_filtro_inicio": None,
            "periodo_filtro_fim": None,
            "dias_cobertos": 0,
            "dias_faltantes": 0,
            "dias_periodo": 0,
            "cobertura_ads_percentual": 100.0 if real_value else 0.0,
            "status_cobertura_ads": "Completo" if real_value else "Sem dados",
            "ads_real": real_value,
            "ads_estimado": 0.0,
            "ads_total_ajustado": real_value,
            "ads_fonte": "Real API ML" if real_value else "Sem dados",
        }

    start_date, end_date = selected_period
    period_days = max((end_date - start_date).days + 1, 1)
    expected_days = {start_date + timedelta(days=offset) for offset in range(period_days)}
    daily = ads_daily_costs(ads_df)
    if daily.empty:
        return {
            "ads_data_inicio": None,
            "ads_data_fim": None,
            "periodo_filtro_inicio": start_date,
            "periodo_filtro_fim": end_date,
            "dias_cobertos": 0,
            "dias_faltantes": period_days,
            "dias_periodo": period_days,
            "cobertura_ads_percentual": 0.0,
            "status_cobertura_ads": "Sem dados",
            "ads_real": 0.0,
            "ads_estimado": 0.0,
            "ads_total_ajustado": 0.0,
            "ads_fonte": "Sem dados",
        }

    covered_days = set(daily["ads_data_ref"]) & expected_days
    covered_count = len(covered_days)
    missing_days = max(period_days - covered_count, 0)
    coverage_pct = covered_count / period_days * 100 if period_days else 0.0
    daily_average = float(daily["cost"].mean()) if not daily.empty else 0.0
    estimated = daily_average * missing_days if covered_count and coverage_pct < 100 else 0.0
    if coverage_pct >= 100:
        status, source = "Completo", "Real API ML"
    elif covered_count > 0:
        status, source = "Parcial", "Real + estimado por media diaria"
    else:
        status, source = "Sem dados", "Sem dados"

    return {
        "ads_data_inicio": min(covered_days) if covered_days else None,
        "ads_data_fim": max(covered_days) if covered_days else None,
        "periodo_filtro_inicio": start_date,
        "periodo_filtro_fim": end_date,
        "dias_cobertos": covered_count,
        "dias_faltantes": missing_days,
        "dias_periodo": period_days,
        "cobertura_ads_percentual": coverage_pct,
        "status_cobertura_ads": status,
        "ads_real": real_value,
        "ads_estimado": estimated,
        "ads_total_ajustado": real_value + estimated,
        "ads_fonte": source,
    }


def calculate_ads_kpis_adjusted(ads_df: pd.DataFrame, coverage: dict[str, object]) -> dict[str, float]:
    kpis = calculate_ads_kpis(ads_df)
    adjusted_cost = float(coverage.get("ads_total_ajustado") or 0.0)
    revenue = float(kpis["revenue"] or 0.0)
    clicks = float(kpis["clicks"] or 0.0)
    impressions = float(kpis["impressions"] or 0.0)
    units = float(ads_df["units"].fillna(0).sum()) if not ads_df.empty and "units" in ads_df.columns else 0.0
    kpis.update(
        {
            "cost_real": float(coverage.get("ads_real") or 0.0),
            "cost_adjusted": adjusted_cost,
            "estimated_cost": float(coverage.get("ads_estimado") or 0.0),
            "roas_adjusted": (revenue / adjusted_cost) if adjusted_cost else 0.0,
            "acos_adjusted": (adjusted_cost / revenue * 100) if revenue else 0.0,
            "ctr": (clicks / impressions * 100) if impressions else 0.0,
            "cpc_adjusted": (adjusted_cost / clicks) if clicks else 0.0,
            "conversion_rate": (units / clicks * 100) if clicks else 0.0,
            "conversions": units,
        }
    )
    return kpis


def classify_ads_campaign(row: pd.Series) -> tuple[str, str]:
    roas = float(row.get("roas") or 0.0)
    acos = float(row.get("acos") or 0.0)
    if roas >= 10 and acos <= 10:
        return "Excelente", "Escalar orcamento"
    if roas >= 6 and acos <= 16:
        return "Boa", "Manter"
    if roas >= 3 and acos <= 25:
        return "Atencao", "Revisar palavras-chave/anuncio"
    if roas < 3 and acos > 25:
        return "Ruim", "Pausar campanha"
    return "Ruim", "Reduzir investimento"


def ads_campaign_summary(ads_df: pd.DataFrame) -> pd.DataFrame:
    if ads_df.empty:
        return pd.DataFrame()
    campaign = (
        ads_df.groupby("campaign_name", as_index=False)
        .agg(
            cost=("cost", "sum"),
            revenue=("revenue", "sum"),
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            orders=("orders", "sum"),
            units=("units", "sum"),
        )
        .sort_values("cost", ascending=False)
    )
    campaign["roas"] = campaign["revenue"] / campaign["cost"].where(campaign["cost"] > 0, pd.NA)
    campaign["acos"] = campaign["cost"] / campaign["revenue"].where(campaign["revenue"] > 0, pd.NA) * 100
    campaign["ctr"] = campaign["clicks"] / campaign["impressions"].where(campaign["impressions"] > 0, pd.NA) * 100
    campaign["cpc"] = campaign["cost"] / campaign["clicks"].where(campaign["clicks"] > 0, pd.NA)
    campaign["conversion_rate"] = campaign["units"] / campaign["clicks"].where(campaign["clicks"] > 0, pd.NA) * 100
    classifications = campaign.apply(classify_ads_campaign, axis=1)
    campaign["status_campanha"] = [item[0] for item in classifications]
    campaign["acao_recomendada"] = [item[1] for item in classifications]
    return campaign.fillna(0)


def ads_status_color(status: str) -> str:
    return {
        "Excelente": "#22C55E",
        "Boa": "#0F766E",
        "Atencao": "#D97706",
        "Ruim": "#DC2626",
    }.get(status, "#64748B")


def ads_margin_impact(kpis: dict[str, float], financial_df: pd.DataFrame) -> float:
    receita_total = first_existing_numeric_sum(financial_df, ["receita", "faturamento", "faturamento_seconds"])
    return (float(kpis.get("cost_adjusted") or 0.0) / receita_total * 100) if receita_total else 0.0


def build_ads_financial_reconciliation(
    ads_kpis: dict[str, float],
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None,
    all_ads_df: pd.DataFrame | None,
) -> pd.DataFrame:
    financials = calculate_executive_financials(financial_df, ads_df, selected_period, all_ads_df)
    ads_tab_value = float(ads_kpis.get("cost_adjusted") or 0.0)
    finance_value = float(financials.get("ads_value") or 0.0)
    return pd.DataFrame(
        [
            {
                "Metrica": "Investimento Ads",
                "Ads & Performance": ads_tab_value,
                "Financeiro Executivo": finance_value,
                "Diferenca": ads_tab_value - finance_value,
            }
        ]
    )


def build_ads_alerts_executive(
    campaign: pd.DataFrame,
    kpis: dict[str, float],
    coverage: dict[str, object],
    margin_impact_pct: float,
    daily: pd.DataFrame,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    if margin_impact_pct > META_OPERACIONAL_ADS_PERCENTUAL:
        excess = float(kpis.get("cost_adjusted") or 0.0) * (margin_impact_pct - META_OPERACIONAL_ADS_PERCENTUAL) / max(margin_impact_pct, 0.01)
        alerts.append(
            {
                "criticidade": "Alta" if margin_impact_pct > 5 else "Media",
                "impacto": br_money(excess),
                "recomendacao": "Revisar campanhas ate o investimento voltar para a meta de 3% da receita total.",
                "alerta": "ACOS acima da meta de 3% de investimento sobre receita total.",
            }
        )
    if str(coverage.get("status_cobertura_ads")) == "Parcial":
        alerts.append(
            {
                "criticidade": "Media",
                "impacto": br_money(float(coverage.get("ads_estimado") or 0.0)),
                "recomendacao": "Ler investimento com estimativa temporal e evitar cortes por ROAS isolado.",
                "alerta": (
                    f"Ads esta parcial no periodo: {coverage.get('dias_cobertos')} dias cobertos e "
                    f"{coverage.get('dias_faltantes')} dias faltantes."
                ),
            }
        )
    if not campaign.empty:
        poor = campaign[(campaign["status_campanha"] == "Ruim") & (campaign["cost"] > 0)].sort_values("cost", ascending=False)
        if not poor.empty:
            row = poor.iloc[0]
            alerts.append(
                {
                    "criticidade": "Alta",
                    "impacto": br_money(float(row["cost"])),
                    "recomendacao": safe_text(row["acao_recomendada"]),
                    "alerta": f"Campanha {safe_text(row['campaign_name'])} consome verba e tem ROAS baixo.",
                }
            )
        scalable = campaign[campaign["status_campanha"].isin(["Excelente", "Boa"])].sort_values("roas", ascending=False)
        if not scalable.empty:
            row = scalable.iloc[0]
            alerts.append(
                {
                    "criticidade": "Oportunidade",
                    "impacto": br_money(float(row["revenue"])),
                    "recomendacao": "Avaliar aumento gradual de orcamento.",
                    "alerta": f"Campanha {safe_text(row['campaign_name'])} tem ROAS alto e pode receber mais orcamento.",
                }
            )
    if len(daily) >= 6 and "revenue" in daily.columns:
        revenue = pd.to_numeric(daily["revenue"], errors="coerce").fillna(0)
        recent = float(revenue.tail(3).mean())
        previous = float(revenue.iloc[-6:-3].mean())
        if previous > 0 and recent < previous * 0.8:
            alerts.append(
                {
                    "criticidade": "Media",
                    "impacto": br_money(previous - recent),
                    "recomendacao": "Investigar queda de receita atribuida nos ultimos dias.",
                    "alerta": "Receita atribuida caiu nos ultimos dias.",
                }
            )
    if not alerts:
        alerts.append(
            {
                "criticidade": "Saudavel",
                "impacto": "N/D",
                "recomendacao": "Manter acompanhamento de ROAS, ACOS e cobertura.",
                "alerta": "Sem alerta critico de Ads para o periodo.",
            }
        )
    return alerts[:5]


def render_ads_kpi_card(
    label: str,
    value: str,
    color: str = "#0F766E",
    detail: str = "",
    status: str = "",
    meta: str = "",
) -> str:
    tooltip = ADS_KPI_TOOLTIPS.get(label, "")
    title_attr = f' title="{html.escape(tooltip, quote=True)}"' if tooltip else ""
    help_icon = (
        f'<span class="kpi-help"{title_attr} aria-label="Explicacao do KPI">&#8505;</span>'
        if tooltip
        else ""
    )
    status_html = f'<div class="ads-kpi-status">{html.escape(status)}</div>' if status else ""
    meta_html = f'<div class="ads-kpi-meta">{html.escape(meta)}</div>' if meta else ""
    return (
        f'<div class="ads-kpi-card" style="--ads-color:{color};">'
        f'<div class="ads-kpi-label"{title_attr}>{html.escape(label)}{help_icon}</div>'
        f'<div class="ads-kpi-value">{html.escape(value)}</div>'
        f'<div class="ads-kpi-detail">{html.escape(detail)}</div>'
        f"{status_html}{meta_html}"
        "</div>"
    )


def render_ads_status_badge(status: str) -> str:
    color = ads_status_color(status)
    return f'<span class="ads-status-badge" style="--ads-status-color:{color};">{html.escape(status)}</span>'


def ads_help_icon(tooltip: str) -> str:
    if not tooltip:
        return ""
    return (
        f'<span class="kpi-help" title="{html.escape(tooltip, quote=True)}" '
        'aria-label="Explicacao do indicador">&#8505;</span>'
    )


def render_ads_section_title(title: str, tooltip: str = "") -> None:
    # Prioridade: tooltip passado diretamente > ADS_SECTION_TOOLTIPS > vazio
    resolved_tooltip = tooltip if tooltip else ADS_SECTION_TOOLTIPS.get(title, "")
    st.markdown(
        f'<div class="section-title">{html.escape(title)}{ads_help_icon(resolved_tooltip)}</div>',
        unsafe_allow_html=True,
    )


def ads_goal_status(label: str, value: float) -> tuple[str, str, str]:
    if label == "ROAS":
        if value >= 6:
            return "🟢 Dentro da meta", "#0F766E", "Meta >= 6"
        if value >= 5:
            return "🟡 Proximo da meta", "#D97706", "Meta >= 6"
        return "🔴 Fora da meta", "#DC2626", "Meta >= 6"
    if label == "ACOS":
        if value <= 15 and value > 0:
            return "🟢 Dentro da meta", "#0F766E", "Meta <= 15%"
        if value <= 20 and value > 0:
            return "🟡 Proximo da meta", "#D97706", "Meta <= 15%"
        return "🔴 Fora da meta", "#DC2626", "Meta <= 15%"
    if label == "CTR":
        if value >= 0.25:
            return "🟢 Dentro da meta", "#0F766E", "Meta >= 0,25%"
        if value >= 0.20:
            return "🟡 Proximo da meta", "#D97706", "Meta >= 0,25%"
        return "🔴 Fora da meta", "#DC2626", "Meta >= 0,25%"
    if label == "Conversao":
        if value >= 2.5:
            return "🟢 Dentro da meta", "#0F766E", "Meta >= 2,5%"
        if value >= 2.0:
            return "🟡 Proximo da meta", "#D97706", "Meta >= 2,5%"
        return "🔴 Fora da meta", "#DC2626", "Meta >= 2,5%"
    if label == "Cobertura dos Dados":
        if value >= 95:
            return "🟢 Dentro da meta", "#0F766E", "Meta 100%"
        if value >= 60:
            return "🟡 Proximo da meta", "#D97706", "Meta 100%"
        return "🔴 Fora da meta", "#DC2626", "Meta 100%"
    if label == "Impacto na Margem":
        if value <= META_OPERACIONAL_ADS_PERCENTUAL and value > 0:
            return "🟢 Dentro da meta", "#0F766E", "Meta <= 3% da receita"
        if value <= 5 and value > 0:
            return "🟡 Proximo da meta", "#D97706", "Meta <= 3% da receita"
        return "🔴 Fora da meta", "#DC2626", "Meta <= 3% da receita"
    return "Monitoramento", "#64748B", "Sem meta fixa"


def ads_health_score(kpis: dict[str, float], coverage: dict[str, object]) -> dict[str, object]:
    roas = float(kpis.get("roas_adjusted") or 0.0)
    acos = float(kpis.get("acos_adjusted") or 0.0)
    ctr = float(kpis.get("ctr") or 0.0)
    conversion = float(kpis.get("conversion_rate") or 0.0)
    coverage_pct = float(coverage.get("cobertura_ads_percentual") or 0.0)
    if float(kpis.get("cost_adjusted") or 0.0) <= 0 and float(kpis.get("revenue") or 0.0) <= 0:
        components = {"ROAS": 0.0, "ACOS": 0.0, "CTR": 0.0, "Conversao": 0.0, "Cobertura": bounded_score(coverage_pct)}
        return {"score": bounded_score(coverage_pct * 0.15), "status": "Critico", "color": "#DC2626", "components": components}
    components = {
        "ROAS": score_from_thresholds(roas, [(10, 100), (6, 82), (3, 50), (0, 20)]),
        "ACOS": score_from_thresholds(acos, [(10, 100), (15, 85), (25, 55), (999, 20)], lower_is_better=True),
        "CTR": score_from_thresholds(ctr, [(0.50, 100), (0.25, 82), (0.15, 55), (0, 25)]),
        "Conversao": score_from_thresholds(conversion, [(5, 100), (2.5, 82), (1.5, 55), (0, 25)]),
        "Cobertura": bounded_score(coverage_pct),
    }
    weights = {"ROAS": 0.30, "ACOS": 0.25, "CTR": 0.15, "Conversao": 0.15, "Cobertura": 0.15}
    score = bounded_score(sum(components[key] * weights[key] for key in weights))
    if score >= 80:
        status, color = "Excelente", "#22C55E"
    elif score >= 60:
        status, color = "Saudavel", "#0F766E"
    elif score >= 40:
        status, color = "Atencao", "#D97706"
    else:
        status, color = "Critico", "#DC2626"
    return {"score": score, "status": status, "color": color, "components": components}


def ads_health_gauge(score_info: dict[str, object]) -> go.Figure:
    score = float(score_info["score"])
    color = str(score_info["color"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34, "color": color}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(148,163,184,.35)"},
                "bar": {"color": color, "thickness": .28},
                "bgcolor": "rgba(15,23,42,.16)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(220,38,38,.18)"},
                    {"range": [40, 60], "color": "rgba(217,119,6,.18)"},
                    {"range": [60, 80], "color": "rgba(15,118,110,.16)"},
                    {"range": [80, 100], "color": "rgba(34,197,94,.20)"},
                ],
                "threshold": {"line": {"color": color, "width": 4}, "thickness": .78, "value": score},
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        height=250,
        margin=dict(l=8, r=8, t=12, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
    )
    return fig


def ads_quadrant_label(roas: float, cost: float, investment_threshold: float) -> tuple[str, str]:
    high_roas = roas >= 6
    high_investment = cost >= investment_threshold
    if high_roas and high_investment:
        return "Escalar", "Alto ROAS + alto investimento"
    if high_roas and not high_investment:
        return "Oportunidade", "Alto ROAS + baixo investimento"
    if not high_roas and high_investment:
        return "Revisar", "Baixo ROAS + alto investimento"
    return "Baixa Prioridade", "Baixo ROAS + baixo investimento"


def ads_campaign_quadrant_chart(campaign: pd.DataFrame) -> go.Figure:
    if campaign.empty:
        return empty_fig("Quadrante de Campanhas")
    chart = campaign.copy()
    chart["cost"] = pd.to_numeric(chart["cost"], errors="coerce").fillna(0)
    chart["revenue"] = pd.to_numeric(chart["revenue"], errors="coerce").fillna(0)
    chart["roas"] = pd.to_numeric(chart["roas"], errors="coerce").fillna(0)
    chart["acos"] = pd.to_numeric(chart["acos"], errors="coerce").fillna(0)
    visual_cap = 30.0
    roas_p95 = chart.loc[chart["roas"] > 0, "roas"].quantile(0.95)
    if pd.notna(roas_p95) and roas_p95 > 0:
        visual_cap = min(visual_cap, max(6.0, float(roas_p95)))
    chart["roas_plot"] = chart["roas"].clip(upper=visual_cap)
    chart["roas_limitado"] = chart["roas"] > visual_cap
    median_investment = chart.loc[chart["cost"] > 0, "cost"].median()
    investment_threshold = float(median_investment) if pd.notna(median_investment) else 0.0
    if investment_threshold <= 0:
        mean_investment = chart["cost"].mean()
        investment_threshold = float(mean_investment) if pd.notna(mean_investment) and mean_investment > 0 else 1.0
    labels = chart.apply(lambda row: ads_quadrant_label(float(row["roas"]), float(row["cost"]), investment_threshold), axis=1)
    chart["quadrante"] = [item[0] for item in labels]
    chart["quadrante_desc"] = [item[1] for item in labels]
    chart["investimento_fmt"] = chart["cost"].map(br_money)
    chart["receita_fmt"] = chart["revenue"].map(br_money)
    chart["roas_fmt"] = chart["roas"].map(lambda value: br_number(value, 2))
    chart["roas_visual_note"] = chart["roas_limitado"].map(
        {True: "ROAS real exibido no limite visual", False: "ROAS real dentro da escala visual"}
    )
    chart["acos_fmt"] = chart["acos"].map(br_percent)
    color_map = {
        "Escalar": "#22C55E",
        "Oportunidade": "#2563EB",
        "Revisar": "#DC2626",
        "Baixa Prioridade": "#64748B",
    }
    fig = px.scatter(
        chart,
        x="roas_plot",
        y="cost",
        size="revenue",
        color="quadrante",
        color_discrete_map=color_map,
        hover_name="campaign_name",
        custom_data=[
            "investimento_fmt",
            "receita_fmt",
            "roas_fmt",
            "acos_fmt",
            "acao_recomendada",
            "quadrante_desc",
            "roas_visual_note",
            "quadrante",
        ],
        size_max=36,
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Investimento: %{customdata[0]}<br>"
            "Receita Ads: %{customdata[1]}<br>"
            "ROAS real: %{customdata[2]}<br>"
            "ACOS: %{customdata[3]}<br>"
            "Status do quadrante: %{customdata[7]} - %{customdata[5]}<br>"
            "Acao recomendada: %{customdata[4]}<br>"
            "%{customdata[6]}<extra></extra>"
        )
    )
    fig.add_vline(x=6, line_width=1, line_dash="dash", line_color="rgba(148,163,184,.55)")
    fig.add_hline(y=investment_threshold, line_width=1, line_dash="dash", line_color="rgba(148,163,184,.55)")
    fig.add_annotation(x=6, y=1.02, xref="x", yref="paper", text="Meta ROAS 6", showarrow=False, font_size=11)
    fig.add_annotation(
        x=1.01,
        y=investment_threshold,
        xref="paper",
        yref="y",
        text="Investimento mediano",
        showarrow=False,
        font_size=11,
    )
    y_max = float(chart["cost"].max() or investment_threshold or 1.0)
    y_low = investment_threshold / 2 if investment_threshold else y_max * 0.25
    y_high = investment_threshold + (y_max - investment_threshold) * 0.62 if y_max > investment_threshold else y_max * 0.82
    x_left = max(0.4, min(3.0, visual_cap * 0.22))
    x_right = min(visual_cap * 0.82, max(6.6, visual_cap * 0.72))
    quadrant_annotations = [
        (x_right, y_high, "Escalar", "#22C55E"),
        (x_right, y_low, "Oportunidade", "#2563EB"),
        (x_left, y_high, "Revisar", "#DC2626"),
        (x_left, y_low, "Baixa prioridade", "#64748B"),
    ]
    for x_pos, y_pos, text, color in quadrant_annotations:
        fig.add_annotation(
            x=x_pos,
            y=y_pos,
            text=text,
            showarrow=False,
            font=dict(size=12, color=color),
            bgcolor="rgba(15,23,42,.68)",
            bordercolor="rgba(148,163,184,.18)",
            borderwidth=1,
            borderpad=4,
        )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text="ROAS visual", range=[0, visual_cap * 1.04])
    fig.update_yaxes(title_text="Investimento")
    return layout_chart(fig, "ROAS x Investimento por campanha", 520)


def ads_budget_share_chart(campaign: pd.DataFrame) -> go.Figure:
    if campaign.empty:
        return empty_fig("Top campanhas por investimento")
    chart = campaign.copy()
    chart["cost"] = pd.to_numeric(chart["cost"], errors="coerce").fillna(0)
    chart["revenue"] = pd.to_numeric(chart["revenue"], errors="coerce").fillna(0)
    total_cost = float(chart["cost"].sum())
    if total_cost <= 0:
        return empty_fig("Top campanhas por investimento")
    chart = chart.sort_values("cost", ascending=False).head(10).sort_values("cost")
    chart["participacao"] = chart["cost"] / total_cost * 100
    chart["investimento_fmt"] = chart["cost"].map(br_money)
    chart["receita_fmt"] = chart["revenue"].map(br_money)
    chart["participacao_fmt"] = chart["participacao"].map(br_percent)
    fig = px.bar(
        chart,
        x="cost",
        y="campaign_name",
        orientation="h",
        color="participacao",
        color_continuous_scale="Tealgrn",
        custom_data=["investimento_fmt", "participacao_fmt", "receita_fmt"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Investimento: %{customdata[0]}<br>"
            "Participacao: %{customdata[1]}<br>"
            "Receita gerada: %{customdata[2]}<extra></extra>"
        )
    )
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(title_text="Investimento")
    fig.update_yaxes(title_text=None)
    return layout_chart(fig, "Top campanhas por investimento", 410)


def ads_opportunities_table(campaign: pd.DataFrame) -> pd.DataFrame:
    if campaign.empty:
        return pd.DataFrame()
    data = campaign.copy()
    data["cost"] = pd.to_numeric(data["cost"], errors="coerce").fillna(0)
    data["roas"] = pd.to_numeric(data["roas"], errors="coerce").fillna(0)
    data["acos"] = pd.to_numeric(data["acos"], errors="coerce").fillna(0)
    data["recomendacao_executiva"] = "Monitorar"
    data.loc[(data["roas"] > 10) & (data["acos"] < 10), "recomendacao_executiva"] = "Aumentar investimento"
    data.loc[(data["roas"] >= 6) & (data["roas"] <= 10), "recomendacao_executiva"] = "Manter"
    data.loc[data["roas"] < 3, "recomendacao_executiva"] = "Revisar"
    data = data[data["recomendacao_executiva"].isin(["Aumentar investimento", "Manter", "Revisar"])]
    if data.empty:
        return pd.DataFrame()
    priority = {"Aumentar investimento": 0, "Revisar": 1, "Manter": 2}
    data["prioridade"] = data["recomendacao_executiva"].map(priority)
    data = data.sort_values(["prioridade", "cost"], ascending=[True, False]).head(12)
    display = data[["campaign_name", "roas", "acos", "cost", "recomendacao_executiva"]].rename(
        columns={
            "campaign_name": "Campanha",
            "roas": "ROAS",
            "acos": "ACOS",
            "cost": "Investimento",
            "recomendacao_executiva": "Recomendacao",
        }
    )
    display["ROAS"] = display["ROAS"].map(lambda value: br_number(value, 2))
    display["ACOS"] = display["ACOS"].map(br_percent)
    display["Investimento"] = display["Investimento"].map(br_money)
    return display


def ads_margin_contribution(
    kpis: dict[str, float],
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None,
    all_ads_df: pd.DataFrame | None,
) -> dict[str, float]:
    revenue = float(kpis.get("revenue") or 0.0)
    investment = float(kpis.get("cost_adjusted") or 0.0)
    margin_generated = revenue - investment
    result_final = 0.0
    if financial_df is not None and not financial_df.empty:
        result_final = float(
            calculate_executive_financials(financial_df, ads_df, selected_period, all_ads_df).get(
                "resultado_operacional_valor"
            )
            or 0.0
        )
    participation = (margin_generated / abs(result_final) * 100) if result_final else 0.0
    return {
        "receita_atribuida": revenue,
        "investimento_ads": investment,
        "margem_gerada": margin_generated,
        "resultado_final": result_final,
        "participacao_resultado": participation,
    }


def ads_opportunity_radar(
    kpis: dict[str, float],
    coverage: dict[str, object],
    campaign: pd.DataFrame,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    roas = float(kpis.get("roas_adjusted") or 0.0)
    ctr = float(kpis.get("ctr") or 0.0)
    conversion = float(kpis.get("conversion_rate") or 0.0)
    if roas >= 6:
        items.append({"nivel": "Positivo", "ponto": "ROAS acima da meta", "detalhe": f"ROAS atual: {br_number(roas, 2)}"})
    else:
        items.append({"nivel": "Atencao" if roas >= 3 else "Critico", "ponto": "ROAS abaixo da meta", "detalhe": f"ROAS atual: {br_number(roas, 2)}"})
    if conversion >= 2.5:
        items.append({"nivel": "Positivo", "ponto": "Conversao acima da meta", "detalhe": f"Conversao: {br_percent(conversion)}"})
    else:
        items.append({"nivel": "Atencao", "ponto": "Conversao pede acompanhamento", "detalhe": f"Conversao: {br_percent(conversion)}"})
    if ctr < 0.25:
        items.append({"nivel": "Atencao", "ponto": "CTR abaixo da meta", "detalhe": f"CTR atual: {br_percent(ctr)}"})
    else:
        items.append({"nivel": "Positivo", "ponto": "CTR dentro da meta", "detalhe": f"CTR atual: {br_percent(ctr)}"})
    if str(coverage.get("status_cobertura_ads")) != "Completo":
        items.append(
            {
                "nivel": "Atencao" if coverage.get("status_cobertura_ads") == "Parcial" else "Critico",
                "ponto": "Cobertura de dados incompleta",
                "detalhe": f"{coverage.get('dias_cobertos')} de {coverage.get('dias_periodo')} dias cobertos",
            }
        )
    if not campaign.empty:
        high_spend_low_return = campaign[(campaign["cost"] > campaign["cost"].median()) & (campaign["roas"] < 3)].sort_values("cost", ascending=False)
        if not high_spend_low_return.empty:
            row = high_spend_low_return.iloc[0]
            items.append(
                {
                    "nivel": "Critico",
                    "ponto": "Campanha com gasto elevado e baixo retorno",
                    "detalhe": f"{safe_text(row['campaign_name'])}: {br_money(float(row['cost']))} | ROAS {br_number(float(row['roas']), 2)}",
                }
            )
    return items[:6]


def build_product_alert_base(filtered_sales: pd.DataFrame) -> pd.DataFrame:
    """Consolida vendas filtradas por produto para alertas executivos."""

    if filtered_sales.empty:
        return pd.DataFrame()

    products = (
        filtered_sales.groupby(
            ["item_id", "SKU", "produto", "Marca", "Nome da Categoria"],
            dropna=False,
            as_index=False,
        )
        .agg(
            receita=("receita", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
            quantidade_periodo=("quantity", "sum"),
            cmv_unitario=("cmv_seconds", "mean"),
            LinkAnuncio=("LinkAnuncio", "first"),
        )
    )
    products["margem_liquida_estimada"] = (
        products["lucro_liquido_estimado"] / products["receita"].replace(0, pd.NA) * 100
    )
    return products


def normalize_alert_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas padrao usadas nas tabelas de alertas."""

    normalized = ensure_columns(
        df,
        {
            "nivel": "N/D",
            "tipo_alerta": "N/D",
            "prioridade": "N/D",
            "impacto_financeiro_estimado": 0.0,
            "MLB": "N/D",
            "SKU": "N/D",
            "produto": "N/D",
            "marca": "N/D",
            "categoria": "N/D",
            "receita": pd.NA,
            "margem": pd.NA,
            "lucro": pd.NA,
            "estoque": pd.NA,
            "campanha": "N/D",
            "ACOS": pd.NA,
            "ROAS": pd.NA,
            "LinkAnuncio": "N/D",
        },
    )
    normalized = normalized.copy()
    text_columns = [
        "nivel",
        "tipo_alerta",
        "prioridade",
        "MLB",
        "SKU",
        "produto",
        "marca",
        "categoria",
        "campanha",
        "LinkAnuncio",
        "acao_recomendada",
        "responsavel_sugerido",
        "status_acao",
        "prazo_sugerido",
    ]
    numeric_columns = [
        "impacto_financeiro_estimado",
        "receita",
        "margem",
        "lucro",
        "estoque",
        "ACOS",
        "ROAS",
    ]
    for column in text_columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(safe_text)
    for column in numeric_columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(safe_number)

    return normalized


def prioritize_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica prioridade e impacto financeiro estimado aos alertas."""

    if df.empty:
        return normalize_alert_columns(df)

    df = normalize_alert_columns(df)
    df = df.copy()

    def classify(row: pd.Series) -> tuple[str, float]:
        alert_type = safe_text(row.get("tipo_alerta"))
        receita = safe_number(row.get("receita"))
        lucro = safe_number(row.get("lucro"))
        margem = safe_number(row.get("margem"))

        if alert_type in {"Lucro negativo", "Margem liquida negativa"}:
            return "Alta", abs(lucro)
        if alert_type == "Gasto sem conversao":
            return "Alta", receita if receita > 0 else 0.0
        if alert_type == "Estoque zerado com vendas recentes":
            return "Alta", receita if receita > 0 else abs(lucro)
        if alert_type == "Produto sem CMV" and receita > 0:
            return "Alta", receita
        if alert_type == "Margem liquida baixa":
            return "Media", max(0.0, receita * max(0.0, (5 - margem) / 100))
        if alert_type in {"ACOS muito alto", "ROAS ruim", "Estoque baixo com alta venda"}:
            return "Media", receita if receita > 0 else abs(lucro)
        if alert_type in {"Produto sem marca", "Produto sem categoria", "Excesso de estoque", "Cadastro incompleto"}:
            return "Baixa", 0.0
        if alert_type == "Margem pos Ads baixa":
            return "Media", abs(lucro)
        return "Baixa", 0.0

    classified = df.apply(classify, axis=1, result_type="expand")
    df["prioridade"] = classified[0]
    df["impacto_financeiro_estimado"] = pd.to_numeric(classified[1], errors="coerce").fillna(0)
    priority_order = {"Alta": 0, "Media": 1, "Baixa": 2, "N/D": 3}
    df["_prioridade_ordem"] = df["prioridade"].map(priority_order).fillna(3)
    return df.sort_values(
        ["_prioridade_ordem", "impacto_financeiro_estimado"],
        ascending=[True, False],
    ).drop(columns="_prioridade_ordem")


def enrich_action_plan(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona plano de acao sugerido a cada alerta priorizado."""

    if df.empty:
        return ensure_columns(
            df,
            {
                "acao_recomendada": "N/D",
                "responsavel_sugerido": "N/D",
                "status_acao": "Pendente",
                "prazo_sugerido": "N/D",
            },
        )

    df = df.copy()

    def action_for(alert_type: object) -> tuple[str, str, str]:
        alert_type = safe_text(alert_type)
        if alert_type in {"Margem liquida negativa", "Lucro negativo", "Margem liquida baixa"}:
            return (
                "Revisar preco, CMV, frete e comissao. Avaliar reajuste ou pausa do anuncio.",
                "Comercial / Precificacao",
                "Hoje",
            )
        if alert_type == "Gasto sem conversao":
            return (
                "Pausar campanha ou reduzir orcamento. Revisar palavras/produtos patrocinados.",
                "Marketing / Mercado Ads",
                "Hoje",
            )
        if alert_type in {"ACOS muito alto", "ROAS ruim"}:
            return (
                "Revisar estrategia da campanha, orcamento e produtos anunciados.",
                "Marketing / Mercado Ads",
                "24h",
            )
        if alert_type == "Produto sem CMV":
            return (
                "Cadastrar ou corrigir CMV na Seconds.",
                "Cadastro / Financeiro",
                "Hoje",
            )
        if alert_type == "Estoque zerado com vendas recentes":
            return (
                "Priorizar reposicao ou pausar anuncio ate regularizar estoque.",
                "Compras / Operacao",
                "Hoje",
            )
        if alert_type == "Estoque baixo com alta venda":
            return (
                "Avaliar compra urgente e reposicao Full/Flex.",
                "Compras",
                "24h",
            )
        if alert_type in {"Produto parado", "Excesso de estoque"}:
            return (
                "Avaliar promocao, Ads ou liquidacao controlada.",
                "Comercial",
                "7 dias",
            )
        if alert_type in {"Produto sem marca", "Produto sem categoria", "Cadastro incompleto"}:
            return (
                "Corrigir cadastro do produto.",
                "Cadastro",
                "7 dias",
            )
        if alert_type == "Margem pos Ads baixa":
            return (
                "Revisar rentabilidade apos Ads e ajustar investimento, preco ou mix.",
                "Comercial / Marketing",
                "24h",
            )
        return ("Avaliar alerta e definir acao corretiva.", "Gestao", "7 dias")

    actions = df["tipo_alerta"].fillna("N/D").map(action_for)
    df["acao_recomendada"] = actions.map(lambda item: item[0])
    df["responsavel_sugerido"] = actions.map(lambda item: item[1])
    df["prazo_sugerido"] = actions.map(lambda item: item[2])
    df["status_acao"] = "Pendente"
    return df


def build_financial_alerts(filtered_sales: pd.DataFrame, ads_df: pd.DataFrame) -> pd.DataFrame:
    """Cria alertas financeiros de margem e lucro."""

    rows: list[dict[str, object]] = []
    products = build_product_alert_base(filtered_sales)
    post_ads = calculate_post_ads_values(filtered_sales, ads_df)
    revenue_total = post_ads["faturamento"]
    lucro_pos_ads = post_ads["lucro_pos_ads"]
    margem_pos_ads = post_ads["margem_pos_ads"]

    if margem_pos_ads < 5:
        rows.append(
            {
                "nivel": "critico",
                "tipo_alerta": "Margem pos Ads baixa",
                "receita": revenue_total,
                "margem": margem_pos_ads,
                "lucro": lucro_pos_ads,
            }
        )

    if not products.empty:
        for row in products[products["margem_liquida_estimada"].fillna(0) < 0].itertuples(index=False):
            rows.append(
                {
                    "nivel": "critico",
                    "tipo_alerta": "Margem liquida negativa",
                    "MLB": row.item_id,
                    "SKU": row.SKU,
                    "produto": row.produto,
                    "marca": row.Marca,
                    "categoria": row._4,
                    "receita": row.receita,
                    "margem": row.margem_liquida_estimada,
                    "lucro": row.lucro_liquido_estimado,
                    "LinkAnuncio": row.LinkAnuncio,
                }
            )
        for row in products[
            products["margem_liquida_estimada"].fillna(0).between(0, 5, inclusive="left")
        ].itertuples(index=False):
            rows.append(
                {
                    "nivel": "atencao",
                    "tipo_alerta": "Margem liquida baixa",
                    "MLB": row.item_id,
                    "SKU": row.SKU,
                    "produto": row.produto,
                    "marca": row.Marca,
                    "categoria": row._4,
                    "receita": row.receita,
                    "margem": row.margem_liquida_estimada,
                    "lucro": row.lucro_liquido_estimado,
                    "LinkAnuncio": row.LinkAnuncio,
                }
            )
        for row in products[products["lucro_liquido_estimado"].fillna(0) < 0].itertuples(index=False):
            rows.append(
                {
                    "nivel": "critico",
                    "tipo_alerta": "Lucro negativo",
                    "MLB": row.item_id,
                    "SKU": row.SKU,
                    "produto": row.produto,
                    "marca": row.Marca,
                    "categoria": row._4,
                    "receita": row.receita,
                    "margem": row.margem_liquida_estimada,
                    "lucro": row.lucro_liquido_estimado,
                    "LinkAnuncio": row.LinkAnuncio,
                }
            )

    return prioritize_alerts(pd.DataFrame(rows))


def build_ads_alerts(ads_df: pd.DataFrame) -> pd.DataFrame:
    """Cria alertas de performance de campanhas."""

    if ads_df.empty:
        return normalize_alert_columns(pd.DataFrame())

    rows: list[dict[str, object]] = []
    for row in ads_df.itertuples(index=False):
        orders_value = safe_number(getattr(row, "orders", 0))
        acos = safe_number(getattr(row, "acos", 0))
        roas = safe_number(getattr(row, "roas", 0))
        cost = safe_number(getattr(row, "cost", 0))
        revenue = safe_number(getattr(row, "revenue", 0))
        campaign_name = safe_text(getattr(row, "campaign_name", "N/D"))

        if acos > 20:
            rows.append(
                {
                    "nivel": "atencao",
                    "tipo_alerta": "ACOS muito alto",
                    "campanha": campaign_name,
                    "receita": cost,
                    "lucro": pd.NA,
                    "ACOS": acos,
                    "ROAS": roas,
                }
            )
        if roas < 3:
            rows.append(
                {
                    "nivel": "critico",
                    "tipo_alerta": "ROAS ruim",
                    "campanha": campaign_name,
                    "receita": revenue,
                    "ACOS": acos,
                    "ROAS": roas,
                }
            )
        if cost > 50 and orders_value == 0:
            rows.append(
                {
                    "nivel": "critico",
                    "tipo_alerta": "Gasto sem conversao",
                    "campanha": campaign_name,
                    "receita": cost,
                    "ACOS": acos,
                    "ROAS": roas,
                }
            )

    return prioritize_alerts(pd.DataFrame(rows))


def build_stock_alerts(stock_df: pd.DataFrame) -> pd.DataFrame:
    """Cria alertas de estoque com base em giro e disponibilidade."""

    if stock_df.empty:
        return normalize_alert_columns(pd.DataFrame())

    rows: list[dict[str, object]] = []
    sold_median = float(stock_df["vendidos_total"].fillna(0).median())
    stock_median = float(stock_df["estoque_atual"].fillna(0).median())

    for row in stock_df.itertuples(index=False):
        status_estoque = safe_text(getattr(row, "status_estoque", "N/D"))
        estoque_atual = safe_number(getattr(row, "estoque_atual", 0))
        vendidos_total = safe_number(getattr(row, "vendidos_total", 0))
        quantidade_periodo = safe_number(getattr(row, "quantidade_periodo", 0))
        common = {
            "MLB": safe_text(getattr(row, "MLB", "N/D")),
            "SKU": safe_text(getattr(row, "SKU_final", "N/D")),
            "produto": safe_text(getattr(row, "produto_final", "N/D")),
            "marca": safe_text(getattr(row, "marca_final", "N/D")),
            "categoria": safe_text(getattr(row, "categoria_final", "N/D")),
            "estoque": estoque_atual,
            "receita": safe_number(getattr(row, "receita", 0)),
            "margem": safe_number(getattr(row, "margem_liquida_estimada", 0)),
            "lucro": safe_number(getattr(row, "lucro_liquido_estimado", 0)),
            "LinkAnuncio": safe_text(getattr(row, "Link_final", "N/D")),
        }
        if status_estoque == "estoque baixo" and vendidos_total > sold_median:
            rows.append({"nivel": "atencao", "tipo_alerta": "Estoque baixo com alta venda", **common})
        if status_estoque == "estoque zerado" and quantidade_periodo > 0:
            rows.append({"nivel": "critico", "tipo_alerta": "Estoque zerado com vendas recentes", **common})
        if estoque_atual > stock_median and vendidos_total <= sold_median:
            rows.append({"nivel": "atencao", "tipo_alerta": "Produto parado", **common})

    return prioritize_alerts(pd.DataFrame(rows))


def build_registration_alerts(filtered_sales: pd.DataFrame) -> pd.DataFrame:
    """Cria alertas de cadastro incompleto."""

    products = build_product_alert_base(filtered_sales)
    if products.empty:
        return normalize_alert_columns(pd.DataFrame())

    rows: list[dict[str, object]] = []
    for row in products.itertuples(index=False):
        cmv_unitario = safe_number(getattr(row, "cmv_unitario", 0))
        marca = safe_text(getattr(row, "Marca", "N/D"))
        categoria = safe_text(getattr(row, "_4", "N/D"))
        common = {
            "MLB": safe_text(getattr(row, "item_id", "N/D")),
            "SKU": safe_text(getattr(row, "SKU", "N/D")),
            "produto": safe_text(getattr(row, "produto", "N/D")),
            "marca": marca,
            "categoria": categoria,
            "receita": safe_number(getattr(row, "receita", 0)),
            "margem": safe_number(getattr(row, "margem_liquida_estimada", 0)),
            "lucro": safe_number(getattr(row, "lucro_liquido_estimado", 0)),
            "LinkAnuncio": safe_text(getattr(row, "LinkAnuncio", "N/D")),
        }
        if cmv_unitario == 0:
            rows.append({"nivel": "atencao", "tipo_alerta": "Produto sem CMV", **common})
        if marca.strip().upper() in {"", "N/D", "NAN"}:
            rows.append({"nivel": "atencao", "tipo_alerta": "Produto sem marca", **common})
        if categoria.strip().upper() in {"", "N/D", "NAN"}:
            rows.append({"nivel": "atencao", "tipo_alerta": "Produto sem categoria", **common})

    return prioritize_alerts(pd.DataFrame(rows))


def build_all_alerts_bundle(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> dict[str, pd.DataFrame]:
    """Gera o conjunto consolidado de alertas usado pelas abas executivas."""

    stock_df = build_stock_view(filtered_sales, inventory_df, filter_state)
    financial_alerts = build_financial_alerts(filtered_sales, ads_df)
    ads_alerts = build_ads_alerts(ads_df)
    stock_alerts = build_stock_alerts(stock_df)
    registration_alerts = build_registration_alerts(filtered_sales)
    all_alerts = enrich_action_plan(
        prioritize_alerts(
            pd.concat(
                [financial_alerts, ads_alerts, stock_alerts, registration_alerts],
                ignore_index=True,
            )
        )
    )
    return {
        "stock": stock_df,
        "financial": financial_alerts,
        "ads": ads_alerts,
        "stock_alerts": stock_alerts,
        "registration": registration_alerts,
        "all": all_alerts,
    }


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v", color: str | None = None) -> go.Figure:
    if df.empty:
        return empty_fig(title)
    fig = px.bar(df, x=x, y=y, orientation=orientation, color=color or y, color_continuous_scale="Tealgrn")
    fig.update_layout(coloraxis_showscale=False)
    return layout_chart(fig, title)


def short_product_label(value: object, max_length: int = 45) -> str:
    text = safe_text(value)
    return f"{text[:max_length]}..." if len(text) > max_length else text


def premium_commercial_layout(fig: go.Figure, title: str, height: int = 500) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=15)),
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial", size=13),
        showlegend=False,
        hoverlabel=dict(bgcolor="rgba(15, 23, 42, .96)", font_size=13),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, title_text=None, automargin=True)
    fig.update_yaxes(showgrid=False, zeroline=False, title_text=None, automargin=True)
    return fig


def premium_money_bar(
    df: pd.DataFrame,
    value_col: str,
    product_col: str,
    title: str,
    color: str,
    top_n: int = 10,
    percent_col: str | None = None,
    impact_col: str | None = None,
    gradient: bool = False,
) -> go.Figure:
    if df.empty or value_col not in df.columns or product_col not in df.columns:
        return empty_fig(title)

    clean = df.copy()
    clean[value_col] = pd.to_numeric(clean[value_col], errors="coerce").fillna(0)
    clean = clean.sort_values(value_col, ascending=False).head(top_n).copy()
    if clean.empty:
        return empty_fig(title)

    clean["produto_resumido"] = clean[product_col].map(short_product_label)
    total = clean[value_col].sum()
    clean["_percentual_hover"] = (
        pd.to_numeric(clean[percent_col], errors="coerce").fillna(0)
        if percent_col and percent_col in clean.columns
        else clean[value_col].div(total).mul(100).fillna(0)
    )
    clean["_impacto_hover"] = (
        pd.to_numeric(clean[impact_col], errors="coerce").fillna(0)
        if impact_col and impact_col in clean.columns
        else clean[value_col]
    )
    clean["_valor_formatado"] = clean[value_col].map(br_money)
    clean["_percentual_formatado"] = clean["_percentual_hover"].map(br_percent)
    clean["_impacto_formatado"] = clean["_impacto_hover"].map(br_money)

    marker = (
        dict(color=clean[value_col], colorscale="Blues", showscale=False)
        if gradient
        else dict(color=color)
    )
    fig = go.Figure(
        go.Bar(
            x=clean[value_col],
            y=clean["produto_resumido"],
            orientation="h",
            marker=marker,
            text=clean["_valor_formatado"],
            textposition="outside",
            cliponaxis=False,
            customdata=clean[[product_col, "_valor_formatado", "_percentual_formatado", "_impacto_formatado"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Valor: %{customdata[1]}<br>"
                "Percentual: %{customdata[2]}<br>"
                "Impacto: %{customdata[3]}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(autorange="reversed")
    return premium_commercial_layout(fig, title)


def premium_dropoff_impact_bar(df: pd.DataFrame, title: str, top_n: int = 10) -> go.Figure:
    """Grafico de impacto de queda com motivo e acao no hover."""

    required = {"produto", "impacto_faturamento_perdido"}
    if df.empty or not required.issubset(df.columns):
        return empty_fig(title)

    clean = ensure_columns(
        df.copy(),
        {
            "queda_percentual": 0.0,
            "motivo_queda": "N/D",
            "acao_recomendada": "N/D",
        },
    )
    clean["impacto_faturamento_perdido"] = pd.to_numeric(
        clean["impacto_faturamento_perdido"],
        errors="coerce",
    ).fillna(0)
    clean["queda_percentual"] = pd.to_numeric(clean["queda_percentual"], errors="coerce").fillna(0)
    clean = clean.sort_values("impacto_faturamento_perdido", ascending=False).head(top_n).copy()
    if clean.empty:
        return empty_fig(title)

    clean["produto_resumido"] = clean["produto"].map(short_product_label)
    clean["_impacto_formatado"] = clean["impacto_faturamento_perdido"].map(br_money)
    clean["_queda_formatada"] = clean["queda_percentual"].map(br_percent)
    custom_cols = [
        "produto",
        "_impacto_formatado",
        "_queda_formatada",
        "motivo_queda",
        "acao_recomendada",
    ]

    fig = go.Figure(
        go.Bar(
            x=clean["impacto_faturamento_perdido"],
            y=clean["produto_resumido"],
            orientation="h",
            marker=dict(color="#DC2626"),
            text=clean["_impacto_formatado"],
            textposition="outside",
            cliponaxis=False,
            customdata=clean[custom_cols],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Impacto perdido: %{customdata[1]}<br>"
                "Queda: %{customdata[2]}<br>"
                "Motivo: %{customdata[3]}<br>"
                "Acao: %{customdata[4]}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(autorange="reversed")
    return premium_commercial_layout(fig, title)


def premium_curva_a_risk_bar(df: pd.DataFrame, title: str, top_n: int = 10) -> go.Figure:
    if df.empty or "score_risco_curva_a" not in df.columns or "produto" not in df.columns:
        return empty_fig(title)

    colors = {
        "Cr\u00edtico": "#DC2626",
        "Alto": "#F97316",
        "M\u00e9dio": "#EAB308",
        "Baixo": "#64748B",
    }
    clean = ensure_columns(
        df.copy(),
        {
            "nivel_risco": "N/D",
            "faturamento": 0.0,
            "motivos_risco": "N/D",
            "acao_recomendada": "N/D",
        },
    )
    clean["score_risco_curva_a"] = pd.to_numeric(clean["score_risco_curva_a"], errors="coerce").fillna(0)
    clean["faturamento"] = pd.to_numeric(clean["faturamento"], errors="coerce").fillna(0)
    clean = clean.sort_values(["score_risco_curva_a", "faturamento"], ascending=[False, False]).head(top_n).copy()
    if clean.empty:
        return empty_fig(title)

    clean["produto_resumido"] = clean["produto"].map(short_product_label)
    clean["_faturamento_formatado"] = clean["faturamento"].map(br_money)
    clean["_score_formatado"] = clean["score_risco_curva_a"].map(lambda value: br_number(value, 0))
    fig = go.Figure(
        go.Bar(
            x=clean["score_risco_curva_a"],
            y=clean["produto_resumido"],
            orientation="h",
            marker=dict(color=[colors.get(safe_text(level), "#64748B") for level in clean["nivel_risco"]]),
            text=clean["_score_formatado"],
            textposition="outside",
            cliponaxis=False,
            customdata=clean[
                [
                    "produto",
                    "_score_formatado",
                    "nivel_risco",
                    "_faturamento_formatado",
                    "motivos_risco",
                    "acao_recomendada",
                ]
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Score: %{customdata[1]}<br>"
                "Risco: %{customdata[2]}<br>"
                "Faturamento: %{customdata[3]}<br>"
                "Motivos: %{customdata[4]}<br>"
                "Acao: %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[0, max(100, float(clean["score_risco_curva_a"].max()) * 1.12)])
    return premium_commercial_layout(fig, title)


def premium_percent_bar(
    df: pd.DataFrame,
    value_col: str,
    product_col: str,
    title: str,
    color: str,
    top_n: int = 10,
    ascending: bool = False,
    impact_col: str | None = None,
) -> go.Figure:
    if df.empty or value_col not in df.columns or product_col not in df.columns:
        return empty_fig(title)

    clean = df.copy()
    clean[value_col] = pd.to_numeric(clean[value_col], errors="coerce")
    clean = clean.dropna(subset=[value_col]).sort_values(value_col, ascending=ascending).head(top_n).copy()
    if clean.empty:
        return empty_fig(title)

    clean["produto_resumido"] = clean[product_col].map(short_product_label)
    clean["_percentual_formatado"] = clean[value_col].map(br_percent)
    clean["_impacto_hover"] = (
        pd.to_numeric(clean[impact_col], errors="coerce").fillna(0)
        if impact_col and impact_col in clean.columns
        else pd.Series(0, index=clean.index)
    )
    clean["_impacto_formatado"] = clean["_impacto_hover"].map(br_money)
    fig = go.Figure(
        go.Bar(
            x=clean[value_col],
            y=clean["produto_resumido"],
            orientation="h",
            marker=dict(color=color),
            text=clean["_percentual_formatado"],
            textposition="outside",
            cliponaxis=False,
            customdata=clean[[product_col, "_percentual_formatado", "_impacto_formatado"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Valor: %{customdata[1]}<br>"
                "Percentual: %{customdata[1]}<br>"
                "Impacto: %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(autorange="reversed")
    return premium_commercial_layout(fig, title)


def premium_abc_donut(abc_counts: pd.DataFrame) -> go.Figure:
    title = "Curva ABC por faturamento"
    if abc_counts.empty or "curva" not in abc_counts.columns or "receita" not in abc_counts.columns:
        return empty_fig(title)

    clean = abc_counts.copy()
    clean["receita"] = pd.to_numeric(clean["receita"], errors="coerce").fillna(0)
    clean = clean[clean["receita"] > 0].copy()
    if clean.empty:
        return empty_fig(title)

    order = ["A", "B", "C"]
    clean["curva"] = pd.Categorical(clean["curva"], categories=order, ordered=True)
    clean = clean.sort_values("curva")
    colors = {"A": "#2563EB", "B": "#D97706", "C": "#DC2626"}
    total = clean["receita"].sum()
    clean["percentual"] = clean["receita"].div(total).mul(100).fillna(0)
    fig = go.Figure(
        go.Pie(
            labels=clean["curva"].astype(str),
            values=clean["receita"],
            hole=0.58,
            sort=False,
            marker=dict(colors=[colors.get(str(curve), "#64748B") for curve in clean["curva"]]),
            texttemplate="%{label}<br>%{percent}",
            textposition="inside",
            customdata=clean[["produtos", "percentual"]] if "produtos" in clean.columns else clean[["percentual"]],
            hovertemplate=(
                "<b>Curva %{label}</b><br>"
                "Faturamento: R$ %{value:,.2f}<br>"
                "Percentual: %{percent}<br>"
                "Impacto: %{percent} do faturamento<extra></extra>"
            ),
        )
    )
    fig.update_traces(textfont_size=14)
    return premium_commercial_layout(fig, title)


def line_chart(df: pd.DataFrame, x: str, y: str | list[str], title: str) -> go.Figure:
    if df.empty:
        return empty_fig(title)
    return layout_chart(px.line(df, x=x, y=y, markers=True), title)


def moving_average_window(df: pd.DataFrame) -> int:
    return 7 if len(df) >= 7 else 3


def clean_date_label(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return str(value)
    return timestamp.strftime(DATE_AXIS_FORMAT)


def with_clean_date_axis(df: pd.DataFrame, date_col: str, label_col: str = "data_grafico") -> pd.DataFrame:
    clean = df.copy()
    clean[label_col] = clean[date_col].map(clean_date_label)
    return clean


def temporal_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    color: str | None = None,
) -> go.Figure:
    if df.empty:
        return empty_fig(title)
    clean = with_clean_date_axis(df, x)
    fig = px.line(clean, x="data_grafico", y=y, color=color, markers=True)
    fig.update_xaxes(type="category", tickangle=-35, nticks=8, automargin=True, title_text=None)
    return layout_chart(fig, title)


def moving_average_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    value_prefix: str = "",
) -> go.Figure:
    if df.empty or x not in df.columns or y not in df.columns:
        return empty_fig(title)

    clean = df[[x, y]].copy()
    clean[y] = pd.to_numeric(clean[y], errors="coerce")
    clean = clean.dropna(subset=[x]).sort_values(x)
    if clean.empty or not clean[y].notna().any():
        return empty_fig(title)

    window = moving_average_window(clean)
    clean["data_grafico"] = clean[x].map(clean_date_label)
    clean["media_movel"] = clean[y].rolling(window=window, min_periods=1).mean()
    hover_value = f"{value_prefix}%{{y:,.2f}}" if value_prefix else "%{y:,.2f}"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=clean["data_grafico"],
            y=clean[y],
            mode="lines+markers",
            name="Diário",
            line=dict(width=2.4, color="#2DD4BF"),
            marker=dict(color="#2DD4BF"),
            hovertemplate=f"Data: %{{x}}<br>Diário: {hover_value}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=clean["data_grafico"],
            y=clean["media_movel"],
            mode="lines",
            name="Média móvel",
            line=dict(width=2.6, dash="dash", color="#F59E0B"),
            hovertemplate=f"Data: %{{x}}<br>Média móvel: {hover_value}<extra></extra>",
        )
    )
    fig.update_xaxes(type="category", tickangle=-35, nticks=8, automargin=True, title_text=None)
    if value_prefix:
        fig.update_yaxes(tickprefix=value_prefix)
    return layout_chart(fig, title)


def clean_temporal_pivot_axis(pivot: pd.DataFrame, *, index: bool = False, columns: bool = False) -> pd.DataFrame:
    clean = pivot.copy()
    if index:
        clean.index = [clean_date_label(value) for value in clean.index]
    if columns:
        clean.columns = [clean_date_label(value) for value in clean.columns]
    return clean


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str) -> go.Figure:
    if df.empty:
        return empty_fig(title)
    fig = px.pie(df, names=names, values=values, hole=0.58, color_discrete_sequence=COLORWAY)
    return layout_chart(fig, title, 340)


def heatmap_from_pivot(
    pivot: pd.DataFrame,
    title: str,
    color_label: str,
    colorscale: str = "Tealgrn",
) -> go.Figure:
    if pivot.empty:
        return empty_fig(title)
    if pivot.columns.duplicated().any():
        pivot = pivot.T.groupby(level=0, sort=False).sum().T
    if pivot.index.duplicated().any():
        pivot = pivot.groupby(level=0, sort=False).sum()
    if pivot.empty:
        return empty_fig(title)
    fig = px.imshow(
        pivot.fillna(0),
        aspect="auto",
        color_continuous_scale=colorscale,
        labels=dict(color=color_label),
    )
    fig.update_traces(hovertemplate="Linha: %{y}<br>Coluna: %{x}<br>Valor: %{z:,.2f}<extra></extra>")
    return layout_chart(fig, title, 430)


def render_header(
    selected_period: tuple[date, date],
    base_period: tuple[date, date],
    requested_period: tuple[date, date] | None = None,
) -> None:
    start_date, end_date = selected_period
    base_min, base_max = base_period
    requested_start, requested_end = requested_period or selected_period
    if requested_period and requested_period != selected_period:
        period_badge = (
            f"Periodo solicitado: {requested_start:%d/%m/%Y} a {requested_end:%d/%m/%Y}"
            f"<br>Periodo analisado: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}"
        )
    else:
        period_badge = f"Periodo filtrado: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}"
    st.markdown(
        f"""
        <div class="app-header">
            <div>
                <h1 class="app-title">Jit Parts Ecommerce Executive BI</h1>
                <div class="app-subtitle">
                    Mercado Livre, CMV Seconds, rentabilidade e performance comercial.
                    Base disponivel: {base_min:%d/%m/%Y} a {base_max:%d/%m/%Y}.
                </div>
            </div>
            <div class="app-badge">{period_badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_executive_opportunities(filtered_sales: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    products = product_summary(filtered_sales, 500)
    if products.empty:
        return pd.DataFrame()

    opportunities = products[
        (products["receita"].fillna(0) > 0)
        & (products["lucro_liquido_estimado"].fillna(0) > 0)
        & (products["margem_liquida_estimada"].fillna(0) >= 10)
    ].copy()
    if opportunities.empty:
        opportunities = products[
            (products["receita"].fillna(0) > 0)
            & (products["lucro_liquido_estimado"].fillna(0) > 0)
        ].copy()
    if opportunities.empty:
        return pd.DataFrame()

    opportunities["potencial_estimado"] = (
        opportunities["lucro_liquido_estimado"].fillna(0)
        * opportunities["margem_liquida_estimada"].fillna(0).clip(lower=0)
        / 100
    )
    return opportunities.sort_values(
        ["potencial_estimado", "lucro_liquido_estimado"],
        ascending=False,
    ).head(top_n)


def build_product_dropoffs(filtered_sales: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if filtered_sales.empty or "date" not in filtered_sales.columns:
        return pd.DataFrame()

    base = filtered_sales.copy()
    base["date"] = pd.to_datetime(base["date"], errors="coerce")
    base = base.dropna(subset=["date"])
    if base["date"].nunique() < 2:
        return pd.DataFrame()

    min_date = base["date"].min()
    max_date = base["date"].max()
    midpoint = min_date + (max_date - min_date) / 2
    previous = base[base["date"] <= midpoint]
    current = base[base["date"] > midpoint]
    if previous.empty or current.empty:
        return pd.DataFrame()

    group_cols = ["item_id", "SKU", "produto", "Marca", "Nome da Categoria"]
    prev_summary = previous.groupby(group_cols, dropna=False, as_index=False).agg(
        receita_anterior=("receita", "sum"),
        quantidade_anterior=("quantity", "sum"),
    )
    curr_summary = current.groupby(group_cols, dropna=False, as_index=False).agg(
        receita_atual=("receita", "sum"),
        quantidade_atual=("quantity", "sum"),
    )
    drops = prev_summary.merge(curr_summary, on=group_cols, how="left").fillna(
        {"receita_atual": 0, "quantidade_atual": 0}
    )
    drops["queda_receita_pct"] = (
        (drops["receita_atual"] - drops["receita_anterior"])
        / drops["receita_anterior"].replace(0, pd.NA)
        * 100
    )
    drops = drops[
        (drops["receita_anterior"].fillna(0) > 0)
        & (drops["queda_receita_pct"].fillna(0) <= -50)
    ].copy()
    drops["impacto_estimado"] = (drops["receita_anterior"] - drops["receita_atual"]).clip(lower=0)
    return drops.sort_values("impacto_estimado", ascending=False).head(top_n)


def abrupt_drop_action(row: pd.Series) -> str:
    estoque = safe_number(row.get("estoque_atual"), default=0.0)
    parametro_confiavel = safe_bool(row.get("parametro_confiavel"), default=True)
    queda = safe_number(row.get("queda_percentual"), default=0.0)

    if estoque <= 0:
        return "Possivel ruptura: verificar estoque"
    if not parametro_confiavel:
        return "Atualizar parametros financeiros na Seconds"
    if queda >= 90:
        return "Queda critica: revisar anuncio, preco, estoque e concorrencia"
    if queda >= 70:
        return "Queda forte: revisar preco, Ads e posicionamento"
    return "Atencao: monitorar queda e revisar competitividade"


def has_numeric_value(row: pd.Series, column: str) -> bool:
    if column not in row.index:
        return False
    try:
        return pd.notna(pd.to_numeric(row.get(column), errors="coerce"))
    except (TypeError, ValueError):
        return False


def inferir_motivo_queda(row: pd.Series) -> pd.Series:
    """Infere motivo provavel da queda sem alterar a regra principal de deteccao."""

    estoque = safe_number(row.get("estoque_atual"), default=0.0)
    pedidos_ultimos_7d = safe_number(row.get("pedidos_ultimos_7d"), default=0.0)
    queda = safe_number(row.get("queda_percentual"), default=0.0)
    margem = safe_number(row.get("margem_liquida_estimada"), default=0.0)

    if estoque <= 2:
        return pd.Series(
            {
                "motivo_queda": "Estoque cr\u00edtico",
                "acao_recomendada": "Repor estoque ou verificar disponibilidade imediatamente",
                "prioridade_queda": "Cr\u00edtica",
            }
        )
    if pedidos_ultimos_7d == 0:
        return pd.Series(
            {
                "motivo_queda": "Produto parou de vender",
                "acao_recomendada": "Revisar an\u00fancio, pre\u00e7o, concorr\u00eancia e exposi\u00e7\u00e3o",
                "prioridade_queda": "Alta",
            }
        )
    if queda >= 90:
        return pd.Series(
            {
                "motivo_queda": "Queda cr\u00edtica de demanda",
                "acao_recomendada": "Investigar pre\u00e7o, an\u00fancio, estoque, Ads e concorr\u00eancia",
                "prioridade_queda": "Cr\u00edtica",
            }
        )
    if has_numeric_value(row, "acos") and safe_number(row.get("acos"), default=0.0) > 20:
        return pd.Series(
            {
                "motivo_queda": "Ads com ACOS elevado",
                "acao_recomendada": "Revisar campanha, or\u00e7amento, palavras-chave e produtos anunciados",
                "prioridade_queda": "Alta",
            }
        )
    if has_numeric_value(row, "roas") and safe_number(row.get("roas"), default=0.0) < 5:
        return pd.Series(
            {
                "motivo_queda": "ROAS abaixo do esperado",
                "acao_recomendada": "Otimizar campanha ou pausar investimento",
                "prioridade_queda": "Alta",
            }
        )
    if margem < 5:
        return pd.Series(
            {
                "motivo_queda": "Margem pressionada",
                "acao_recomendada": "Revisar pre\u00e7o, CMV, frete e comiss\u00e3o",
                "prioridade_queda": "M\u00e9dia",
            }
        )
    return pd.Series(
        {
            "motivo_queda": "Poss\u00edvel perda de relev\u00e2ncia ou concorr\u00eancia",
            "acao_recomendada": "Comparar pre\u00e7o, reputa\u00e7\u00e3o, prazo, fotos e posicionamento do an\u00fancio",
            "prioridade_queda": "M\u00e9dia",
        }
    )


def build_abrupt_product_dropoffs(filtered_sales: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Detecta produtos que vendiam bem e perderam tracao nos ultimos 7 dias."""

    output_columns = [
        "item_id",
        "produto",
        "marca",
        "categoria",
        "faturamento_30d_anteriores",
        "faturamento_ultimos_7d",
        "queda_percentual",
        "impacto_faturamento_perdido",
        "pedidos_30d_anteriores",
        "pedidos_ultimos_7d",
        "estoque_atual",
        "margem_liquida_estimada",
        "acos",
        "roas",
        "motivo_queda",
        "acao_recomendada",
        "prioridade_queda",
        "sugestao_automatica",
        "link_anuncio",
    ]
    if filtered_sales.empty or "date_created" not in filtered_sales.columns:
        return pd.DataFrame(columns=output_columns)

    base = filtered_sales.copy()
    base["data_venda_queda"] = pd.to_datetime(base["date_created"], errors="coerce", utc=True)
    if base["data_venda_queda"].notna().any():
        base["data_venda_queda"] = base["data_venda_queda"].dt.tz_convert(APP_TIMEZONE).dt.tz_localize(None)
    base = base.dropna(subset=["data_venda_queda"])
    if base.empty:
        return pd.DataFrame(columns=output_columns)

    base = ensure_columns(
        base,
        {
            "item_id": "N/D",
            "produto": "N/D",
            "Marca": "N/D",
            "Nome da Categoria": "N/D",
            "receita": 0.0,
            "order_id": pd.NA,
            "estoque_atual": pd.NA,
            "margem_liquida_estimada": pd.NA,
            "acos": pd.NA,
            "roas": pd.NA,
            "parametro_confiavel": True,
            "LinkAnuncio": "N/D",
        },
    )
    if "link_anuncio" not in base.columns:
        base["link_anuncio"] = base["LinkAnuncio"]
    base["receita"] = pd.to_numeric(base["receita"], errors="coerce").fillna(0)
    base["estoque_atual"] = pd.to_numeric(base["estoque_atual"], errors="coerce")
    base["margem_liquida_estimada"] = pd.to_numeric(base["margem_liquida_estimada"], errors="coerce")
    base["acos"] = pd.to_numeric(base["acos"], errors="coerce")
    base["roas"] = pd.to_numeric(base["roas"], errors="coerce")
    base["item_id"] = base["item_id"].fillna("N/D").astype(str)
    base["produto"] = base["produto"].fillna("N/D").astype(str)
    base["marca"] = base["Marca"].fillna("N/D").astype(str)
    base["categoria"] = base["Nome da Categoria"].fillna("N/D").astype(str)
    base["link_anuncio"] = base["link_anuncio"].fillna("N/D").astype(str)
    base["parametro_confiavel"] = base["parametro_confiavel"].map(lambda value: safe_bool(value, default=True))

    max_date = base["data_venda_queda"].max().normalize()
    ultimos_7_inicio = max_date - pd.Timedelta(days=6)
    anteriores_30_inicio = ultimos_7_inicio - pd.Timedelta(days=30)
    anteriores_30_fim = ultimos_7_inicio

    recent = base[
        (base["data_venda_queda"] >= ultimos_7_inicio)
        & (base["data_venda_queda"] < max_date + pd.Timedelta(days=1))
    ].copy()
    previous = base[
        (base["data_venda_queda"] >= anteriores_30_inicio)
        & (base["data_venda_queda"] < anteriores_30_fim)
    ].copy()
    if previous.empty:
        return pd.DataFrame(columns=output_columns)

    group_cols = ["item_id", "produto", "marca", "categoria"]
    order_agg = "nunique" if "order_id" in base.columns else "count"
    previous_summary = previous.groupby(group_cols, dropna=False, as_index=False).agg(
        faturamento_30d_anteriores=("receita", "sum"),
        pedidos_30d_anteriores=("order_id", order_agg),
        estoque_atual=("estoque_atual", "max"),
        margem_liquida_estimada=("margem_liquida_estimada", "mean"),
        acos=("acos", "mean"),
        roas=("roas", "mean"),
        parametro_confiavel=("parametro_confiavel", "min"),
        link_anuncio=("link_anuncio", "first"),
    )
    recent_summary = recent.groupby(group_cols, dropna=False, as_index=False).agg(
        faturamento_ultimos_7d=("receita", "sum"),
        pedidos_ultimos_7d=("order_id", order_agg),
    )

    drops = previous_summary.merge(recent_summary, on=group_cols, how="left")
    drops[["faturamento_ultimos_7d", "pedidos_ultimos_7d"]] = drops[
        ["faturamento_ultimos_7d", "pedidos_ultimos_7d"]
    ].fillna(0)
    drops["media_diaria_7d"] = drops["faturamento_ultimos_7d"] / 7
    drops["media_diaria_30d"] = drops["faturamento_30d_anteriores"] / 30
    drops["queda_percentual"] = (
        (drops["media_diaria_30d"] - drops["media_diaria_7d"])
        / drops["media_diaria_30d"].replace(0, pd.NA)
        * 100
    )
    drops["impacto_faturamento_perdido"] = (
        (drops["media_diaria_30d"] - drops["media_diaria_7d"]) * 7
    ).clip(lower=0)
    drops = drops[
        (drops["faturamento_30d_anteriores"].fillna(0) >= 500)
        & (drops["pedidos_30d_anteriores"].fillna(0) >= 5)
        & (drops["queda_percentual"].fillna(0) >= 50)
    ].copy()
    if drops.empty:
        return pd.DataFrame(columns=output_columns)

    drops["sugestao_automatica"] = drops.apply(abrupt_drop_action, axis=1)
    drop_reason = drops.apply(inferir_motivo_queda, axis=1)
    drops[["motivo_queda", "acao_recomendada", "prioridade_queda"]] = drop_reason
    drops = drops.sort_values("impacto_faturamento_perdido", ascending=False)
    if top_n is not None:
        drops = drops.head(top_n)
    return drops[output_columns]


def product_days_without_sale(financial_df: pd.DataFrame) -> dict[str, int]:
    """Calcula dias sem venda por item a partir das datas ja carregadas no dashboard."""

    if financial_df.empty or "item_id" not in financial_df.columns:
        return {}

    base = financial_df.copy()
    if "date_created" in base.columns and base["date_created"].notna().any():
        dates = pd.to_datetime(base["date_created"], errors="coerce", utc=True)
        dates = dates.dt.tz_convert(APP_TIMEZONE).dt.tz_localize(None)
    elif "date" in base.columns and base["date"].notna().any():
        dates = pd.to_datetime(base["date"], errors="coerce")
    else:
        return {}

    base["_data_ultima_venda"] = dates
    base = base.dropna(subset=["_data_ultima_venda"])
    if base.empty:
        return {}

    max_date = base["_data_ultima_venda"].max().normalize()
    last_sale = base.groupby("item_id")["_data_ultima_venda"].max()
    days = (max_date - last_sale.dt.normalize()).dt.days.fillna(0).clip(lower=0)
    return days.astype(int).to_dict()


def recommended_actions_product_base(
    products: pd.DataFrame,
    stock: pd.DataFrame,
    financial_df: pd.DataFrame,
) -> pd.DataFrame:
    """Monta base de produto para o motor de acoes sem alterar calculos existentes."""

    product_defaults = {
        "item_id": "N/D",
        "SKU": "N/D",
        "produto": "N/D",
        "Marca": "N/D",
        "Nome da Categoria": "N/D",
        "receita": 0.0,
        "lucro_liquido_estimado": 0.0,
        "margem_operacional": pd.NA,
        "margem_liquida_estimada": pd.NA,
        "pedidos": 0,
        "quantidade": 0,
    }
    base = ensure_columns(products.copy(), product_defaults)
    base = base[list(product_defaults.keys())].copy()

    if not stock.empty:
        stock_cols = [
            "MLB",
            "SKU_final",
            "produto_final",
            "marca_final",
            "categoria_final",
            "estoque_atual",
            "vendidos_total",
            "quantidade_periodo",
            "receita",
            "lucro_liquido_estimado",
            "margem_liquida_estimada",
        ]
        stock_view = ensure_columns(stock.copy(), {column: pd.NA for column in stock_cols})[stock_cols].copy()
        stock_view = stock_view.drop_duplicates(subset=["MLB"], keep="last")
        stock_merge = stock_view[["MLB", "estoque_atual", "vendidos_total"]].rename(columns={"MLB": "item_id"})
        base = base.merge(stock_merge, on="item_id", how="left")

        known_items = set(base["item_id"].fillna("N/D").astype(str))
        stock_missing = stock_view[~stock_view["MLB"].fillna("N/D").astype(str).isin(known_items)].copy()
        if not stock_missing.empty:
            stock_missing = stock_missing.rename(
                columns={
                    "MLB": "item_id",
                    "SKU_final": "SKU",
                    "produto_final": "produto",
                    "marca_final": "Marca",
                    "categoria_final": "Nome da Categoria",
                    "quantidade_periodo": "quantidade",
                }
            )
            stock_missing["margem_operacional"] = pd.NA
            stock_missing["pedidos"] = 0
            stock_missing = ensure_columns(stock_missing, product_defaults | {"estoque_atual": pd.NA, "vendidos_total": pd.NA})
            base = pd.concat(
                [base, stock_missing[base.columns]],
                ignore_index=True,
            )
    else:
        base["estoque_atual"] = pd.NA
        base["vendidos_total"] = pd.NA

    base = safe_numeric(
        base,
        [
            "receita",
            "lucro_liquido_estimado",
            "margem_operacional",
            "margem_liquida_estimada",
            "pedidos",
            "quantidade",
            "estoque_atual",
            "vendidos_total",
        ],
    )
    base["margem_base"] = base["margem_operacional"].where(
        base["margem_operacional"].notna(),
        base["margem_liquida_estimada"],
    )
    base["dias_sem_venda"] = base["item_id"].astype(str).map(product_days_without_sale(financial_df))
    base["dias_sem_venda"] = base["dias_sem_venda"].fillna(
        base["estoque_atual"].fillna(0).gt(0).map({True: 999, False: 0})
    )
    return base


def build_recommended_actions_df(
    financial_df: pd.DataFrame,
    products: pd.DataFrame,
    stock: pd.DataFrame,
    dropoffs: pd.DataFrame,
    ads_df: pd.DataFrame,
) -> pd.DataFrame:
    """Motor de regras executivo para a Central de Acoes Recomendadas."""

    output_columns = [
        "produto",
        "item_id",
        "categoria",
        "problema",
        "acao_recomendada",
        "prioridade",
        "impacto_financeiro",
        "urgencia_cor",
        "margem",
        "faturamento",
        "queda_percentual",
        "roas",
        "acos",
        "estoque",
    ]
    red = "\U0001F534 vermelho"
    dark_red = "\U0001F534 vermelho escuro"
    orange = "\U0001F7E0 laranja"
    yellow = "\U0001F7E1 amarelo"
    green = "\U0001F7E2 verde"
    priority_critical = "Cr\u00edtica"
    priority_medium = "M\u00e9dia"

    rows: list[dict[str, object]] = []

    def append_action(
        *,
        produto: object,
        item_id: object,
        categoria: str,
        problema: str,
        acao_recomendada: str,
        prioridade: str,
        impacto_financeiro: float,
        urgencia_cor: str,
        margem: float = 0.0,
        faturamento: float = 0.0,
        queda_percentual: float = 0.0,
        roas: float = 0.0,
        acos: float = 0.0,
        estoque: float = 0.0,
    ) -> None:
        rows.append(
            {
                "produto": safe_text(produto),
                "item_id": safe_text(item_id),
                "categoria": categoria,
                "problema": problema,
                "acao_recomendada": acao_recomendada,
                "prioridade": prioridade,
                "impacto_financeiro": impacto_financeiro,
                "urgencia_cor": urgencia_cor,
                "margem": margem,
                "faturamento": faturamento,
                "queda_percentual": queda_percentual,
                "roas": roas,
                "acos": acos,
                "estoque": estoque,
            }
        )

    if not dropoffs.empty:
        for row in dropoffs.itertuples(index=False):
            queda = safe_number(getattr(row, "queda_percentual", 0))
            if queda >= 70:
                append_action(
                    produto=getattr(row, "produto", "N/D"),
                    item_id=getattr(row, "item_id", "N/D"),
                    categoria="Venda",
                    problema="Queda brusca",
                    acao_recomendada="Revisar anuncio, preco, estoque e concorrencia",
                    prioridade="Alta",
                    impacto_financeiro=safe_number(getattr(row, "impacto_faturamento_perdido", 0)),
                    urgencia_cor=red,
                    faturamento=safe_number(getattr(row, "faturamento_ultimos_7d", 0)),
                    queda_percentual=queda,
                    estoque=safe_number(getattr(row, "estoque_atual", 0)),
                )

    product_base = recommended_actions_product_base(products, stock, financial_df)
    positive_revenue = product_base["receita"].fillna(0)
    positive_revenue = positive_revenue[positive_revenue > 0]
    relevant_revenue_threshold = float(positive_revenue.median()) if not positive_revenue.empty else 0.0

    for row in product_base.itertuples(index=False):
        margem = safe_number(getattr(row, "margem_base", 0))
        pedidos = safe_number(getattr(row, "pedidos", 0))
        faturamento = safe_number(getattr(row, "receita", 0))
        lucro = safe_number(getattr(row, "lucro_liquido_estimado", 0))
        estoque = safe_number(getattr(row, "estoque_atual", 0))
        dias_sem_venda = safe_number(getattr(row, "dias_sem_venda", 0))
        produto = getattr(row, "produto", "N/D")
        item_id = getattr(row, "item_id", "N/D")

        if margem >= 15 and pedidos <= 2:
            append_action(
                produto=produto,
                item_id=item_id,
                categoria="Oportunidade",
                problema="Alta margem + baixo giro",
                acao_recomendada="Aumentar Ads e exposicao",
                prioridade=priority_medium,
                impacto_financeiro=max(0.0, lucro, faturamento * margem / 100),
                urgencia_cor=green,
                margem=margem,
                faturamento=faturamento,
                estoque=estoque,
            )
        if dias_sem_venda > 30:
            append_action(
                produto=produto,
                item_id=item_id,
                categoria="Estoque",
                problema="Produto sem giro",
                acao_recomendada="Revisar estoque ou pausar anuncio",
                prioridade=priority_medium,
                impacto_financeiro=max(0.0, faturamento),
                urgencia_cor=yellow,
                margem=margem,
                faturamento=faturamento,
                estoque=estoque,
            )
        if margem < 0:
            append_action(
                produto=produto,
                item_id=item_id,
                categoria="Financeiro",
                problema="Margem negativa",
                acao_recomendada="Revisar CMV, preco e comissao",
                prioridade=priority_critical,
                impacto_financeiro=abs(lucro) if lucro else abs(faturamento * margem / 100),
                urgencia_cor=dark_red,
                margem=margem,
                faturamento=faturamento,
                estoque=estoque,
            )
        if estoque <= 2 and faturamento > 0 and faturamento >= relevant_revenue_threshold:
            append_action(
                produto=produto,
                item_id=item_id,
                categoria="Estoque",
                problema="Estoque critico",
                acao_recomendada="Repor estoque urgente",
                prioridade="Alta",
                impacto_financeiro=faturamento,
                urgencia_cor=red,
                margem=margem,
                faturamento=faturamento,
                estoque=estoque,
            )

    if not ads_df.empty:
        ads = ensure_columns(
            ads_df.copy(),
            {
                "campaign_id": "N/D",
                "campaign_name": "N/D",
                "cost": 0.0,
                "revenue": 0.0,
                "orders": 0.0,
                "acos": pd.NA,
                "roas": pd.NA,
            },
        )
        ads = safe_numeric(ads, ["cost", "revenue", "orders", "acos", "roas"])
        ads_by_campaign = (
            ads.groupby(["campaign_id", "campaign_name"], dropna=False, as_index=False)
            .agg(cost=("cost", "sum"), revenue=("revenue", "sum"), orders=("orders", "sum"))
        )
        ads_by_campaign["roas"] = ads_by_campaign["revenue"] / ads_by_campaign["cost"].where(
            ads_by_campaign["cost"] > 0,
            pd.NA,
        )
        ads_by_campaign["acos"] = (
            ads_by_campaign["cost"] / ads_by_campaign["revenue"].where(ads_by_campaign["revenue"] > 0, pd.NA) * 100
        )
        for row in ads_by_campaign.itertuples(index=False):
            acos = safe_number(getattr(row, "acos", 0))
            roas = safe_number(getattr(row, "roas", 0))
            campaign_name = getattr(row, "campaign_name", "N/D")
            campaign_id = getattr(row, "campaign_id", "N/D")
            if acos > 20:
                append_action(
                    produto=campaign_name,
                    item_id=campaign_id,
                    categoria="Ads",
                    problema="Ads ruim",
                    acao_recomendada="Reduzir investimento ou revisar campanha",
                    prioridade="Alta",
                    impacto_financeiro=safe_number(getattr(row, "cost", 0)),
                    urgencia_cor=orange,
                    faturamento=safe_number(getattr(row, "revenue", 0)),
                    roas=roas,
                    acos=acos,
                )
            if roas > 10:
                append_action(
                    produto=campaign_name,
                    item_id=campaign_id,
                    categoria="Ads",
                    problema="ROAS alto",
                    acao_recomendada="Escalar campanha",
                    prioridade="Baixa",
                    impacto_financeiro=safe_number(getattr(row, "revenue", 0)),
                    urgencia_cor=green,
                    faturamento=safe_number(getattr(row, "revenue", 0)),
                    roas=roas,
                    acos=acos,
                )

    acoes_recomendadas_df = pd.DataFrame(rows, columns=output_columns)
    if acoes_recomendadas_df.empty:
        return acoes_recomendadas_df

    acoes_recomendadas_df = safe_numeric(
        acoes_recomendadas_df,
        ["impacto_financeiro", "margem", "faturamento", "queda_percentual", "roas", "acos", "estoque"],
    )
    priority_order = {priority_critical: 0, "Alta": 1, priority_medium: 2, "Baixa": 3}
    acoes_recomendadas_df["_prioridade_ordem"] = (
        acoes_recomendadas_df["prioridade"].map(priority_order).fillna(4)
    )
    acoes_recomendadas_df = acoes_recomendadas_df.sort_values(
        ["_prioridade_ordem", "impacto_financeiro"],
        ascending=[True, False],
    ).drop(columns="_prioridade_ordem")
    return acoes_recomendadas_df[output_columns]


def build_abc_curve(filtered_sales: pd.DataFrame) -> pd.DataFrame:
    products = product_summary(filtered_sales, 500)
    if products.empty:
        return pd.DataFrame()

    abc = products.sort_values("receita", ascending=False).copy()
    total_revenue = abc["receita"].fillna(0).sum()
    if total_revenue <= 0:
        abc["participacao_pct"] = 0.0
        abc["participacao_acumulada_pct"] = 0.0
        abc["curva"] = "C"
        return abc

    abc["participacao_pct"] = abc["receita"].fillna(0) / total_revenue * 100
    abc["participacao_acumulada_pct"] = abc["participacao_pct"].cumsum()
    abc["curva"] = pd.cut(
        abc["participacao_acumulada_pct"],
        bins=[-0.01, 80, 95, float("inf")],
        labels=["A", "B", "C"],
    ).astype(str)
    return abc


def classify_curva_a_risk(score: float) -> str:
    if score >= 60:
        return "Cr\u00edtico"
    if score >= 40:
        return "Alto"
    if score >= 20:
        return "M\u00e9dio"
    return "Baixo"


def build_curva_a_em_risco_df(
    abc: pd.DataFrame,
    financial_df: pd.DataFrame,
    stock: pd.DataFrame,
    dropoffs: pd.DataFrame,
) -> pd.DataFrame:
    """Identifica produtos da Curva A com sinais comerciais ou operacionais de risco."""

    output_columns = [
        "item_id",
        "produto",
        "marca",
        "categoria",
        "faturamento",
        "lucro_liquido_estimado",
        "margem_base",
        "classe_abc",
        "score_risco_curva_a",
        "nivel_risco",
        "motivos_risco",
        "acao_recomendada",
        "estoque_atual",
        "pedidos_ultimos_7d",
        "queda_percentual",
        "link_anuncio",
    ]
    if abc.empty:
        return pd.DataFrame(columns=output_columns)

    base = ensure_columns(
        abc.copy(),
        {
            "item_id": "N/D",
            "produto": "N/D",
            "Marca": "N/D",
            "Nome da Categoria": "N/D",
            "receita": 0.0,
            "lucro_liquido_estimado": 0.0,
            "margem_operacional": pd.NA,
            "margem_liquida_estimada": pd.NA,
            "curva": "N/D",
        },
    )
    base = base[base["curva"].astype(str).eq("A")].copy()
    if base.empty:
        return pd.DataFrame(columns=output_columns)

    base["item_id"] = base["item_id"].fillna("N/D").astype(str)
    base["faturamento"] = pd.to_numeric(base["receita"], errors="coerce").fillna(0)
    base["margem_base"] = pd.to_numeric(base["margem_operacional"], errors="coerce")
    fallback_margin = pd.to_numeric(base["margem_liquida_estimada"], errors="coerce")
    base["margem_base"] = base["margem_base"].where(base["margem_base"].notna(), fallback_margin)
    base["classe_abc"] = base["curva"].astype(str)
    base["marca"] = base["Marca"].fillna("N/D").astype(str)
    base["categoria"] = base["Nome da Categoria"].fillna("N/D").astype(str)

    if not financial_df.empty:
        finance = ensure_columns(
            financial_df.copy(),
            {
                "item_id": "N/D",
                "parametro_confiavel": True,
                "LinkAnuncio": pd.NA,
                "link_anuncio": pd.NA,
                "estoque_atual": pd.NA,
            },
        )
        finance["item_id"] = finance["item_id"].fillna("N/D").astype(str)
        finance["parametro_confiavel_bool"] = finance["parametro_confiavel"].map(
            lambda value: safe_bool(value, default=True)
        )
        finance["link_anuncio_base"] = finance["LinkAnuncio"].where(
            finance["LinkAnuncio"].notna(),
            finance["link_anuncio"],
        )
        finance["estoque_atual"] = pd.to_numeric(finance["estoque_atual"], errors="coerce")
        finance_summary = (
            finance.groupby("item_id", dropna=False, as_index=False)
            .agg(
                parametro_confiavel=("parametro_confiavel_bool", "min"),
                link_anuncio_financeiro=("link_anuncio_base", "first"),
                estoque_atual_financeiro=("estoque_atual", "max"),
            )
        )
        base = base.merge(finance_summary, on="item_id", how="left")
    else:
        base["parametro_confiavel"] = True
        base["link_anuncio_financeiro"] = pd.NA
        base["estoque_atual_financeiro"] = pd.NA

    if not stock.empty:
        stock_base = ensure_columns(stock.copy(), {"MLB": "N/D", "estoque_atual": pd.NA, "Link_final": pd.NA})
        stock_summary = pd.DataFrame(
            {
                "item_id": stock_base["MLB"].fillna("N/D").astype(str),
                "estoque_atual_estoque": pd.to_numeric(stock_base["estoque_atual"], errors="coerce"),
                "link_anuncio_estoque": stock_base["Link_final"],
            }
        )
        stock_summary = (
            stock_summary.groupby("item_id", dropna=False, as_index=False)
            .agg(
                estoque_atual_estoque=("estoque_atual_estoque", "max"),
                link_anuncio_estoque=("link_anuncio_estoque", "first"),
            )
        )
        base = base.merge(stock_summary, on="item_id", how="left")
    else:
        base["estoque_atual_estoque"] = pd.NA
        base["link_anuncio_estoque"] = pd.NA

    if not dropoffs.empty:
        drop_base = ensure_columns(
            dropoffs.copy(),
            {
                "item_id": "N/D",
                "pedidos_ultimos_7d": 0,
                "queda_percentual": 0.0,
                "link_anuncio": pd.NA,
            },
        )
        drop_base["item_id"] = drop_base["item_id"].fillna("N/D").astype(str)
        drop_summary = (
            drop_base.groupby("item_id", dropna=False, as_index=False)
            .agg(
                pedidos_ultimos_7d=("pedidos_ultimos_7d", "max"),
                queda_percentual=("queda_percentual", "max"),
                link_anuncio_queda=("link_anuncio", "first"),
            )
        )
        drop_summary["queda_brusca"] = True
        base = base.merge(drop_summary, on="item_id", how="left")
    else:
        base["pedidos_ultimos_7d"] = pd.NA
        base["queda_percentual"] = pd.NA
        base["link_anuncio_queda"] = pd.NA
        base["queda_brusca"] = False

    base["parametro_confiavel"] = base["parametro_confiavel"].fillna(True).map(
        lambda value: safe_bool(value, default=True)
    )
    base["estoque_atual"] = pd.to_numeric(base["estoque_atual_estoque"], errors="coerce")
    base["estoque_atual"] = base["estoque_atual"].where(
        base["estoque_atual"].notna(),
        pd.to_numeric(base["estoque_atual_financeiro"], errors="coerce"),
    )
    base["pedidos_ultimos_7d"] = pd.to_numeric(base["pedidos_ultimos_7d"], errors="coerce")
    base["queda_percentual"] = pd.to_numeric(base["queda_percentual"], errors="coerce")
    base["queda_brusca"] = base["queda_brusca"].fillna(False).map(lambda value: safe_bool(value, default=False))
    base["link_anuncio"] = base["link_anuncio_queda"].where(base["link_anuncio_queda"].notna(), base["link_anuncio_estoque"])
    base["link_anuncio"] = base["link_anuncio"].where(base["link_anuncio"].notna(), base["link_anuncio_financeiro"])

    rows: list[dict[str, object]] = []
    for _, row in base.iterrows():
        queda_brusca = safe_bool(row.get("queda_brusca"), default=False)
        estoque_critico = pd.notna(row.get("estoque_atual")) and safe_number(row.get("estoque_atual")) <= 2
        margem_press = safe_number(row.get("margem_base"), default=0.0) < 7
        parou_vender = pd.notna(row.get("pedidos_ultimos_7d")) and safe_number(row.get("pedidos_ultimos_7d")) == 0
        sem_parametro = not safe_bool(row.get("parametro_confiavel"), default=True)

        signals = [
            ("Queda brusca", queda_brusca, 35, "Revisar pre\u00e7o, Ads, concorr\u00eancia e posicionamento"),
            ("Estoque cr\u00edtico", estoque_critico, 25, "Priorizar reposi\u00e7\u00e3o imediata"),
            ("Margem pressionada", margem_press, 20, "Revisar pre\u00e7o, CMV, frete e comiss\u00e3o"),
            ("Parou de vender", parou_vender, 15, "Revisar pre\u00e7o, Ads, concorr\u00eancia e posicionamento"),
            ("Sem par\u00e2metro financeiro confi\u00e1vel", sem_parametro, 10, "Atualizar par\u00e2metros financeiros na Seconds"),
        ]
        active = [signal for signal in signals if signal[1]]
        if not active:
            continue

        score = sum(signal[2] for signal in active)
        actions = list(dict.fromkeys(signal[3] for signal in active))
        rows.append(
            {
                "item_id": safe_text(row.get("item_id")),
                "produto": safe_text(row.get("produto")),
                "marca": safe_text(row.get("marca")),
                "categoria": safe_text(row.get("categoria")),
                "faturamento": safe_number(row.get("faturamento")),
                "lucro_liquido_estimado": safe_number(row.get("lucro_liquido_estimado")),
                "margem_base": safe_number(row.get("margem_base")),
                "classe_abc": "A",
                "score_risco_curva_a": score,
                "nivel_risco": classify_curva_a_risk(score),
                "motivos_risco": " | ".join(signal[0] for signal in active),
                "acao_recomendada": " | ".join(actions),
                "estoque_atual": safe_number(row.get("estoque_atual"), default=0.0),
                "pedidos_ultimos_7d": safe_number(row.get("pedidos_ultimos_7d"), default=0.0),
                "queda_percentual": safe_number(row.get("queda_percentual"), default=0.0),
                "link_anuncio": safe_text(row.get("link_anuncio")),
            }
        )

    curva_a_em_risco_df = pd.DataFrame(rows, columns=output_columns)
    if curva_a_em_risco_df.empty:
        return curva_a_em_risco_df

    risk_order = {"Cr\u00edtico": 0, "Alto": 1, "M\u00e9dio": 2, "Baixo": 3}
    curva_a_em_risco_df["_risk_order"] = curva_a_em_risco_df["nivel_risco"].map(risk_order).fillna(4)
    return curva_a_em_risco_df.sort_values(
        ["_risk_order", "score_risco_curva_a", "faturamento"],
        ascending=[True, False, False],
    ).drop(columns="_risk_order")


def render_visao_geral_executiva(
    filtered_sales: pd.DataFrame,
    financial_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
    selected_period: tuple[date, date],
) -> None:
    bundle = build_all_alerts_bundle(filtered_sales, inventory_df, ads_df, filter_state)
    all_alerts = bundle["all"]
    financial_mode = str(financial_df.attrs.get("financial_mode", FINANCIAL_MODE_HYBRID))
    financials = calculate_executive_financials(financial_df, ads_df, selected_period)
    ads_kpis = calculate_ads_kpis(ads_df)
    faturamento = financials["receita"]
    pedidos = int(financial_df["order_id"].nunique()) if "order_id" in financial_df.columns else 0
    ticket = faturamento / pedidos if pedidos else 0.0
    high_priority_count = int((all_alerts["prioridade"] == "Alta").sum()) if not all_alerts.empty else 0
    result_status = result_operational_status(financials["resultado_operacional_pct"])

    first_row = [
        ("Faturamento", br_money(faturamento), "faturamento"),
        ("Pedidos", br_number(pedidos), None),
        ("Ticket medio", br_money(ticket), "ticket_medio"),
        ("ROAS", br_number(ads_kpis["roas"], 2), "roas"),
        ("ACOS", br_percent(ads_kpis["acos"]), "acos"),
    ]
    second_row = [
        ("Margem Base", br_percent(financials["margem_operacional_pct"]), "margem_operacional"),
        ("Custos Comerciais", br_percent(financials["custos_operacionais_comerciais_pct"]), "impacto_comercial"),
        (
            "Resultado Final da Margem",
            f"{br_percent(financials['resultado_operacional_pct'])} | {br_money(financials['resultado_operacional_valor'])}",
            "resultado_operacional_consolidado",
        ),
        ("Investimento Ads", br_money(financials["ads_value"]), "investimento_ads"),
        ("Alertas alta prioridade", br_number(high_priority_count), "alertas_alta_prioridade"),
    ]
    cols = st.columns(5)
    for col, (label, value, expl_key) in zip(cols, first_row):
        with col:
            kpi_card(label, value, financial_mode, explanation_key=expl_key)
    cols = st.columns(5)
    for col, (label, value, expl_key) in zip(cols, second_row):
        with col:
            if label == "Resultado Final da Margem":
                kpi_status_card(label, value, result_status, financial_mode, explanation_key=expl_key)
            else:
                kpi_card(label, value, financial_mode, explanation_key=expl_key)

    render_commercial_costs_summary(financials)

    daily = daily_summary(financial_df)
    executive_daily = executive_financials_timeseries(financial_df, ads_df, "date")
    col1, col2 = st.columns(2)
    col1.plotly_chart(
        moving_average_line_chart(daily, "date", "receita", "Faturamento por dia"),
        use_container_width=True,
    )
    col2.plotly_chart(
        moving_average_line_chart(executive_daily, "date", "resultado_operacional_valor", "Resultado final por dia"),
        use_container_width=True,
    )
    col3, col4, col5 = st.columns(3)
    col3.plotly_chart(
        moving_average_line_chart(executive_daily, "date", "margem_operacional_pct", "Margem base por dia"),
        use_container_width=True,
    )
    col4.plotly_chart(
        moving_average_line_chart(daily, "date", "pedidos", "Pedidos por dia"),
        use_container_width=True,
    )
    col5.plotly_chart(
        moving_average_line_chart(daily, "date", "ticket_medio_dia", "Ticket medio por dia", value_prefix="R$ "),
        use_container_width=True,
    )

    start_date, end_date = selected_period
    top_risks = all_alerts.sort_values("impacto_financeiro_estimado", ascending=False).head(5)
    opportunities = build_executive_opportunities(financial_df, 5)
    risk_value = (
        float(top_risks["impacto_financeiro_estimado"].fillna(0).sum())
        if not top_risks.empty
        else 0.0
    )
    opportunity_value = (
        float(opportunities["potencial_estimado"].fillna(0).sum())
        if "potencial_estimado" in opportunities.columns and not opportunities.empty
        else 0.0
    )

    st.markdown('<div class="section-title">Resumo executivo automatico</div>', unsafe_allow_html=True)
    devolucao_summary = (
        br_percent(financials["devolucao_pct"])
        if financials["devolucao_custo_real_disponivel"]
        else "N/D - custo real nao disponivel"
    )
    summary = [
        f"Periodo analisado: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}, fonte financeira: {financial_mode}.",
        f"Resultado final da margem: {br_percent(financials['resultado_operacional_pct'])}, equivalente a {br_money(financials['resultado_operacional_valor'])}.",
        f"Leitura diretiva: margem base {br_percent(financials['margem_operacional_pct'])} e custos operacionais comerciais {br_percent(financials['custos_operacionais_comerciais_pct'])}.",
        f"Custos comerciais: Ads {br_percent(financials['ads_pct'])}, FULL {br_percent(financials['full_pct'])}, devolucoes {devolucao_summary}, outras tarifas {br_percent(financials['outras_taxas_pct']) if financials['outras_taxas_explicita'] else 'N/D - coluna explicita ausente'} e papelaria {br_percent(financials['papelaria_embalagens_pct'])}.",
        f"Cobertura Ads: {br_percent(financials['ads_cobertura_pct'], 0)}; fonte {financials['ads_fonte']}.",
        f"Prioridade: {br_number(high_priority_count)} alertas de alta prioridade demandam acompanhamento executivo.",
        f"Alavancas: os 5 maiores riscos concentram {br_money(risk_value)} e as 5 oportunidades somam potencial estimado de {br_money(opportunity_value)}.",
    ]
    for line in summary:
        st.markdown(f"- {line}")

    col_risks, col_opps = st.columns(2)
    short_alert_cols = [
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "produto",
        "campanha",
        "receita",
        "lucro",
        "margem",
    ]
    with col_risks:
        st.markdown('<div class="section-title">Top 5 riscos</div>', unsafe_allow_html=True)
        if top_risks.empty:
            st.info("Nenhum risco relevante para os filtros atuais.")
        else:
            st.dataframe(
                style_executive_alerts(top_risks[short_alert_cols]),
                use_container_width=True,
                hide_index=True,
                height=260,
            )
    with col_opps:
        st.markdown('<div class="section-title">Top 5 oportunidades</div>', unsafe_allow_html=True)
        opp_cols = [
            "item_id",
            "SKU",
            "produto",
            "Marca",
            "receita",
            "lucro_liquido_estimado",
            "margem_liquida_estimada",
            "potencial_estimado",
        ]
        if opportunities.empty:
            st.info("Nenhuma oportunidade clara para os filtros atuais.")
        else:
            st.dataframe(
                format_table(opportunities[opp_cols]),
                use_container_width=True,
                hide_index=True,
                height=260,
            )

    with st.expander("Historico e tendencias", expanded=False):
        render_historico_tendencias(selected_period)


def month_label_pt(value: object) -> str:
    period = pd.Period(value, freq="M")
    return f"{MONTH_NAMES_PT[period.month]}/{period.year}"


def month_label_short_pt(value: object) -> str:
    period = pd.Period(value, freq="M")
    return f"{MONTH_ABBR_PT[period.month]}/{period.year}"


def signed_br_percent(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    numeric = float(value)
    sign = "+" if numeric > 0 else ""
    return f"{sign}{numeric:.{decimals}f}%".replace(".", ",")


def commercial_sales_date_series(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """Escolhe a data de venda filtrada, sem depender de data de snapshot."""

    for column in ["data_venda", "data_ref", "date"]:
        if column in df.columns and df[column].notna().any():
            return pd.to_datetime(df[column], errors="coerce"), column

    if "date_created" in df.columns and df["date_created"].notna().any():
        parsed = pd.to_datetime(df["date_created"], errors="coerce", utc=True)
        parsed = parsed.dt.tz_convert(APP_TIMEZONE).dt.tz_localize(None)
        return parsed, "date_created"

    return pd.Series(pd.NaT, index=df.index), "indisponivel"


def log_commercial_debug(
    base: pd.DataFrame,
    date_column: str,
    date_series: pd.Series,
    revenue: pd.DataFrame | None = None,
) -> None:
    """Debug temporario da aba Comercial."""

    debug = base.copy()
    debug["_data_comercial"] = date_series
    debug["_mes_comercial"] = debug["_data_comercial"].dt.to_period("M")
    valid = debug.dropna(subset=["_mes_comercial"])
    month_counts = valid.groupby("_mes_comercial").size()
    revenue_column = "receita" if "receita" in valid.columns else "faturamento"
    month_revenue = (
        valid.groupby("_mes_comercial")[revenue_column].sum()
        if revenue_column in valid.columns
        else pd.Series(dtype="float")
    )

    if revenue is not None:
        pass  # log removido para producao(df: pd.DataFrame) -> tuple[pd.DataFrame, list[pd.Period], dict[pd.Period, str]]:
    base = df.copy()
    base["Marca"] = base["Marca"].fillna("N/D").replace("", "N/D").astype(str)
    date_series, date_column = commercial_sales_date_series(base)
    base["data_venda_comercial"] = date_series
    base["mes_ref"] = base["data_venda_comercial"].dt.to_period("M").dt.to_timestamp()
    base["mes_periodo"] = base["mes_ref"].dt.to_period("M")
    log_commercial_debug(base, date_column, date_series)
    base = base.dropna(subset=["mes_periodo"])
    if base.empty:
        return pd.DataFrame(), [], {}

    months = sorted(base["mes_periodo"].unique())
    month_labels = {month: month_label_short_pt(month) for month in months}
    monthly = (
        base.groupby(["Marca", "mes_periodo"], as_index=False)
        .agg(
            faturamento=("receita", "sum"),
            lucro_liquido_estimado=("lucro_liquido_estimado", "sum"),
        )
        .sort_values(["Marca", "mes_periodo"])
    )
    return monthly, months, month_labels


def commercial_monthly_matrices(df: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    monthly, months, month_labels = commercial_monthly_base(df)
    if monthly.empty:
        return {}

    brand_order = (
        monthly.groupby("Marca")["faturamento"]
        .sum()
        .sort_values(ascending=False)
        .index
        .tolist()
    )
    revenue = (
        monthly.pivot_table(index="Marca", columns="mes_periodo", values="faturamento", aggfunc="sum")
        .reindex(index=brand_order, columns=months)
        .fillna(0)
    )
    profit = (
        monthly.pivot_table(index="Marca", columns="mes_periodo", values="lucro_liquido_estimado", aggfunc="sum")
        .reindex(index=brand_order, columns=months)
        .fillna(0)
    )

    growth_values = pd.DataFrame(index=revenue.index, columns=revenue.columns, dtype="float")
    growth_display = pd.DataFrame(index=revenue.index, columns=revenue.columns, dtype="object")
    for brand in revenue.index:
        for position, month in enumerate(revenue.columns):
            current = safe_number(revenue.loc[brand, month])
            if position == 0:
                growth_display.loc[brand, month] = "Iniciando" if current > 0 else "Sem venda"
                continue
            previous = safe_number(revenue.loc[brand, revenue.columns[position - 1]])
            if previous == 0 and current > 0:
                growth_display.loc[brand, month] = "Iniciando"
            elif previous == 0 and current == 0:
                growth_display.loc[brand, month] = "Sem venda"
            elif current == 0 and previous > 0:
                growth_values.loc[brand, month] = -100.0
                growth_display.loc[brand, month] = signed_br_percent(-100.0)
            else:
                growth = (current / previous - 1) * 100
                growth_values.loc[brand, month] = growth
                growth_display.loc[brand, month] = signed_br_percent(growth)

    month_totals = revenue.sum(axis=0)
    participation_values = revenue.div(month_totals.replace(0, pd.NA), axis=1) * 100
    participation_values = participation_values.fillna(0)
    participation_values.loc["Geral"] = [100 if month_totals.loc[month] > 0 else 0 for month in revenue.columns]
    participation_display = participation_values.map(br_percent)

    margin_values = profit.div(revenue.replace(0, pd.NA)) * 100
    total_profit = profit.sum(axis=0)
    margin_values.loc["Geral"] = total_profit.div(month_totals.replace(0, pd.NA)) * 100
    margin_display = margin_values.map(br_percent)

    rename_columns = {month: month_labels[month] for month in months}
    matrices = {
        "growth": (growth_display.rename(columns=rename_columns), growth_values.rename(columns=rename_columns)),
        "participation": (
            participation_display.rename(columns=rename_columns),
            participation_values.rename(columns=rename_columns),
        ),
        "margin": (margin_display.rename(columns=rename_columns), margin_values.rename(columns=rename_columns)),
    }
    return matrices


def color_growth_cell(value: object) -> str:
    if pd.isna(value):
        return "background-color: rgba(100, 116, 139, .12); color: #64748B; font-weight: 700;"
    if value < CRESCIMENTO_META_AMARELO:
        return "background-color: rgba(220, 38, 38, .18); color: #991B1B; font-weight: 700;"
    if value < CRESCIMENTO_META_VERDE:
        return "background-color: rgba(217, 119, 6, .20); color: #92400E; font-weight: 700;"
    return "background-color: rgba(15, 118, 110, .18); color: #0F766E; font-weight: 700;"


def color_participation_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if value < 5:
        return "background-color: rgba(220, 38, 38, .16); color: #991B1B; font-weight: 700;"
    if value < 15:
        return "background-color: rgba(217, 119, 6, .18); color: #92400E; font-weight: 700;"
    return "background-color: rgba(15, 118, 110, .18); color: #0F766E; font-weight: 700;"


def color_margin_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if value < 8:
        return "background-color: rgba(220, 38, 38, .18); color: #991B1B; font-weight: 700;"
    if value < 10:
        return "background-color: rgba(217, 119, 6, .20); color: #92400E; font-weight: 700;"
    return "background-color: rgba(15, 118, 110, .18); color: #0F766E; font-weight: 700;"


def style_commercial_matrix(display: pd.DataFrame, values: pd.DataFrame, color_fn):
    def apply_colors(_: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=display.index, columns=display.columns)
        for row in display.index:
            for column in display.columns:
                styles.loc[row, column] = color_fn(values.loc[row, column])
        return styles

    return (
        display.style.apply(apply_colors, axis=None)
        .set_properties(**{"text-align": "center", "min-width": "112px"})
        .set_table_styles(
            [
                {"selector": "th", "props": [("font-weight", "700"), ("text-align", "center")]},
                {"selector": "td", "props": [("border", "1px solid rgba(148, 163, 184, .22)")]},
            ]
        )
    )


def render_commercial_matrix(
    title: str,
    legend: str,
    display: pd.DataFrame,
    values: pd.DataFrame,
    color_fn,
    file_name: str,
) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.caption(legend)
    st.download_button(
        "Download CSV",
        data=display.reset_index(names="Marca").to_csv(index=False, encoding="utf-8-sig"),
        file_name=file_name,
        mime="text/csv",
        use_container_width=True,
        key=f"download_{file_name}",
    )
    st.dataframe(style_commercial_matrix(display, values, color_fn), use_container_width=True, height=360)


def render_comercial(df: pd.DataFrame) -> None:
    matrices = commercial_monthly_matrices(df)
    if not matrices:
        st.info("Sem dados mensais por marca para o periodo selecionado.")
        return

    growth_display, growth_values = matrices["growth"]
    participation_display, participation_values = matrices["participation"]
    margin_display, margin_values = matrices["margin"]

    render_commercial_matrix(
        "Crescimento de venda por marca",
        "Legenda: vermelho = queda | amarelo = estabilidade | verde = crescimento | cinza = iniciando.",
        growth_display,
        growth_values,
        color_growth_cell,
        "crescimento_venda_marca.csv",
    )
    render_commercial_matrix(
        "Participação mensal sobre o faturamento",
        "Legenda: vermelho = baixa participação | amarelo = intermediária | verde = maior participação.",
        participation_display,
        participation_values,
        color_participation_cell,
        "participacao_mensal_marca.csv",
    )
    render_commercial_matrix(
        "Margem mensal por marca",
        "Legenda: vermelho < 8% | amarelo >= 8% e < 10% | verde >= 10%.",
        margin_display,
        margin_values,
        color_margin_cell,
        "margem_mensal_marca.csv",
    )


def render_produtos(df: pd.DataFrame) -> None:
    products = product_summary(df, 500)
    view_columns = [
        "item_id",
        "SKU",
        "produto",
        "Marca",
        "Nome da Categoria",
        "FULL",
        "Flex",
        "receita",
        "CMV",
        "lucro_liquido_estimado",
        "margem_liquida_estimada",
        "lucro_operacional",
        "margem_operacional",
        "lucro_bruto",
        "margem_bruta",
    ]

    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(
        bar_chart(
            products.sort_values("lucro_liquido_estimado").tail(15),
            "lucro_liquido_estimado",
            "produto",
            "Ranking lucro liquido estimado",
            "h",
        ),
        use_container_width=True,
    )
    col2.plotly_chart(
        bar_chart(
            products.sort_values("margem_liquida_estimada").tail(15),
            "margem_liquida_estimada",
            "produto",
            "Ranking margem liquida estimada",
            "h",
        ),
        use_container_width=True,
    )
    col3.plotly_chart(bar_chart(products.sort_values("receita").tail(15), "receita", "produto", "Ranking faturamento", "h"), use_container_width=True)

    sem_cmv = products[products["cmv_unitario"].isna() | (products["CMV"] == 0)]
    margem_negativa = products[products["margem_liquida_estimada"] < 0]

    st.markdown('<div class="section-title">Itens sem CMV</div>', unsafe_allow_html=True)
    st.dataframe(format_table(sem_cmv[view_columns]), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Itens com margem negativa</div>', unsafe_allow_html=True)
    st.dataframe(format_table(margem_negativa[view_columns]), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Tabela detalhada de produtos</div>', unsafe_allow_html=True)
    st.dataframe(format_table(products[view_columns]), use_container_width=True, hide_index=True)


def render_marcas(df: pd.DataFrame) -> None:
    brands = dimension_summary(df, "Marca", 50)
    col1, col2 = st.columns(2)
    col1.plotly_chart(bar_chart(brands.sort_values("receita"), "receita", "Marca", "Faturamento por marca", "h"), use_container_width=True)
    col2.plotly_chart(
        bar_chart(
            brands.sort_values("lucro_liquido_estimado"),
            "lucro_liquido_estimado",
            "Marca",
            "Lucro liquido estimado por marca",
            "h",
        ),
        use_container_width=True,
    )

    col3, col4 = st.columns(2)
    col3.plotly_chart(
        bar_chart(
            brands.sort_values("margem_liquida_estimada"),
            "margem_liquida_estimada",
            "Marca",
            "Margem liquida estimada por marca",
            "h",
        ),
        use_container_width=True,
    )
    col4.plotly_chart(bar_chart(brands.sort_values("ticket"), "ticket", "Marca", "Ticket medio por marca", "h"), use_container_width=True)

    st.plotly_chart(bar_chart(brands.sort_values("quantidade"), "quantidade", "Marca", "Quantidade vendas por marca", "h"), use_container_width=True)
    monthly = df.groupby(["month", "Marca"], as_index=False).agg(receita=("receita", "sum"))
    st.plotly_chart(layout_chart(px.line(monthly, x="month", y="receita", color="Marca"), "Crescimento temporal por marca"), use_container_width=True)


def truncate_text(value: object, max_chars: int = 58) -> str:
    text = safe_text(value)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def action_group_definitions() -> list[dict[str, str]]:
    return [
        {
            "key": "criticas",
            "title": "\U0001F534 Cr\u00edticas",
            "expander": "\U0001F534 A\u00e7\u00f5es cr\u00edticas",
            "color": "#DC2626",
            "file": "acoes_criticas.csv",
        },
        {
            "key": "altas",
            "title": "\U0001F7E0 Altas",
            "expander": "\U0001F7E0 A\u00e7\u00f5es altas",
            "color": "#F97316",
            "file": "acoes_altas.csv",
        },
        {
            "key": "medias",
            "title": "\U0001F7E1 M\u00e9dias",
            "expander": "\U0001F7E1 A\u00e7\u00f5es m\u00e9dias",
            "color": "#EAB308",
            "file": "acoes_medias.csv",
        },
        {
            "key": "oportunidades",
            "title": "\U0001F7E2 Oportunidades",
            "expander": "\U0001F7E2 Oportunidades",
            "color": "#16A34A",
            "file": "acoes_oportunidades.csv",
        },
    ]


def recommended_action_color(row: pd.Series) -> str:
    priority = safe_text(row.get("prioridade"))
    category = safe_text(row.get("categoria"))
    if category == "Oportunidade" or priority == "Baixa":
        return "#16A34A"
    if priority == "Cr\u00edtica":
        return "#DC2626"
    if priority == "Alta":
        return "#F97316"
    if priority == "M\u00e9dia":
        return "#EAB308"
    return "#64748B"


def recommended_action_label(row: pd.Series) -> str:
    priority = safe_text(row.get("prioridade"))
    category = safe_text(row.get("categoria"))
    if category == "Oportunidade" or priority == "Baixa":
        return "Oportunidade" if category == "Oportunidade" else "Baixa"
    return priority


def enrich_recommended_actions_links(
    acoes_recomendadas_df: pd.DataFrame,
    financial_df: pd.DataFrame,
    stock: pd.DataFrame,
) -> pd.DataFrame:
    """Adiciona link de anuncio para filtros/exportacao visual, sem alterar o motor."""

    df = acoes_recomendadas_df.copy()
    if df.empty:
        df["link_anuncio"] = pd.NA
        return df

    link_frames: list[pd.DataFrame] = []
    if not financial_df.empty:
        sales = ensure_columns(financial_df.copy(), {"item_id": "N/D", "LinkAnuncio": pd.NA, "link_anuncio": pd.NA})
        sales_link = sales["LinkAnuncio"].where(sales["LinkAnuncio"].notna(), sales["link_anuncio"])
        link_frames.append(
            pd.DataFrame(
                {
                    "item_id": sales["item_id"].fillna("N/D").astype(str),
                    "link_anuncio_visual": sales_link,
                }
            )
        )
    if not stock.empty:
        stock_links = ensure_columns(stock.copy(), {"MLB": "N/D", "Link_final": pd.NA})
        link_frames.append(
            pd.DataFrame(
                {
                    "item_id": stock_links["MLB"].fillna("N/D").astype(str),
                    "link_anuncio_visual": stock_links["Link_final"],
                }
            )
        )

    if not link_frames:
        df["link_anuncio"] = pd.NA
        return df

    links = pd.concat(link_frames, ignore_index=True)
    links["item_id"] = links["item_id"].fillna("N/D").astype(str)
    links["link_anuncio_visual"] = links["link_anuncio_visual"].map(lambda value: safe_text(value, ""))
    links = links[~links["link_anuncio_visual"].str.lower().isin(["", "n/d", "nan", "none", "nat", "<na>"])]
    links = links.drop_duplicates(subset=["item_id"], keep="first")

    df["item_id"] = df["item_id"].fillna("N/D").astype(str)
    df = df.merge(links, on="item_id", how="left")
    df["link_anuncio"] = df["link_anuncio_visual"]
    return df.drop(columns=["link_anuncio_visual"])


def recommended_action_groups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = ensure_columns(
        df,
        {
            "categoria": pd.NA,
            "prioridade": pd.NA,
            "impacto_financeiro": 0.0,
            "problema": pd.NA,
        },
    )
    priority_critical = "Cr\u00edtica"
    priority_medium = "M\u00e9dia"
    opportunities_mask = (df["categoria"] == "Oportunidade") | (df["prioridade"] == "Baixa")
    return {
        "criticas": df[df["prioridade"] == priority_critical].copy(),
        "altas": df[df["prioridade"] == "Alta"].copy(),
        "medias": df[(df["prioridade"] == priority_medium) & ~opportunities_mask].copy(),
        "oportunidades": df[opportunities_mask].copy(),
    }


def main_problem_label(df: pd.DataFrame) -> str:
    if df.empty or "problema" not in df.columns:
        return "N/D"
    counts = df["problema"].dropna().astype(str).value_counts()
    return counts.index[0] if not counts.empty else "N/D"


def render_priority_day_panel(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Painel de Prioridades do Dia</div>', unsafe_allow_html=True)
    df = ensure_columns(df, {"impacto_financeiro": 0.0, "problema": pd.NA})
    groups = recommended_action_groups(df)
    cols = st.columns(4)
    for col, group in zip(cols, action_group_definitions()):
        data = groups[group["key"]]
        impact = float(data["impacto_financeiro"].fillna(0).sum()) if not data.empty else 0.0
        principal = main_problem_label(data)
        with col:
            st.markdown(
                f"""
                <div class="priority-card" style="--priority-color:{group['color']};">
                    <div class="priority-card-title">{html.escape(group['title'])}</div>
                    <div class="priority-card-count">{html.escape(br_number(len(data)))}</div>
                    <div class="priority-card-meta">
                        Impacto: {html.escape(br_money(impact))}<br>
                        Principal: {html.escape(truncate_text(principal, 34))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def recommended_action_metrics(row: pd.Series) -> str:
    metrics: list[str] = []
    margem = safe_number(row.get("margem"), default=0.0)
    faturamento = safe_number(row.get("faturamento"), default=0.0)
    queda = safe_number(row.get("queda_percentual"), default=0.0)
    estoque = safe_number(row.get("estoque"), default=0.0)
    roas = safe_number(row.get("roas"), default=0.0)
    acos = safe_number(row.get("acos"), default=0.0)

    if margem:
        metrics.append(f"margem {br_percent(margem, 1)}")
    if faturamento:
        metrics.append(f"faturamento {br_money(faturamento)}")
    if queda:
        metrics.append(f"queda -{br_percent(abs(queda), 1)}")
    if estoque:
        metrics.append(f"estoque {br_number(estoque, 0)}")
    if roas:
        metrics.append(f"ROAS {br_number(roas, 2)}")
    if acos:
        metrics.append(f"ACOS {br_percent(acos, 1)}")
    return " | ".join(metrics) if metrics else "M\u00e9tricas indispon\u00edveis"


def render_recommended_action_card(row: pd.Series) -> None:
    color = recommended_action_color(row)
    label = recommended_action_label(row)
    category = safe_text(row.get("categoria"))
    product = truncate_text(row.get("produto"), 72)
    problem = truncate_text(row.get("problema"), 72)
    action = truncate_text(row.get("acao_recomendada"), 120)
    impact = br_money(safe_number(row.get("impacto_financeiro"), default=0.0))
    metrics = recommended_action_metrics(row)
    st.markdown(
        f"""
        <div class="action-card" style="--priority-color:{color};">
            <div class="action-card-header">
                <div class="action-card-priority">{html.escape(label)}</div>
                <div class="action-card-category">{html.escape(category)}</div>
            </div>
            <div class="action-card-product">{html.escape(product)}</div>
            <div class="action-card-line"><strong>Problema:</strong> {html.escape(problem)}</div>
            <div class="action-card-impact">Impacto estimado: {html.escape(impact)}</div>
            <div class="action-card-line"><strong>A\u00e7\u00e3o:</strong> {html.escape(action)}</div>
            <div class="action-card-metrics">{html.escape(metrics)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_recommended_action_cards(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Top 10 a\u00e7\u00f5es priorit\u00e1rias</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Nenhuma a\u00e7\u00e3o encontrada para os filtros selecionados.")
        return

    top_actions = df.head(10).reset_index(drop=True)
    for start in range(0, len(top_actions), 2):
        cols = st.columns(2)
        for col, (_, row) in zip(cols, top_actions.iloc[start : start + 2].iterrows()):
            with col:
                render_recommended_action_card(row)


def render_actions_expanders(df: pd.DataFrame) -> None:
    groups = recommended_action_groups(df)
    for group in action_group_definitions():
        data = groups[group["key"]]
        title = f"{group['expander']} ({br_number(len(data))})"
        with st.expander(title, expanded=False):
            st.download_button(
                f"Download CSV - {group['file'].replace('.csv', '').replace('_', ' ')}",
                data=data.to_csv(index=False, encoding="utf-8-sig"),
                file_name=group["file"],
                mime="text/csv",
                use_container_width=True,
                key=f"download_{group['key']}",
            )
            if data.empty:
                st.info("Nenhuma a\u00e7\u00e3o neste grupo para os filtros atuais.")
            else:
                st.dataframe(
                    style_recommended_actions(data),
                    use_container_width=True,
                    hide_index=True,
                    height=360,
                )


def render_central_acoes_recomendadas(
    acoes_recomendadas_df: pd.DataFrame,
    financial_df: pd.DataFrame,
    stock: pd.DataFrame,
) -> None:
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Central de A\u00e7\u00f5es Recomendadas</div>', unsafe_allow_html=True)

    if acoes_recomendadas_df.empty:
        render_priority_day_panel(acoes_recomendadas_df)
        st.info("Nenhuma a\u00e7\u00e3o recomendada foi detectada pelos criterios atuais.")
        return

    acoes_recomendadas_df = enrich_recommended_actions_links(acoes_recomendadas_df, financial_df, stock)
    priority_critical = "Cr\u00edtica"
    priority_medium = "M\u00e9dia"
    critical_count = int((acoes_recomendadas_df["prioridade"] == priority_critical).sum())
    critical_impact = float(
        acoes_recomendadas_df.loc[
            acoes_recomendadas_df["prioridade"] == priority_critical,
            "impacto_financeiro",
        ].fillna(0).sum()
    )
    total_impact = float(acoes_recomendadas_df["impacto_financeiro"].fillna(0).sum())
    principal = main_problem_label(acoes_recomendadas_df)
    summary_impact = critical_impact if critical_count else total_impact
    summary_sentence = (
        f"As cr\u00edticas somam {br_money(summary_impact)} de impacto potencial."
        if critical_count
        else f"Elas somam {br_money(summary_impact)} de impacto potencial."
    )
    st.markdown(
        f"""
        <div class="action-summary">
            <div class="action-summary-title">Resumo executivo das a\u00e7\u00f5es</div>
            <div class="action-summary-text">
                Foram detectadas {html.escape(br_number(len(acoes_recomendadas_df)))} a\u00e7\u00f5es recomendadas.
                {html.escape(summary_sentence)}
                A principal causa \u00e9 {html.escape(principal)}.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_priority_day_panel(acoes_recomendadas_df)

    st.download_button(
        "Download CSV completo",
        data=acoes_recomendadas_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="acoes_recomendadas.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_acoes_recomendadas_completo",
    )

    st.markdown('<div class="section-title">Filtros executivos</div>', unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    category_options = sorted(acoes_recomendadas_df["categoria"].dropna().unique().tolist())
    priority_order = [priority_critical, "Alta", priority_medium, "Baixa"]
    priority_options = [
        priority
        for priority in priority_order
        if priority in set(acoes_recomendadas_df["prioridade"].dropna().tolist())
    ]
    selected_categories = filter_col1.multiselect(
        "Categoria",
        category_options,
        default=category_options,
        key="central_acoes_categoria",
    )
    selected_priorities = filter_col2.multiselect(
        "Prioridade",
        priority_options,
        default=priority_options,
        key="central_acoes_prioridade",
    )
    impact_min = filter_col3.number_input(
        "Impacto minimo",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
        key="central_acoes_impacto_minimo",
    )
    filter_col4, filter_col5 = st.columns(2)
    only_with_link = filter_col4.checkbox(
        "Somente a\u00e7\u00f5es com link de an\u00fancio",
        value=False,
        key="central_acoes_somente_link",
    )
    only_with_stock = filter_col5.checkbox(
        "Somente produtos com estoque",
        value=False,
        key="central_acoes_somente_estoque",
    )

    filtered_actions = acoes_recomendadas_df[
        acoes_recomendadas_df["categoria"].isin(selected_categories)
        & acoes_recomendadas_df["prioridade"].isin(selected_priorities)
        & (acoes_recomendadas_df["impacto_financeiro"].fillna(0) >= impact_min)
    ].copy()
    if only_with_link:
        link_text = filtered_actions["link_anuncio"].fillna("").astype(str).str.strip().str.lower()
        filtered_actions = filtered_actions[~link_text.isin(["", "n/d", "nan", "none", "nat", "<na>"])].copy()
    if only_with_stock:
        filtered_actions = filtered_actions[filtered_actions["estoque"].fillna(0) > 0].copy()

    render_top_recommended_action_cards(filtered_actions)
    render_actions_expanders(filtered_actions)

    with st.expander("Ver tabela completa de a\u00e7\u00f5es", expanded=False):
        st.download_button(
            "Download CSV completo filtrado",
            data=filtered_actions.to_csv(index=False, encoding="utf-8-sig"),
            file_name="acoes_recomendadas_filtradas.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_acoes_recomendadas_filtradas",
        )
        if filtered_actions.empty:
            st.info("Nenhuma a\u00e7\u00e3o encontrada para os filtros selecionados.")
        else:
            table_columns = [
                "produto",
                "item_id",
                "categoria",
                "problema",
                "acao_recomendada",
                "prioridade",
                "impacto_financeiro",
                "urgencia_cor",
                "margem",
                "faturamento",
                "queda_percentual",
                "roas",
                "acos",
                "estoque",
                "link_anuncio",
            ]
            table_columns = [column for column in table_columns if column in filtered_actions.columns]
            st.dataframe(
                style_recommended_actions(filtered_actions[table_columns]),
                use_container_width=True,
                hide_index=True,
                height=460,
            )


def render_curva_a_em_risco(curva_a_em_risco_df: pd.DataFrame) -> None:
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Curva A em risco</div>', unsafe_allow_html=True)

    curva_a_em_risco_df = ensure_columns(
        curva_a_em_risco_df,
        {
            "nivel_risco": "N/D",
            "score_risco_curva_a": 0,
            "faturamento": 0.0,
            "produto": "N/D",
        },
    )
    sorted_risks = curva_a_em_risco_df.sort_values(
        ["score_risco_curva_a", "faturamento"],
        ascending=[False, False],
    ).copy()
    priority_risks = sorted_risks[sorted_risks["nivel_risco"].isin(["Cr\u00edtico", "Alto"])].copy()
    secondary_risks = sorted_risks[sorted_risks["nivel_risco"].isin(["M\u00e9dio", "Baixo"])].copy()
    critical_count = int((priority_risks["nivel_risco"] == "Cr\u00edtico").sum())
    high_count = int((priority_risks["nivel_risco"] == "Alto").sum())
    priority_impact = float(priority_risks["faturamento"].fillna(0).sum()) if not priority_risks.empty else 0.0
    most_critical_product = truncate_text(priority_risks.iloc[0]["produto"], 32) if not priority_risks.empty else "N/D"

    card_values = [
        ("Curva A risco critico", br_number(critical_count)),
        ("Curva A risco alto", br_number(high_count)),
        ("Impacto critico + alto", br_money(priority_impact)),
        ("Produto mais critico", most_critical_product),
    ]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, card_values):
        with col:
            kpi_card(label, value)

    if priority_risks.empty:
        st.info("Nenhum produto da Curva A exige acao imediata pelos criterios atuais.")
    else:
        st.info(
            f"{br_number(len(priority_risks))} produtos da Curva A exigem a\u00e7\u00e3o imediata, "
            f"somando {br_money(priority_impact)} de faturamento em risco."
        )

    st.plotly_chart(
        premium_curva_a_risk_bar(
            priority_risks,
            "Top 10 produtos Curva A por score de risco",
            top_n=10,
        ),
        use_container_width=True,
    )
    st.download_button(
        "Download CSV - curva A em risco",
        data=priority_risks.to_csv(index=False, encoding="utf-8-sig"),
        file_name="curva_a_em_risco.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_curva_a_em_risco",
    )
    view_columns = [
        "item_id",
        "produto",
        "marca",
        "categoria",
        "faturamento",
        "lucro_liquido_estimado",
        "margem_base",
        "classe_abc",
        "score_risco_curva_a",
        "nivel_risco",
        "motivos_risco",
        "acao_recomendada",
        "estoque_atual",
        "pedidos_ultimos_7d",
        "queda_percentual",
        "link_anuncio",
    ]
    view_columns = [column for column in view_columns if column in sorted_risks.columns]
    if not priority_risks.empty:
        st.dataframe(
            style_curva_a_risk(priority_risks[view_columns]),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

    with st.expander("Ver riscos m\u00e9dios e baixos", expanded=False):
        st.download_button(
            "Download CSV - riscos medios e baixos",
            data=secondary_risks.to_csv(index=False, encoding="utf-8-sig"),
            file_name="curva_a_riscos_medios_baixos.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_curva_a_riscos_medios_baixos",
        )
        if secondary_risks.empty:
            st.info("Nenhum risco medio ou baixo encontrado para Curva A.")
        else:
            st.dataframe(
                style_curva_a_risk(secondary_risks[view_columns]),
                use_container_width=True,
                hide_index=True,
                height=360,
            )


def render_inteligencia_comercial(
    filtered_sales: pd.DataFrame,
    financial_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> None:
    products = product_summary(financial_df, 500)
    abc = build_abc_curve(financial_df)
    bundle = build_all_alerts_bundle(filtered_sales, inventory_df, ads_df, filter_state)
    all_alerts = bundle["all"]
    stock = bundle["stock"]
    opportunities = build_executive_opportunities(financial_df, 50)
    dropoffs = build_abrupt_product_dropoffs(financial_df)
    curva_a_em_risco_df = build_curva_a_em_risco_df(abc, financial_df, stock, dropoffs)
    acoes_recomendadas_df = build_recommended_actions_df(
        financial_df,
        products,
        stock,
        dropoffs,
        ads_df,
    )
    dangerous_products = all_alerts[
        all_alerts["MLB"].fillna("N/D").ne("N/D")
        & all_alerts["tipo_alerta"].isin(
            [
                "Margem liquida negativa",
                "Lucro negativo",
                "Margem pos Ads baixa",
                "Estoque zerado com vendas recentes",
                "Estoque baixo com alta venda",
            ]
        )
    ].copy()
    no_turnover = (
        stock[
            (stock["estoque_atual"].fillna(0) > 0)
            & (stock["vendidos_total"].fillna(0) <= 0)
        ].copy()
        if not stock.empty
        else pd.DataFrame()
    )
    estimated_impact = (
        float(dangerous_products["impacto_financeiro_estimado"].fillna(0).sum())
        if not dangerous_products.empty
        else 0.0
    )
    critical_dropoffs = (
        int((dropoffs["prioridade_queda"] == "Cr\u00edtica").sum())
        if not dropoffs.empty and "prioridade_queda" in dropoffs.columns
        else 0
    )

    card_values = [
        ("Produtos em queda brusca", br_number(len(dropoffs))),
        ("Quedas criticas", br_number(critical_dropoffs)),
        ("Oportunidades", br_number(len(opportunities))),
        ("Produtos perigosos", br_number(dangerous_products["MLB"].nunique() if not dangerous_products.empty else 0)),
        ("Produtos sem giro", br_number(len(no_turnover))),
        ("Impacto financeiro estimado", br_money(estimated_impact)),
    ]
    cols = st.columns(6)
    for col, (label, value) in zip(cols, card_values):
        with col:
            kpi_card(label, value)

    st.markdown('<div class="section-title">Produtos em queda brusca</div>', unsafe_allow_html=True)
    render_abrupt_dropoffs_methodology()
    drop_impact = (
        float(dropoffs["impacto_faturamento_perdido"].fillna(0).sum())
        if not dropoffs.empty and "impacto_faturamento_perdido" in dropoffs.columns
        else 0.0
    )
    if dropoffs.empty:
        st.info("Nenhum produto com historico suficiente apresentou queda brusca pelos criterios atuais.")
    else:
        dropoffs = ensure_columns(
            dropoffs,
            {
                "motivo_queda": "N/D",
                "acao_recomendada": "N/D",
                "prioridade_queda": "N/D",
            },
        )
        reason_counts = dropoffs["motivo_queda"].fillna("N/D").astype(str).value_counts()
        estoque_critico = int(reason_counts.get("Estoque cr\u00edtico", 0))
        parou_vender = int(reason_counts.get("Produto parou de vender", 0))
        perda_relevancia = int(reason_counts.get("Poss\u00edvel perda de relev\u00e2ncia ou concorr\u00eancia", 0))
        st.info(
            f"Dos {br_number(len(dropoffs))} produtos em queda, "
            f"{br_number(estoque_critico)} t\u00eam estoque cr\u00edtico, "
            f"{br_number(parou_vender)} pararam de vender e "
            f"{br_number(perda_relevancia)} indicam poss\u00edvel perda de relev\u00e2ncia."
        )
        st.info(
            f"{br_number(len(dropoffs))} produtos apresentaram queda brusca, "
            f"com impacto estimado de {br_money(drop_impact)} em faturamento perdido nos ultimos 7 dias."
        )
        filter_reason_col, filter_priority_col = st.columns(2)
        motivo_options = sorted(dropoffs["motivo_queda"].dropna().astype(str).unique().tolist())
        prioridade_order = ["Cr\u00edtica", "Alta", "M\u00e9dia", "Baixa", "N/D"]
        prioridade_options = [
            priority
            for priority in prioridade_order
            if priority in set(dropoffs["prioridade_queda"].dropna().astype(str).tolist())
        ]
        selected_motivos = filter_reason_col.multiselect(
            "Motivo da queda",
            motivo_options,
            default=motivo_options,
            key="queda_motivo_filter",
        )
        selected_prioridades_queda = filter_priority_col.multiselect(
            "Prioridade da queda",
            prioridade_options,
            default=prioridade_options,
            key="queda_prioridade_filter",
        )
        filtered_dropoffs = dropoffs[
            dropoffs["motivo_queda"].isin(selected_motivos)
            & dropoffs["prioridade_queda"].isin(selected_prioridades_queda)
        ].copy()
        if filtered_dropoffs.empty:
            st.info("Nenhum produto em queda para os filtros selecionados.")
            chart_dropoffs = filtered_dropoffs
        else:
            chart_dropoffs = filtered_dropoffs.sort_values("impacto_faturamento_perdido", ascending=False).head(10)
        st.plotly_chart(
            premium_dropoff_impact_bar(
                chart_dropoffs,
                "Top 10 produtos por impacto de queda",
                top_n=10,
            ),
            use_container_width=True,
        )
        st.download_button(
            "Download CSV - produtos em queda brusca",
            data=filtered_dropoffs.to_csv(index=False, encoding="utf-8-sig"),
            file_name="produtos_em_queda_brusca.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_produtos_em_queda_brusca",
        )
        drop_cols = [
            "item_id",
            "produto",
            "marca",
            "categoria",
            "faturamento_30d_anteriores",
            "faturamento_ultimos_7d",
            "queda_percentual",
            "impacto_faturamento_perdido",
            "pedidos_30d_anteriores",
            "pedidos_ultimos_7d",
            "estoque_atual",
            "motivo_queda",
            "acao_recomendada",
            "prioridade_queda",
            "sugestao_automatica",
            "link_anuncio",
        ]
        drop_cols = [column for column in drop_cols if column in filtered_dropoffs.columns]
        st.dataframe(
            format_table(filtered_dropoffs[drop_cols]),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.plotly_chart(
        premium_money_bar(
            products,
            "receita",
            "produto",
            "Top faturamento",
            "#2563EB",
            top_n=10,
            gradient=True,
        ),
        use_container_width=True,
    )
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.plotly_chart(
        premium_money_bar(
            products,
            "lucro_liquido_estimado",
            "produto",
            "Top lucro",
            "#0F766E",
            top_n=10,
        ),
        use_container_width=True,
    )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    worst_margin = products[
        products["receita"].fillna(0) > 0
    ].sort_values("margem_liquida_estimada").head(10)
    st.plotly_chart(
        premium_percent_bar(
            worst_margin,
            "margem_liquida_estimada",
            "produto",
            "Piores margens",
            "#DC2626",
            top_n=10,
            ascending=True,
            impact_col="receita",
        ),
        use_container_width=True,
    )
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    abc_counts = abc.groupby("curva", as_index=False).agg(produtos=("item_id", "nunique"), receita=("receita", "sum")) if not abc.empty else pd.DataFrame()
    st.plotly_chart(
        premium_abc_donut(abc_counts),
        use_container_width=True,
    )

    render_curva_a_em_risco(curva_a_em_risco_df)

    render_central_acoes_recomendadas(acoes_recomendadas_df, financial_df, stock)

    table_cols = ["item_id", "SKU", "produto", "Marca", "Nome da Categoria", "receita", "lucro_liquido_estimado", "margem_liquida_estimada"]
    col5, col6 = st.columns(2)
    with col5:
        st.markdown('<div class="section-title">Produtos com potencial</div>', unsafe_allow_html=True)
        if opportunities.empty:
            st.info("Nenhuma oportunidade clara para os filtros atuais.")
        else:
            st.dataframe(
                format_table(opportunities[table_cols + ["potencial_estimado"]].head(15)),
                use_container_width=True,
                hide_index=True,
                height=360,
            )
    with col6:
        st.markdown('<div class="section-title">Produtos perigosos</div>', unsafe_allow_html=True)
        danger_cols = [
            "prioridade",
            "tipo_alerta",
            "impacto_financeiro_estimado",
            "MLB",
            "SKU",
            "produto",
            "marca",
            "receita",
            "lucro",
            "margem",
        ]
        if dangerous_products.empty:
            st.info("Nenhum produto perigoso para os filtros atuais.")
        else:
            st.dataframe(
                style_executive_alerts(dangerous_products[danger_cols].head(15)),
                use_container_width=True,
                hide_index=True,
                height=360,
            )

    st.markdown('<div class="section-title">Produtos sem giro</div>', unsafe_allow_html=True)
    no_turnover_cols = [
        "MLB",
        "SKU_final",
        "produto_final",
        "marca_final",
        "categoria_final",
        "estoque_atual",
        "vendidos_total",
        "status_estoque",
    ]
    if no_turnover.empty:
        st.info("Nenhum produto sem giro encontrado.")
    else:
        st.dataframe(
            format_table(no_turnover.sort_values("estoque_atual", ascending=False)[no_turnover_cols].head(20)),
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    st.markdown('<div class="section-title">Sugestao automatica de acao</div>', unsafe_allow_html=True)
    action_cols = [
        "prioridade",
        "tipo_alerta",
        "acao_recomendada",
        "responsavel_sugerido",
        "prazo_sugerido",
        "impacto_financeiro_estimado",
        "produto",
        "campanha",
    ]
    if all_alerts.empty:
        st.info("Nenhuma acao sugerida para os filtros atuais.")
    else:
        st.dataframe(
            style_action_plan(all_alerts[action_cols].head(25)),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

    with st.expander("Matrizes comerciais por marca", expanded=False):
        render_comercial(filtered_sales)
    with st.expander("Detalhamento de produtos", expanded=False):
        render_produtos(financial_df)
    with st.expander("Detalhamento de marcas", expanded=False):
        render_marcas(financial_df)


def render_estoque_giro(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    filter_state: dict[str, object],
    selected_period: tuple[date, date],
) -> None:
    """Renderiza visao executiva de estoque, giro, cobertura e alertas."""

    if inventory_df.empty:
        st.info("Base de estoque indisponivel. Gere primeiro data/ml_items_details.csv.")
        return

    stock = build_stock_view(filtered_sales, inventory_df, filter_state)
    if stock.empty:
        st.info("Nenhum anuncio encontrado para os filtros selecionados.")
        return

    kpis = calculate_stock_kpis(stock, selected_period)
    values = [
        ("Estoque total", br_number(kpis["estoque_total"])),
        ("Anuncios sem estoque", br_number(kpis["sem_estoque"])),
        ("Estoque baixo", br_number(kpis["baixo"])),
        ("Estoque normal", br_number(kpis["normal"])),
        ("Excesso de estoque", br_number(kpis["excesso"])),
        ("Produtos vendidos no periodo", br_number(kpis["vendidos_periodo"])),
        ("Giro estimado", br_number(kpis["giro_estimado"], 2)),
        ("Cobertura estimada", f"{br_number(kpis['cobertura_estimada'], 1)} dias"),
    ]
    for start in range(0, len(values), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, values[start : start + 4]):
            with col:
                kpi_card(label, value)

    status_order = ["estoque zerado", "estoque baixo", "estoque normal", "excesso estoque", "N/D"]
    status_colors = {
        "estoque zerado": "#DC2626",
        "estoque baixo": "#D97706",
        "estoque normal": "#0F766E",
        "excesso estoque": "#64748B",
        "N/D": "#94A3B8",
    }
    status_dist = (
        stock.groupby("status_estoque", as_index=False)
        .size()
        .rename(columns={"size": "anuncios"})
    )
    status_dist["status_estoque"] = pd.Categorical(status_dist["status_estoque"], status_order, ordered=True)
    status_dist = status_dist.sort_values("status_estoque")

    col1, col2 = st.columns(2)
    if status_dist.empty:
        col1.plotly_chart(empty_fig("Distribuicao por status de estoque"), use_container_width=True)
    else:
        fig_status = px.bar(
            status_dist,
            x="status_estoque",
            y="anuncios",
            color="status_estoque",
            color_discrete_map=status_colors,
        )
        fig_status.update_layout(showlegend=False)
        col1.plotly_chart(layout_chart(fig_status, "Distribuicao por status de estoque"), use_container_width=True)

    stock_brand = (
        stock.groupby("marca_final", as_index=False)
        .agg(estoque_atual=("estoque_atual", "sum"))
        .sort_values("estoque_atual", ascending=False)
        .head(15)
    )
    col2.plotly_chart(
        bar_chart(stock_brand.sort_values("estoque_atual"), "estoque_atual", "marca_final", "Estoque por marca", "h"),
        use_container_width=True,
    )

    stock_category = (
        stock.groupby("categoria_final", as_index=False)
        .agg(estoque_atual=("estoque_atual", "sum"))
        .sort_values("estoque_atual", ascending=False)
        .head(15)
    )
    top_stock = stock.sort_values("estoque_atual", ascending=False).head(20)
    col3, col4 = st.columns(2)
    col3.plotly_chart(
        bar_chart(
            stock_category.sort_values("estoque_atual"),
            "estoque_atual",
            "categoria_final",
            "Estoque por categoria",
            "h",
        ),
        use_container_width=True,
    )
    col4.plotly_chart(
        bar_chart(
            top_stock.sort_values("estoque_atual"),
            "estoque_atual",
            "produto_final",
            "Top 20 produtos com maior estoque",
            "h",
        ),
        use_container_width=True,
    )

    zero_stock = stock[stock["status_estoque"] == "estoque zerado"].sort_values(
        ["quantidade_periodo", "vendidos_total"],
        ascending=False,
    ).head(20)
    high_sales_low_stock = stock[
        stock["status_estoque"].isin(["estoque zerado", "estoque baixo"])
        & (stock["quantidade_periodo"] > 0)
    ].sort_values("quantidade_periodo", ascending=False).head(20)
    col5, col6 = st.columns(2)
    col5.plotly_chart(
        bar_chart(
            zero_stock.sort_values("quantidade_periodo"),
            "quantidade_periodo",
            "produto_final",
            "Top 20 produtos com estoque zerado",
            "h",
        ),
        use_container_width=True,
    )
    col6.plotly_chart(
        bar_chart(
            high_sales_low_stock.sort_values("quantidade_periodo"),
            "quantidade_periodo",
            "produto_final",
            "Alta venda e baixo estoque",
            "h",
        ),
        use_container_width=True,
    )

    high_margin_low_stock = stock[
        stock["status_estoque"].isin(["estoque zerado", "estoque baixo"])
        & stock["margem_liquida_estimada"].notna()
    ].sort_values("margem_liquida_estimada", ascending=False).head(20)
    full_status = (
        stock.groupby(["full_label_estoque", "status_estoque"], as_index=False)
        .size()
        .rename(columns={"size": "anuncios"})
    )
    col7, col8 = st.columns(2)
    col7.plotly_chart(
        bar_chart(
            high_margin_low_stock.sort_values("margem_liquida_estimada"),
            "margem_liquida_estimada",
            "produto_final",
            "Margem alta e baixo estoque",
            "h",
        ),
        use_container_width=True,
    )
    if full_status.empty:
        col8.plotly_chart(empty_fig("FULL x status de estoque"), use_container_width=True)
    else:
        fig_full = px.bar(
            full_status,
            x="full_label_estoque",
            y="anuncios",
            color="status_estoque",
            color_discrete_map=status_colors,
            category_orders={"status_estoque": status_order},
        )
        col8.plotly_chart(layout_chart(fig_full, "FULL x status de estoque"), use_container_width=True)

    alerts = stock[
        stock["status_estoque"].isin(["estoque zerado", "estoque baixo", "excesso estoque"])
    ].copy()
    alerts = alerts[
        [
            "MLB",
            "SKU_final",
            "produto_final",
            "marca_final",
            "categoria_final",
            "estoque_atual",
            "vendidos_total",
            "status_estoque",
            "margem_liquida_estimada",
            "lucro_liquido_estimado",
            "Link_final",
        ]
    ].rename(
        columns={
            "SKU_final": "SKU",
            "produto_final": "produto",
            "marca_final": "marca",
            "categoria_final": "categoria",
            "Link_final": "LinkAnuncio",
        }
    )
    alert_order = {"estoque zerado": 0, "estoque baixo": 1, "excesso estoque": 2}
    alerts["_ordem"] = alerts["status_estoque"].map(alert_order).fillna(99)
    alerts = alerts.sort_values(["_ordem", "vendidos_total"], ascending=[True, False]).drop(columns="_ordem")

    st.markdown('<div class="section-title">Alertas de estoque</div>', unsafe_allow_html=True)
    st.download_button(
        "Download CSV dos alertas",
        data=alerts.to_csv(index=False, encoding="utf-8-sig"),
        file_name="alertas_estoque.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.dataframe(style_stock_alerts(alerts), use_container_width=True, hide_index=True, height=520)


STOCK_KPI_TOOLTIPS = {
    "Score Saude do Estoque": (
        "Formula: media ponderada de ruptura, estoque baixo, giro, excesso de estoque e produtos parados. "
        "Meta: acima de 80. Interpretacao: quanto maior, mais equilibrado o estoque. "
        "Acao: priorizar reposicao, reducao de excesso e giro dos parados quando o score cair."
    ),
    "Estoque Total": (
        "Formula: soma de estoque_atual dos anuncios filtrados. Meta: estoque suficiente para cobrir a demanda sem excesso. "
        "Interpretacao: volume total disponivel. Acao: ler junto com cobertura e capital parado."
    ),
    "Produtos sem estoque": (
        "Formula: quantidade de anuncios com status_estoque = estoque zerado. Meta: zero. "
        "Interpretacao: risco direto de ruptura. Acao: repor ou pausar anuncio ate regularizar."
    ),
    "Estoque baixo": (
        "Formula: quantidade de anuncios com status_estoque = estoque baixo. Meta: reduzir principalmente nos itens com venda. "
        "Interpretacao: risco de ruptura futura. Acao: priorizar compras em marcas com crescimento."
    ),
    "Produtos parados": (
        "Formula: produtos com estoque relevante e baixa venda conforme alerta de estoque. Meta: reduzir. "
        "Interpretacao: capital preso em itens de baixo giro. Acao: promocao, Ads seletivo ou liquidacao controlada."
    ),
    "Capital parado": (
        "Formula: estoque_atual x valor unitario estimado, usando preco do anuncio quando CMV unitario nao esta disponivel. "
        "Meta: reduzir sem comprometer ruptura. Interpretacao: capital imobilizado em estoque. "
        "Acao: atacar o ranking de maior valor parado."
    ),
    "Cobertura media": (
        "Formula: estoque total / venda media diaria do periodo. Meta: equilibrio entre 30 e 75 dias. "
        "Interpretacao: dias estimados de estoque. Acao: comprar mais quando baixa e reduzir quando alta."
    ),
    "Alertas criticos": (
        "Formula: alertas operacionais com nivel critico ou prioridade alta. Meta: zero. "
        "Interpretacao: fila executiva de risco. Acao: tratar os primeiros itens do plano de acao."
    ),
}

STOCK_SECTION_TOOLTIPS = {
    "Score Saude do Estoque": STOCK_KPI_TOOLTIPS["Score Saude do Estoque"],
    "Resumo Executivo": "KPIs de decisao para ruptura, capital parado, cobertura e criticidade do estoque.",
    "Crescimento por Marca": (
        "Heatmap mensal usando a mesma logica de crescimento por marca da visao comercial. "
        "Meta: crescimento mensal minimo de 5%."
    ),
    "Participacao Mensal no Faturamento por Marca": (
        "Distribuicao do faturamento do mes mais recente por marca e variacao de participacao contra o mes anterior."
    ),
    "Matriz Estrategica de Compras": (
        "Quadrante executivo: eixo X = crescimento mensal da marca; eixo Y = cobertura de estoque. "
        "Classifica comprar mais, monitorar, reduzir compras ou liquidar estoque."
    ),
    "Capital Parado": "Ranking de produtos com maior valor estimado imobilizado em estoque.",
    "Alertas Executivos": "Alertas automaticos de crescimento, queda, ruptura, excesso e marcas criticas.",
    "Oportunidades Automaticas": "Recomendacoes geradas por crescimento de marca e cobertura de estoque.",
    "Ranking de Marcas": "Top crescimento, top queda e comparacao mensal das marcas.",
}


def stock_help_icon(tooltip: str) -> str:
    if not tooltip:
        return ""
    return (
        f'<span class="kpi-help" title="{html.escape(tooltip, quote=True)}" '
        'aria-label="Explicacao do indicador">&#8505;</span>'
    )


def render_stock_section_title(title: str) -> None:
    tooltip = STOCK_SECTION_TOOLTIPS.get(title, "")
    st.markdown(
        f'<div class="section-title">{html.escape(title)}{stock_help_icon(tooltip)}</div>',
        unsafe_allow_html=True,
    )


def render_stock_kpi_card(
    label: str,
    value: str,
    color: str = "#0F766E",
    detail: str = "",
    status: str = "",
    meta: str = "",
) -> str:
    tooltip = STOCK_KPI_TOOLTIPS.get(label, "")
    title_attr = f' title="{html.escape(tooltip, quote=True)}"' if tooltip else ""
    help_icon = stock_help_icon(tooltip)
    status_html = f'<div class="stock-kpi-status">{html.escape(status)}</div>' if status else ""
    meta_html = f'<div class="stock-kpi-meta">{html.escape(meta)}</div>' if meta else ""
    return (
        f'<div class="stock-kpi-card" style="--stock-color:{color};">'
        f'<div class="stock-kpi-label"{title_attr}>{html.escape(label)}{help_icon}</div>'
        f'<div class="stock-kpi-value">{html.escape(value)}</div>'
        f'<div class="stock-kpi-detail">{html.escape(detail)}</div>'
        f"{status_html}{meta_html}"
        "</div>"
    )


def stock_value_unit_series(stock: pd.DataFrame) -> pd.Series:
    candidates = [
        "cmv_seconds_unitario",
        "cmv_unitario_seconds",
        "CMV unitario",
        "CMV unitario",
        "price",
        "base_price",
    ]
    value = pd.Series(0.0, index=stock.index)
    for column in candidates:
        if column in stock.columns:
            current = pd.to_numeric(stock[column], errors="coerce")
            value = value.mask(value <= 0, current)
    return value.fillna(0).clip(lower=0)


def prepare_stock_executive_base(
    stock: pd.DataFrame,
    filtered_sales: pd.DataFrame,
    selected_period: tuple[date, date],
) -> pd.DataFrame:
    if stock.empty:
        return stock.copy()
    prepared = stock.copy()
    prepared["estoque_atual"] = pd.to_numeric(prepared["estoque_atual"], errors="coerce").fillna(0)
    prepared["quantidade_periodo"] = pd.to_numeric(prepared["quantidade_periodo"], errors="coerce").fillna(0)
    prepared["vendidos_total"] = pd.to_numeric(prepared["vendidos_total"], errors="coerce").fillna(0)
    prepared["valor_unitario_estimado"] = stock_value_unit_series(prepared)
    prepared["capital_parado"] = prepared["estoque_atual"] * prepared["valor_unitario_estimado"]
    start_date, end_date = selected_period
    period_days = max((end_date - start_date).days + 1, 1)
    prepared["venda_media_diaria"] = prepared["quantidade_periodo"] / period_days
    prepared["cobertura_dias"] = prepared.apply(
        lambda row: row["estoque_atual"] / row["venda_media_diaria"] if row["venda_media_diaria"] > 0 else 999.0,
        axis=1,
    )
    if filtered_sales.empty or "item_id" not in filtered_sales.columns:
        prepared["dias_sem_venda"] = period_days
        return prepared
    sales = filtered_sales.copy()
    date_series, _ = commercial_sales_date_series(sales)
    sales["_data_ultima_venda"] = date_series
    last_sale = sales.dropna(subset=["_data_ultima_venda"]).groupby("item_id")["_data_ultima_venda"].max()
    prepared["_ultima_venda"] = prepared["item_id"].map(last_sale)
    end_ts = pd.Timestamp(end_date)
    prepared["dias_sem_venda"] = (end_ts - prepared["_ultima_venda"]).dt.days
    prepared["dias_sem_venda"] = prepared["dias_sem_venda"].fillna(period_days).clip(lower=0)
    return prepared


def stock_health_score(
    stock: pd.DataFrame,
    stock_alerts: pd.DataFrame,
    kpis: dict[str, float],
) -> dict[str, object]:
    total_items = max(len(stock), 1)
    rupture_pct = float(kpis.get("sem_estoque", 0.0)) / total_items * 100
    low_pct = float(kpis.get("baixo", 0.0)) / total_items * 100
    excess_pct = float(kpis.get("excesso", 0.0)) / total_items * 100
    stopped = (
        int((stock_alerts["tipo_alerta"] == "Produto parado").sum())
        if not stock_alerts.empty and "tipo_alerta" in stock_alerts.columns
        else 0
    )
    stopped_pct = stopped / total_items * 100
    giro = float(kpis.get("giro_estimado", 0.0))
    components = {
        "Ruptura": score_from_thresholds(rupture_pct, [(0, 100), (3, 82), (8, 55), (999, 20)], lower_is_better=True),
        "Estoque baixo": score_from_thresholds(low_pct, [(5, 100), (12, 76), (25, 48), (999, 18)], lower_is_better=True),
        "Giro": score_from_thresholds(giro, [(0.45, 100), (0.25, 80), (0.10, 55), (0, 25)]),
        "Excesso": score_from_thresholds(excess_pct, [(5, 100), (12, 78), (25, 50), (999, 20)], lower_is_better=True),
        "Parados": score_from_thresholds(stopped_pct, [(5, 100), (12, 75), (25, 45), (999, 16)], lower_is_better=True),
    }
    weights = {"Ruptura": 0.28, "Estoque baixo": 0.20, "Giro": 0.22, "Excesso": 0.15, "Parados": 0.15}
    score = bounded_score(sum(components[key] * weights[key] for key in weights))
    if score >= 85:
        status, color = "Excelente", "#22C55E"
    elif score >= 70:
        status, color = "Saudavel", "#0F766E"
    elif score >= 50:
        status, color = "Atencao", "#D97706"
    else:
        status, color = "Critico", "#DC2626"
    rationale = (
        f"Ruptura {br_percent(rupture_pct, 1)} | Estoque baixo {br_percent(low_pct, 1)} | "
        f"Giro {br_number(giro, 2)} | Excesso {br_percent(excess_pct, 1)} | "
        f"Parados {br_percent(stopped_pct, 1)}."
    )
    return {"score": score, "status": status, "color": color, "components": components, "rationale": rationale}


def stock_health_gauge(score_info: dict[str, object]) -> go.Figure:
    return ads_health_gauge(score_info)


def monthly_brand_metrics(df: pd.DataFrame) -> pd.DataFrame:
    monthly, months, month_labels = commercial_monthly_base(df)
    if monthly.empty:
        return pd.DataFrame()

    brands = sorted(monthly["Marca"].dropna().astype(str).unique())
    grid = pd.MultiIndex.from_product([brands, months], names=["Marca", "mes_periodo"]).to_frame(index=False)
    data = grid.merge(monthly, on=["Marca", "mes_periodo"], how="left")
    data["faturamento"] = pd.to_numeric(data["faturamento"], errors="coerce").fillna(0.0)
    data["lucro_liquido_estimado"] = pd.to_numeric(data["lucro_liquido_estimado"], errors="coerce").fillna(0.0)
    data["mes_ref"] = data["mes_periodo"].map(lambda value: pd.Period(value, freq="M").to_timestamp())
    data = data.sort_values(["Marca", "mes_ref"]).reset_index(drop=True)
    data["receita_anterior"] = data.groupby("Marca")["faturamento"].shift(1).fillna(0.0)
    data["ordem_mes_marca"] = data.groupby("Marca").cumcount()
    data["crescimento"] = pd.NA
    data["status_crescimento"] = "Sem venda"

    previous = data["receita_anterior"]
    current = data["faturamento"]
    normal = (previous > 0) & (current > 0)
    drop_to_zero = (previous > 0) & (current == 0)
    starting = (previous == 0) & (current > 0)
    no_sale = (previous == 0) & (current == 0)
    data.loc[normal, "crescimento"] = (current[normal] / previous[normal] - 1) * 100
    data.loc[drop_to_zero, "crescimento"] = -100.0
    data.loc[starting, "status_crescimento"] = "Iniciando"
    data.loc[no_sale, "status_crescimento"] = "Sem venda"
    data.loc[drop_to_zero, "status_crescimento"] = "Abaixo da meta"
    growth_numeric = pd.to_numeric(data["crescimento"], errors="coerce")
    data.loc[normal & (growth_numeric >= CRESCIMENTO_META_VERDE), "status_crescimento"] = "Acima da meta"
    data.loc[
        normal
        & (growth_numeric >= CRESCIMENTO_META_AMARELO)
        & (growth_numeric < CRESCIMENTO_META_VERDE),
        "status_crescimento",
    ] = "Proximo da meta"
    data.loc[normal & (growth_numeric < CRESCIMENTO_META_AMARELO), "status_crescimento"] = "Abaixo da meta"
    data["crescimento"] = growth_numeric
    data["crescimento_anterior"] = data.groupby("Marca")["crescimento"].shift(1)
    data["crescimento_display"] = data.apply(
        lambda row: row["status_crescimento"] if pd.isna(row["crescimento"]) else signed_br_percent(row["crescimento"]),
        axis=1,
    )
    data["status_score"] = data["status_crescimento"].map(
        {"Acima da meta": 1, "Proximo da meta": 0, "Abaixo da meta": -1, "Iniciando": -2, "Sem venda": -2}
    ).fillna(-2)
    data["interpretacao_crescimento"] = data["status_crescimento"].map(
        {
            "Acima da meta": "Crescimento acima da meta; proteger disponibilidade e avaliar compra incremental.",
            "Proximo da meta": "Crescimento proximo da meta; monitorar sustentacao antes de ampliar compra.",
            "Abaixo da meta": "Crescimento abaixo da meta ou queda; revisar demanda, preco, estoque e acao comercial.",
            "Iniciando": "Marca com venda no mes atual sem base comparavel anterior.",
            "Sem venda": "Marca sem venda no mes atual e sem base comparavel positiva anterior.",
        }
    )

    totals = data.groupby("mes_periodo")["faturamento"].transform("sum")
    data["receita_total_mes"] = totals
    data["participacao"] = data["faturamento"].div(totals.where(totals > 0)) * 100
    data["participacao"] = data["participacao"].fillna(0.0)
    data["participacao_anterior"] = data.groupby("Marca")["participacao"].shift(1)
    data["variacao_participacao"] = data["participacao"] - data["participacao_anterior"]
    data["mes_label"] = data["mes_periodo"].map(month_labels)
    return data.sort_values(["Marca", "mes_ref"])


def growth_status(value: float | None, status: str | None = None) -> tuple[str, int, str]:
    if status in {"Iniciando", "Sem venda"}:
        action = (
            "Historico anterior indisponivel; monitorar primeira leitura."
            if status == "Iniciando"
            else "Sem venda na comparacao; validar ruptura, demanda e cadastro."
        )
        return str(status), -2, action
    if value is None or pd.isna(value):
        return "Iniciando", -2, "Historico anterior indisponivel; monitorar primeira leitura."
    if value >= CRESCIMENTO_META_VERDE:
        return "Acima da meta", 1, "Manter disponibilidade e avaliar compra incremental."
    if value >= CRESCIMENTO_META_AMARELO:
        return "Proximo da meta", 0, "Monitorar para confirmar sustentacao do crescimento."
    return "Abaixo da meta", -1, "Revisar mix, disponibilidade e acao comercial."


def brand_growth_heatmap(
    monthly: pd.DataFrame,
    top_n: int | None = TOP_MARCAS_HEATMAP_EXECUTIVO,
    title: str = "Crescimento mensal por marca",
) -> go.Figure:
    if monthly.empty:
        return empty_fig(title)
    brand_order = monthly.groupby("Marca")["faturamento"].sum().sort_values(ascending=False)
    if top_n is not None:
        brand_order = brand_order.head(top_n)
    brand_order = brand_order.index.tolist()
    months = sorted(monthly["mes_ref"].dropna().unique())
    chart = monthly[monthly["Marca"].isin(brand_order)].copy()
    if chart.empty:
        return empty_fig(title)
    statuses = chart.apply(lambda row: growth_status(row["crescimento"], row.get("status_crescimento")), axis=1)
    chart["status"] = [item[0] for item in statuses]
    chart["status_score"] = [item[1] for item in statuses]
    chart["acao"] = [item[2] for item in statuses]
    chart["crescimento_fmt"] = chart["crescimento_display"]
    chart["crescimento_anterior_fmt"] = chart["crescimento_anterior"].map(
        lambda value: "N/D" if pd.isna(value) else signed_br_percent(value)
    )
    chart["receita_atual_fmt"] = chart["faturamento"].map(br_money)
    chart["receita_anterior_fmt"] = chart["receita_anterior"].map(br_money)
    chart["meta_fmt"] = f"Verde >= {br_percent(CRESCIMENTO_META_VERDE, 0)} | Amarelo >= {br_percent(CRESCIMENTO_META_AMARELO, 0)}"
    pivot = (
        chart.pivot_table(index="Marca", columns="mes_ref", values="status_score", aggfunc="first")
        .reindex(index=brand_order, columns=months)
    )
    text = (
        chart.pivot_table(index="Marca", columns="mes_ref", values="crescimento_fmt", aggfunc="first")
        .reindex(index=brand_order, columns=months)
    )
    custom = chart.pivot_table(
        index="Marca",
        columns="mes_ref",
        values=[
            "crescimento_fmt",
            "crescimento_anterior_fmt",
            "meta_fmt",
            "status",
            "acao",
            "receita_atual_fmt",
            "receita_anterior_fmt",
            "interpretacao_crescimento",
        ],
        aggfunc="first",
    ).reindex(index=brand_order)
    custom_array = []
    for brand in pivot.index:
        row = []
        for month in pivot.columns:
            row.append(
                [
                    custom.loc[brand, ("crescimento_fmt", month)] if ("crescimento_fmt", month) in custom.columns else "N/D",
                    custom.loc[brand, ("crescimento_anterior_fmt", month)] if ("crescimento_anterior_fmt", month) in custom.columns else "N/D",
                    custom.loc[brand, ("meta_fmt", month)] if ("meta_fmt", month) in custom.columns else "N/D",
                    custom.loc[brand, ("status", month)] if ("status", month) in custom.columns else "N/D",
                    custom.loc[brand, ("acao", month)] if ("acao", month) in custom.columns else "Monitorar.",
                    custom.loc[brand, ("receita_atual_fmt", month)] if ("receita_atual_fmt", month) in custom.columns else "N/D",
                    custom.loc[brand, ("receita_anterior_fmt", month)] if ("receita_anterior_fmt", month) in custom.columns else "N/D",
                    custom.loc[brand, ("interpretacao_crescimento", month)] if ("interpretacao_crescimento", month) in custom.columns else "N/D",
                ]
            )
        custom_array.append(row)
    x_labels = [month_label_short_pt(month) for month in pivot.columns]
    fig = go.Figure(
        go.Heatmap(
            z=pivot.fillna(-2).values,
            x=x_labels,
            y=list(pivot.index),
            text=text.reindex(index=pivot.index, columns=pivot.columns).fillna("Sem venda").values,
            texttemplate="%{text}",
            textfont={"size": 11, "color": "#F8FAFC"},
            customdata=custom_array,
            zmin=-2,
            zmax=1,
            colorscale=[
                [0.0, "#64748B"],
                [0.24, "#64748B"],
                [0.25, "#DC2626"],
                [0.49, "#DC2626"],
                [0.50, "#D97706"],
                [0.74, "#D97706"],
                [0.75, "#0F766E"],
                [1.0, "#22C55E"],
            ],
            showscale=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Mes: %{x}<br>"
                "Receita mes atual: %{customdata[5]}<br>"
                "Receita mes anterior: %{customdata[6]}<br>"
                "Crescimento do mes: %{customdata[0]}<br>"
                "Crescimento anterior: %{customdata[1]}<br>"
                "Meta utilizada: %{customdata[2]}<br>"
                "Status: %{customdata[3]}<br>"
                "Formula: faturamento do mes / faturamento do mes anterior - 1.<br>"
                "Interpretacao: %{customdata[7]}<br>"
                "Acao recomendada: %{customdata[4]}<extra></extra>"
            ),
        )
    )
    return layout_chart(fig, title, 470)


def brand_growth_rankings(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if monthly.empty:
        empty = pd.DataFrame(columns=["Marca", "crescimento", "faturamento", "receita_anterior"])
        return empty, empty, empty
    latest_month = monthly["mes_ref"].max()
    latest = monthly[monthly["mes_ref"] == latest_month].copy()
    valid = latest.dropna(subset=["crescimento"]).copy()
    top_growth = valid.sort_values("crescimento", ascending=False).head(6)
    top_drop = valid.sort_values("crescimento", ascending=True).head(6)
    starting = latest[(latest["status_crescimento"] == "Iniciando") & (latest["faturamento"] > 0)].sort_values(
        "faturamento", ascending=False
    ).head(6)
    return top_growth, top_drop, starting


def stock_growth_insights(monthly: pd.DataFrame) -> list[str]:
    if monthly.empty:
        return ["Sem dados mensais suficientes para gerar insights de crescimento por marca."]
    latest_month = monthly["mes_ref"].max()
    latest = monthly[monthly["mes_ref"] == latest_month].copy()
    latest_label = month_label_pt(latest_month)
    insights: list[str] = []
    valid_growth = latest.dropna(subset=["crescimento"])
    if not valid_growth.empty:
        top = valid_growth.sort_values("crescimento", ascending=False).iloc[0]
        if safe_number(top["crescimento"]) >= CRESCIMENTO_META_VERDE:
            insights.append(
                f"{safe_text(top['Marca'])} cresceu {signed_br_percent(top['crescimento'])} em {latest_label}, "
                f"acima da meta de {br_percent(CRESCIMENTO_META_VERDE, 0)}."
            )
        drop = valid_growth.sort_values("crescimento", ascending=True).iloc[0]
        if safe_number(drop["crescimento"]) < CRESCIMENTO_META_AMARELO:
            insights.append(
                f"{safe_text(drop['Marca'])} caiu {signed_br_percent(drop['crescimento'])} em {latest_label} e exige revisao."
            )
    share_loss = latest.dropna(subset=["variacao_participacao"]).sort_values("variacao_participacao").head(1)
    if not share_loss.empty and safe_number(share_loss.iloc[0]["variacao_participacao"]) < 0:
        row = share_loss.iloc[0]
        insights.append(
            f"{safe_text(row['Marca'])} perdeu {br_pp(row['variacao_participacao'])} de participacao no faturamento no mes mais recente."
        )
    latest_positive = latest[latest["faturamento"] > 0].sort_values("participacao", ascending=False)
    if not latest_positive.empty:
        concentration = latest_positive.head(5)["participacao"].sum()
        insights.append(f"As 5 maiores marcas concentram {br_percent(concentration, 1)} do faturamento de {latest_label}.")
    return insights[:4] if insights else ["Sem desvio relevante de crescimento ou participacao no mes mais recente."]


def brand_participation_chart(monthly: pd.DataFrame) -> go.Figure:
    title = "Participacao do mes mais recente"
    if monthly.empty:
        return empty_fig(title)
    latest_month = monthly["mes_ref"].max()
    chart = monthly[monthly["mes_ref"] == latest_month].copy()
    chart = chart[chart["faturamento"] > 0].sort_values("participacao", ascending=False).head(12)
    if chart.empty:
        return empty_fig(title)
    chart["participacao_fmt"] = chart["participacao"].map(br_percent)
    chart["variacao_fmt"] = chart["variacao_participacao"].map(lambda value: "N/D" if pd.isna(value) else br_pp(value))
    chart["receita_fmt"] = chart["faturamento"].map(br_money)
    chart["receita_total_fmt"] = chart["receita_total_mes"].map(br_money)
    chart["ganho_perda"] = chart["variacao_participacao"].map(
        lambda value: "Ganho de participacao" if safe_number(value) > 0 else ("Perda de participacao" if safe_number(value) < 0 else "Estavel")
    )
    fig = px.treemap(
        chart,
        path=["Marca"],
        values="faturamento",
        color="variacao_participacao",
        color_continuous_scale="RdYlGn",
        custom_data=["participacao_fmt", "variacao_fmt", "ganho_perda", "mes_label", "receita_fmt", "receita_total_fmt"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Mes: %{customdata[3]}<br>"
            "Receita da marca: %{customdata[4]}<br>"
            "Receita total do mes: %{customdata[5]}<br>"
            "Participacao: %{customdata[0]}<br>"
            "Variacao vs mes anterior: %{customdata[1]}<br>"
            "Leitura: %{customdata[2]}<br>"
            "Formula: faturamento da marca / faturamento total do mes.<br>"
            "Acao recomendada: proteger marcas que ganham share e revisar marcas que perdem share.<extra></extra>"
        )
    )
    fig.update_layout(coloraxis_showscale=False)
    return layout_chart(fig, title, 430)


def brand_participation_trend_chart(monthly: pd.DataFrame, top_n: int = TOP_MARCAS_PARTICIPACAO_TENDENCIA) -> go.Figure:
    title = "Tendencia de participacao - Top 10 marcas"
    if monthly.empty:
        return empty_fig(title)
    top_brands = monthly.groupby("Marca")["faturamento"].sum().sort_values(ascending=False).head(top_n).index
    chart = monthly[monthly["Marca"].isin(top_brands)].copy().sort_values(["mes_ref", "Marca"])
    if chart.empty:
        return empty_fig(title)
    month_order = [month_label_short_pt(month) for month in sorted(chart["mes_ref"].unique())]
    chart["participacao_fmt"] = chart["participacao"].map(br_percent)
    chart["variacao_fmt"] = chart["variacao_participacao"].map(lambda value: "N/D" if pd.isna(value) else br_pp(value))
    chart["receita_fmt"] = chart["faturamento"].map(br_money)
    chart["receita_total_fmt"] = chart["receita_total_mes"].map(br_money)
    fig = px.line(
        chart,
        x="mes_label",
        y="participacao",
        color="Marca",
        markers=True,
        color_discrete_sequence=COLORWAY,
        custom_data=["Marca", "mes_label", "receita_fmt", "receita_total_fmt", "participacao_fmt", "variacao_fmt"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Mes: %{customdata[1]}<br>"
            "Receita da marca: %{customdata[2]}<br>"
            "Receita total do mes: %{customdata[3]}<br>"
            "Participacao: %{customdata[4]}<br>"
            "Variacao vs mes anterior: %{customdata[5]}<br>"
            "Formula: faturamento da marca / faturamento total do mes.<br>"
            "Acao recomendada: proteger marcas que ganham share e revisar marcas que perdem share.<extra></extra>"
        )
    )
    fig.update_xaxes(categoryorder="array", categoryarray=month_order, title_text="Mes")
    fig.update_yaxes(title_text="Participacao no faturamento (%)")
    return layout_chart(fig, title, 430)


def format_brand_growth_table(frame: pd.DataFrame, mode: str = "growth") -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    view = frame.copy()
    if mode == "starting":
        view = view[["Marca", "faturamento"]].rename(columns={"faturamento": "Receita atual"})
        view["Receita atual"] = view["Receita atual"].map(br_money)
        return view
    view = view[["Marca", "crescimento", "faturamento", "receita_anterior"]].rename(
        columns={
            "crescimento": "Crescimento",
            "faturamento": "Receita atual",
            "receita_anterior": "Receita anterior",
        }
    )
    view["Crescimento"] = view["Crescimento"].map(signed_br_percent)
    view["Receita atual"] = view["Receita atual"].map(br_money)
    view["Receita anterior"] = view["Receita anterior"].map(br_money)
    return view


def latest_brand_growth(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame(columns=["Marca", "crescimento", "crescimento_anterior", "participacao", "variacao_participacao"])
    idx = monthly.sort_values("mes_ref").groupby("Marca").tail(1).index
    return monthly.loc[idx].copy()


def brand_purchase_matrix(stock: pd.DataFrame, monthly: pd.DataFrame, selected_period: tuple[date, date]) -> pd.DataFrame:
    if stock.empty:
        return pd.DataFrame()
    start_date, end_date = selected_period
    period_days = max((end_date - start_date).days + 1, 1)
    brand = (
        stock.groupby("marca_final", as_index=False)
        .agg(
            estoque_total=("estoque_atual", "sum"),
            venda_periodo=("quantidade_periodo", "sum"),
            capital_parado=("capital_parado", "sum"),
            produtos=("item_id", "nunique"),
        )
        .rename(columns={"marca_final": "Marca"})
    )
    brand["venda_media_diaria"] = brand["venda_periodo"] / period_days
    brand["cobertura_dias"] = brand.apply(
        lambda row: row["estoque_total"] / row["venda_media_diaria"] if row["venda_media_diaria"] > 0 else 999.0,
        axis=1,
    )
    latest = latest_brand_growth(monthly)[["Marca", "crescimento", "crescimento_anterior", "participacao", "variacao_participacao"]]
    brand = brand.merge(latest, on="Marca", how="left")
    brand["crescimento"] = pd.to_numeric(brand["crescimento"], errors="coerce").fillna(0)
    brand["participacao"] = pd.to_numeric(brand["participacao"], errors="coerce").fillna(0)

    def classify(row: pd.Series) -> tuple[str, str, str, str]:
        growth = safe_number(row.get("crescimento"))
        coverage = safe_number(row.get("cobertura_dias"))
        if growth >= META_OPERACIONAL_TOTAL_PERCENTUAL and coverage < 30:
            return "Comprar Mais", "#22C55E", "Marca cresce acima da meta e cobertura esta baixa.", "Aumentar compra/reposicao."
        if growth >= META_OPERACIONAL_TOTAL_PERCENTUAL and coverage <= 75:
            return "Monitorar", "#2563EB", "Marca cresce com cobertura equilibrada.", "Manter compra planejada."
        if growth < 0 and coverage > 90:
            return "Liquidar Estoque", "#DC2626", "Marca em queda com cobertura alta.", "Reduzir preco, criar promocao ou liquidar."
        if coverage > 75 or growth < META_OPERACIONAL_TOTAL_PERCENTUAL - 2:
            return "Reduzir Compras", "#D97706", "Crescimento abaixo da meta ou cobertura elevada.", "Segurar novas compras."
        return "Monitorar", "#2563EB", "Marca proxima da meta com risco controlado.", "Acompanhar proximo ciclo."

    classified = brand.apply(classify, axis=1, result_type="expand")
    brand["classificacao"] = classified[0]
    brand["cor"] = classified[1]
    brand["racional"] = classified[2]
    brand["acao_recomendada"] = classified[3]
    return brand.sort_values(["classificacao", "capital_parado"], ascending=[True, False])


def purchase_matrix_chart(matrix: pd.DataFrame) -> go.Figure:
    title = "Crescimento x Cobertura"
    if matrix.empty:
        return empty_fig(title)
    chart = matrix.copy()
    chart["cobertura_plot"] = chart["cobertura_dias"].clip(upper=180)
    chart["crescimento_fmt"] = chart["crescimento"].map(br_percent)
    chart["cobertura_fmt"] = chart["cobertura_dias"].map(lambda value: f"{br_number(value, 1)} dias")
    chart["capital_fmt"] = chart["capital_parado"].map(br_money)
    color_map = {
        "Comprar Mais": "#22C55E",
        "Monitorar": "#2563EB",
        "Reduzir Compras": "#D97706",
        "Liquidar Estoque": "#DC2626",
    }
    fig = px.scatter(
        chart,
        x="crescimento",
        y="cobertura_plot",
        size="capital_parado",
        color="classificacao",
        color_discrete_map=color_map,
        hover_name="Marca",
        custom_data=["crescimento_fmt", "cobertura_fmt", "capital_fmt", "racional", "acao_recomendada", "classificacao"],
        size_max=42,
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Crescimento da marca: %{customdata[0]}<br>"
            "Cobertura de estoque: %{customdata[1]}<br>"
            "Capital parado: %{customdata[2]}<br>"
            "Classificacao: %{customdata[5]}<br>"
            "Formula: X = crescimento mensal; Y = estoque / venda media diaria.<br>"
            "Meta: crescimento >= 5% e cobertura entre 30 e 75 dias.<br>"
            "Interpretacao: %{customdata[3]}<br>"
            "Acao recomendada: %{customdata[4]}<extra></extra>"
        )
    )
    fig.add_vline(x=META_OPERACIONAL_TOTAL_PERCENTUAL, line_width=1, line_dash="dash", line_color="rgba(148,163,184,.6)")
    fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="rgba(148,163,184,.5)")
    fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="rgba(148,163,184,.5)")
    fig.update_xaxes(title_text="Crescimento da marca (%)")
    fig.update_yaxes(title_text="Cobertura de estoque (dias)", range=[0, max(90, float(chart["cobertura_plot"].max() or 90) * 1.08)])
    return layout_chart(fig, title, 520)


def capital_parado_ranking(stock: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    if stock.empty:
        return pd.DataFrame()
    ranking = stock.copy()
    ranking = ranking[ranking["estoque_atual"] > 0].sort_values("capital_parado", ascending=False).head(top_n)
    return ranking


def capital_parado_chart(ranking: pd.DataFrame) -> go.Figure:
    title = "Produtos com maior capital parado"
    if ranking.empty:
        return empty_fig(title)
    chart = ranking.copy()
    chart["produto_resumido"] = chart["produto_final"].map(short_product_label)
    chart["capital_fmt"] = chart["capital_parado"].map(br_money)
    chart["estoque_fmt"] = chart["estoque_atual"].map(lambda value: br_number(value, 0))
    chart["dias_fmt"] = chart["dias_sem_venda"].map(lambda value: f"{br_number(value, 0)} dias")
    fig = go.Figure(
        go.Bar(
            x=chart["capital_parado"],
            y=chart["produto_resumido"],
            orientation="h",
            marker=dict(color="#D97706"),
            customdata=chart[["produto_final", "estoque_fmt", "dias_fmt", "capital_fmt", "marca_final"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Marca: %{customdata[4]}<br>"
                "Estoque: %{customdata[1]}<br>"
                "Dias sem venda: %{customdata[2]}<br>"
                "Valor estimado parado: %{customdata[3]}<br>"
                "Formula: estoque x valor unitario estimado.<br>"
                "Acao recomendada: reduzir estoque, promocionar ou liquidar conforme giro.<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(autorange="reversed")
    return layout_chart(fig, title, 470)


def build_stock_executive_alerts(
    kpis: dict[str, float],
    matrix: pd.DataFrame,
    monthly: pd.DataFrame,
    stock_alerts: pd.DataFrame,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    latest = latest_brand_growth(monthly)
    if not latest.empty and latest["crescimento"].notna().any():
        top_growth = latest.sort_values("crescimento", ascending=False).iloc[0]
        top_drop = latest.sort_values("crescimento", ascending=True).iloc[0]
        if safe_number(top_growth.get("crescimento")) >= META_OPERACIONAL_TOTAL_PERCENTUAL:
            alerts.append(
                {
                    "criticidade": "Oportunidade",
                    "titulo": "Crescimento relevante",
                    "detalhe": f"{safe_text(top_growth['Marca'])}: {br_percent(top_growth['crescimento'])}. Comprar com cobertura controlada.",
                }
            )
        if safe_number(top_drop.get("crescimento")) < 0:
            alerts.append(
                {
                    "criticidade": "Alta",
                    "titulo": "Queda relevante",
                    "detalhe": f"{safe_text(top_drop['Marca'])}: {br_percent(top_drop['crescimento'])}. Revisar compra e acao comercial.",
                }
            )
    if safe_number(kpis.get("sem_estoque")) > 0:
        alerts.append(
            {
                "criticidade": "Alta",
                "titulo": "Ruptura",
                "detalhe": f"{br_number(kpis['sem_estoque'], 0)} produtos sem estoque. Repor ou pausar anuncios.",
            }
        )
    if safe_number(kpis.get("excesso")) > 0:
        alerts.append(
            {
                "criticidade": "Media",
                "titulo": "Excesso de estoque",
                "detalhe": f"{br_number(kpis['excesso'], 0)} produtos com excesso. Reduzir compras e ativar giro.",
            }
        )
    critical_brands = int((matrix["classificacao"] == "Liquidar Estoque").sum()) if not matrix.empty else 0
    if critical_brands:
        alerts.append(
            {
                "criticidade": "Alta",
                "titulo": "Marcas criticas",
                "detalhe": f"{critical_brands} marcas no quadrante Liquidar Estoque. Tratar antes de novas compras.",
            }
        )
    if stock_alerts.empty and not alerts:
        alerts.append(
            {
                "criticidade": "Saudavel",
                "titulo": "Sem alerta critico",
                "detalhe": "Estoque sem ruptura critica nos filtros atuais. Manter monitoramento.",
            }
        )
    return alerts[:6]


def render_stock_exec_css() -> None:
    st.markdown(
        """
<style>
.stock-score-layout{display:grid;grid-template-columns:minmax(260px,.9fr) minmax(0,1.25fr);gap:.85rem;align-items:stretch;margin-bottom:1rem;}
.stock-score-panel{border:1px solid rgba(148,163,184,.18);border-radius:8px;padding:.75rem .9rem;background:rgba(15,23,42,.18);}
.stock-score-title{display:flex;align-items:center;color:rgba(226,232,240,.98);font-size:.95rem;font-weight:950;margin-bottom:.3rem;}
.stock-score-status{color:var(--score-color);font-size:1rem;font-weight:950;margin-top:-.2rem;text-align:center;}
.stock-score-components{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem;}
.stock-score-component{border:1px solid rgba(148,163,184,.16);border-radius:8px;padding:.65rem;background:rgba(2,6,23,.18);}
.stock-score-component-label{color:rgba(148,163,184,.98);font-size:.7rem;font-weight:900;text-transform:uppercase;}
.stock-score-component-value{color:rgba(226,232,240,.98);font-size:1.05rem;font-weight:950;margin-top:.22rem;}
.stock-score-rationale{color:rgba(148,163,184,.98);font-size:.8rem;font-weight:720;line-height:1.35;margin-top:.65rem;}
.stock-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin-bottom:1rem;}
.stock-kpi-card{border:1px solid rgba(148,163,184,.18);border-top:4px solid var(--stock-color);border-radius:8px;padding:.9rem;background:linear-gradient(180deg,color-mix(in srgb,var(--stock-color) 9%,transparent),rgba(15,23,42,.12));min-height:142px;}
.stock-kpi-label{display:flex;align-items:center;color:rgba(148,163,184,.96);font-size:.72rem;font-weight:900;text-transform:uppercase;margin-bottom:.4rem;}
.stock-kpi-value{color:var(--stock-color);font-size:1.35rem;line-height:1.08;font-weight:950;}
.stock-kpi-detail{color:rgba(148,163,184,.98);font-size:.78rem;font-weight:720;margin-top:.45rem;line-height:1.35;}
.stock-kpi-status{color:rgba(226,232,240,.96);font-size:.72rem;font-weight:900;margin-top:.58rem;}
.stock-kpi-meta{color:rgba(148,163,184,.92);font-size:.7rem;font-weight:720;margin-top:.18rem;}
.stock-alert-grid,.stock-opportunity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.7rem;margin-bottom:1rem;}
.stock-alert-card,.stock-opportunity-card{border:1px solid rgba(148,163,184,.18);border-left:4px solid var(--alert-color);border-radius:8px;padding:.82rem .9rem;background:color-mix(in srgb,var(--alert-color) 8%,transparent);min-height:126px;}
.stock-alert-severity{color:var(--alert-color);font-size:.68rem;text-transform:uppercase;font-weight:900;margin-bottom:.35rem;}
.stock-alert-title{color:rgba(226,232,240,.96);font-weight:900;line-height:1.22;margin-bottom:.35rem;}
.stock-alert-detail{color:rgba(148,163,184,.98);font-size:.8rem;font-weight:680;line-height:1.35;}
.mini-title{color:rgba(226,232,240,.96);font-size:.82rem;font-weight:950;text-transform:uppercase;margin:.15rem 0 .45rem;}
@media(max-width:900px){.stock-score-layout,.stock-kpi-grid{grid-template-columns:1fr;}}
</style>
        """,
        unsafe_allow_html=True,
    )


def build_decision_quadrants(
    stock: pd.DataFrame,
    matrix: pd.DataFrame,
    filtered_sales: pd.DataFrame,
) -> pd.DataFrame:
    """Classifica produtos em 4 quadrantes de decisão: INVESTIR / COMPRAR / LIQUIDAR / IGNORAR.

    Critérios por produto (cruzando dados de stock com crescimento da marca via matrix):
      - crescimento_marca >= META_OPERACIONAL_TOTAL_PERCENTUAL → cresce
      - cobertura_dias >= 15 → tem estoque

    Quadrantes:
      INVESTIR  : cresce + tem estoque  → garantir disponibilidade
      COMPRAR   : cresce + sem estoque  → risco de ruptura iminente
      LIQUIDAR  : não cresce + tem estoque → capital parado
      IGNORAR   : não cresce + sem estoque  → baixa prioridade
    """
    if stock.empty:
        return pd.DataFrame()

    # Mapear crescimento da marca para cada produto
    brand_growth = {}
    if not matrix.empty and "Marca" in matrix.columns and "crescimento" in matrix.columns:
        brand_growth = dict(zip(
            matrix["Marca"].astype(str),
            pd.to_numeric(matrix["crescimento"], errors="coerce").fillna(0),
        ))

    s = stock.copy()
    s["_crescimento_marca"] = s["marca_final"].astype(str).map(brand_growth).fillna(0)
    s["_cresce"] = s["_crescimento_marca"] >= META_OPERACIONAL_TOTAL_PERCENTUAL
    s["_tem_estoque"] = s["cobertura_dias"].fillna(999) >= 15

    def _quad(row: pd.Series) -> str:
        if row["_cresce"] and row["_tem_estoque"]:
            return "INVESTIR"
        if row["_cresce"] and not row["_tem_estoque"]:
            return "COMPRAR"
        if not row["_cresce"] and row["_tem_estoque"]:
            return "LIQUIDAR"
        return "IGNORAR"

    s["quadrante"] = s.apply(_quad, axis=1)

    # Receita por produto para impacto financeiro
    if not filtered_sales.empty and "item_id" in filtered_sales.columns:
        receita_map = (
            filtered_sales.groupby("item_id")["receita"]
            .sum()
            .to_dict()
        )
        s["_receita"] = s["item_id"].map(receita_map).fillna(0)
    else:
        s["_receita"] = s.get("receita", pd.Series(0, index=s.index)).fillna(0)

    s["_capital"] = s["capital_parado"].fillna(0)
    return s[[
        "item_id", "produto_final", "marca_final", "quadrante",
        "_crescimento_marca", "cobertura_dias", "estoque_atual",
        "_receita", "_capital",
    ]].copy()


def build_stock_sales_daily(
    filtered_sales: pd.DataFrame,
    stock: pd.DataFrame,
) -> pd.DataFrame:
    """Constrói série diária de vendas + estoque total (snapshot do último valor).

    Retorna DataFrame com: _data, vendas_dia, estoque_snap, mm7_vendas, mm30_vendas.
    Estoque é constante (inventário atual) — representa o saldo atual vs volume de vendas.
    """
    if filtered_sales.empty:
        return pd.DataFrame()

    sales = filtered_sales.copy()
    date_series, _ = commercial_sales_date_series(sales)
    sales["_data"] = date_series
    sales = sales.dropna(subset=["_data"])
    if sales.empty:
        return pd.DataFrame()

    daily = (
        sales.groupby("_data", as_index=False)
        .agg(vendas_dia=("quantity", "sum"), receita_dia=("receita", "sum"))
        .sort_values("_data")
        .reset_index(drop=True)
    )
    daily["mm7_vendas"] = daily["vendas_dia"].rolling(7, min_periods=1).mean().round(1)
    daily["mm30_vendas"] = daily["vendas_dia"].rolling(30, min_periods=1).mean().round(1)

    estoque_total = float(stock["estoque_atual"].fillna(0).sum()) if not stock.empty else 0.0
    daily["estoque_snap"] = estoque_total  # saldo atual como referência constante

    # Linha de ruptura: dias em que vendas > estoque total restante simulado
    daily["_data_ts"] = pd.to_datetime(daily["_data"])
    return daily


def build_capital_parado_enriched(
    stock: pd.DataFrame,
    filtered_sales: pd.DataFrame,
    selected_period: tuple[date, date],
) -> pd.DataFrame:
    """Enriquece capital parado com % do faturamento e impacto estimado no caixa."""
    if stock.empty:
        return pd.DataFrame()

    receita_total = float(filtered_sales["receita"].sum()) if not filtered_sales.empty else 0.0
    _, end_date = selected_period
    period_days = max((end_date - selected_period[0]).days + 1, 1)

    ranking = stock[stock["estoque_atual"] > 0].sort_values("capital_parado", ascending=False).copy()
    ranking["capital_pct_fat"] = (
        ranking["capital_parado"] / receita_total * 100
        if receita_total > 0
        else 0.0
    )
    # Dias de giro: capital_parado / (venda_media_diaria * valor_unitario)
    ranking["dias_giro_est"] = ranking.apply(
        lambda r: (
            r["estoque_atual"] / r["venda_media_diaria"]
            if r.get("venda_media_diaria", 0) > 0
            else 999
        ),
        axis=1,
    )
    ranking["dias_giro_est"] = ranking["dias_giro_est"].clip(upper=999).round(0)
    return ranking.head(20)


def build_intelligent_stock_alerts(
    stock: pd.DataFrame,
    matrix: pd.DataFrame,
    monthly: pd.DataFrame,
    kpis: dict[str, float],
    capital_parado_total: float,
    receita_total: float,
) -> list[dict[str, str]]:
    """Alertas executivos inteligentes com regras ampliadas."""
    alerts: list[dict[str, str]] = []

    # 1. Produtos parados > 30 dias com estoque relevante
    if not stock.empty:
        parados_30 = stock[
            (stock.get("dias_sem_venda", pd.Series(0, index=stock.index)).fillna(999) > 30)
            & (stock["estoque_atual"].fillna(0) > 0)
            & (stock["capital_parado"].fillna(0) > 0)
        ]
        if not parados_30.empty:
            n = len(parados_30)
            cap = float(parados_30["capital_parado"].sum())
            alerts.append({
                "criticidade": "Alta",
                "titulo": f"{n} produto(s) parados há mais de 30 dias",
                "detalhe": f"Capital imobilizado: {br_money(cap)}. Avaliar promoção ou liquidação.",
            })

    # 2. Crescimento alto sem estoque (oportunidade perdida)
    if not matrix.empty:
        opp_lost = matrix[
            (matrix["crescimento"].fillna(0) >= META_OPERACIONAL_TOTAL_PERCENTUAL)
            & (matrix["cobertura_dias"].fillna(999) < 15)
        ]
        if not opp_lost.empty:
            marcas = ", ".join(opp_lost["Marca"].astype(str).head(3).tolist())
            alerts.append({
                "criticidade": "Alta",
                "titulo": f"Crescimento sem cobertura: {opp_lost.shape[0]} marca(s)",
                "detalhe": f"{marcas}. Vendas crescendo mas estoque crítico — compra urgente.",
            })

    # 3. Concentração de capital parado por marca
    if not stock.empty and capital_parado_total > 0:
        capital_marca = (
            stock.groupby("marca_final")["capital_parado"]
            .sum()
            .sort_values(ascending=False)
        )
        if not capital_marca.empty:
            top_marca = capital_marca.index[0]
            top_val = float(capital_marca.iloc[0])
            pct = top_val / capital_parado_total * 100
            if pct > 40:
                alerts.append({
                    "criticidade": "Media",
                    "titulo": f"Concentração de capital: {top_marca}",
                    "detalhe": f"{br_percent(pct)} do capital parado em uma única marca ({br_money(top_val)}). Diversificar ou liquidar.",
                })

    # 4. Capital parado como % do faturamento
    if receita_total > 0 and capital_parado_total > 0:
        pct_fat = capital_parado_total / receita_total * 100
        if pct_fat > 30:
            alerts.append({
                "criticidade": "Alta",
                "titulo": "Capital parado excessivo",
                "detalhe": f"{br_percent(pct_fat)} do faturamento está imobilizado em estoque parado ({br_money(capital_parado_total)}). Revisar política de compras.",
            })

    # 5. Ruptura + excesso simultâneos (desbalanceamento)
    sem_estoque = safe_number(kpis.get("sem_estoque"))
    excesso = safe_number(kpis.get("excesso"))
    if sem_estoque > 0 and excesso > 0:
        alerts.append({
            "criticidade": "Media",
            "titulo": "Desbalanceamento: ruptura e excesso simultâneos",
            "detalhe": f"{br_number(sem_estoque, 0)} itens sem estoque e {br_number(excesso, 0)} com excesso. Redistribuir compras.",
        })

    # 6. Alertas existentes (compatibilidade)
    latest = latest_brand_growth(monthly)
    if not latest.empty and latest["crescimento"].notna().any():
        top_growth = latest.sort_values("crescimento", ascending=False).iloc[0]
        top_drop = latest.sort_values("crescimento", ascending=True).iloc[0]
        if safe_number(top_growth.get("crescimento")) >= META_OPERACIONAL_TOTAL_PERCENTUAL:
            alerts.append({
                "criticidade": "Oportunidade",
                "titulo": "Crescimento relevante",
                "detalhe": f"{safe_text(top_growth['Marca'])}: {br_percent(top_growth['crescimento'])}. Comprar com cobertura controlada.",
            })
        if safe_number(top_drop.get("crescimento")) < 0:
            alerts.append({
                "criticidade": "Alta",
                "titulo": "Queda relevante",
                "detalhe": f"{safe_text(top_drop['Marca'])}: {br_percent(top_drop['crescimento'])}. Revisar compra e ação comercial.",
            })

    return alerts[:7]


def render_operacional_estoque(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
    selected_period: tuple[date, date],
) -> None:
    bundle = build_all_alerts_bundle(filtered_sales, inventory_df, ads_df, filter_state)
    stock = prepare_stock_executive_base(bundle["stock"], filtered_sales, selected_period)
    stock_alerts = bundle["stock_alerts"]
    registration_alerts = bundle["registration"]
    operational_alerts = enrich_action_plan(
        prioritize_alerts(pd.concat([stock_alerts, registration_alerts], ignore_index=True))
    )
    kpis = calculate_stock_kpis(stock, selected_period) if not stock.empty else {
        "estoque_total": 0,
        "sem_estoque": 0,
        "baixo": 0,
    }
    stopped_products = (
        int((stock_alerts["tipo_alerta"] == "Produto parado").sum())
        if not stock_alerts.empty
        else 0
    )
    due_today = (
        int((operational_alerts["prazo_sugerido"] == "Hoje").sum())
        if not operational_alerts.empty and "prazo_sugerido" in operational_alerts.columns
        else 0
    )
    critical_alerts = (
        int((operational_alerts["nivel"] == "critico").sum())
        if not operational_alerts.empty
        else 0
    )
    capital_parado_total = float(stock["capital_parado"].fillna(0).sum()) if not stock.empty else 0.0
    cobertura_media = float(kpis.get("cobertura_estimada", 0.0) or 0.0)
    monthly = monthly_brand_metrics(filtered_sales)
    matrix = brand_purchase_matrix(stock, monthly, selected_period)
    score_info = stock_health_score(stock, stock_alerts, kpis)
    capital_ranking = capital_parado_ranking(stock)  # necessário para expander "Detalhes de capital parado"
    render_stock_exec_css()

    # CSS adicional para os novos blocos
    st.markdown("""
<style>
.stock-quad-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.8rem;margin-bottom:1rem;}
.stock-quad-card{border:1px solid rgba(148,163,184,.18);border-left:5px solid var(--quad-color);border-radius:8px;padding:.9rem 1rem;background:color-mix(in srgb,var(--quad-color) 9%,transparent);min-height:148px;}
.stock-quad-label{color:var(--quad-color);font-size:.72rem;text-transform:uppercase;font-weight:900;margin-bottom:.45rem;letter-spacing:.04em;}
.stock-quad-action{color:rgba(148,163,184,.96);font-size:.78rem;font-weight:750;margin-bottom:.55rem;}
.stock-quad-value{color:rgba(226,232,240,.98);font-size:1.18rem;font-weight:900;margin-bottom:.2rem;}
.stock-quad-sub{color:rgba(148,163,184,.9);font-size:.76rem;font-weight:680;line-height:1.35;}
.stock-ranking-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin-bottom:.8rem;}
@media(max-width:900px){.stock-quad-grid{grid-template-columns:1fr;}.stock-ranking-grid{grid-template-columns:1fr;}}
</style>
""", unsafe_allow_html=True)

    # Preparar dados enriquecidos usados pelos novos blocos
    _receita_total = float(filtered_sales["receita"].sum()) if not filtered_sales.empty else 0.0
    _quad_df = build_decision_quadrants(stock, matrix, filtered_sales)
    _daily_df = build_stock_sales_daily(filtered_sales, stock)
    _capital_enriched = build_capital_parado_enriched(stock, filtered_sales, selected_period)

    # ── BLOCO 0: PAINEL DE DECISÃO (topo da aba) ───────────────────────
    render_stock_section_title("Painel de Decisao — Onde Agir Agora")

    _quad_defs = [
        ("INVESTIR",  "#0F766E", "Cresce + tem estoque",    "Proteger disponibilidade e ampliar Ads"),
        ("COMPRAR",   "#2563EB", "Cresce + sem estoque",    "Compra urgente — risco de ruptura iminente"),
        ("LIQUIDAR",  "#DC2626", "Não cresce + tem estoque","Promoção, desconto ou pausa do anúncio"),
        ("IGNORAR",   "#64748B", "Não cresce + sem estoque","Baixa prioridade — não repor"),
    ]
    if not _quad_df.empty:
        _quad_html_parts = []
        for _qname, _qcolor, _qcrit, _qacao in _quad_defs:
            _qd = _quad_df[_quad_df["quadrante"] == _qname]
            _qn = len(_qd)
            _qr = float(_qd["_receita"].sum())
            _qc = float(_qd["_capital"].sum())
            _qpct = _qr / _receita_total * 100 if _receita_total > 0 else 0.0
            _quad_html_parts.append(
                f'<div class="stock-quad-card" style="--quad-color:{_qcolor};">'
                f'<div class="stock-quad-label">{html.escape(_qname)}'
                f'{stock_help_icon(_qcrit)}</div>'
                f'<div class="stock-quad-action">{html.escape(_qacao)}</div>'
                f'<div class="stock-quad-value">{br_number(_qn, 0)} SKU(s)</div>'
                f'<div class="stock-quad-sub">'
                f'Receita: {html.escape(br_money(_qr))} ({html.escape(br_percent(_qpct, 1))})<br>'
                f'Capital imobilizado: {html.escape(br_money(_qc))}'
                f'</div></div>'
            )
        st.markdown(f'<div class="stock-quad-grid">{"".join(_quad_html_parts)}</div>', unsafe_allow_html=True)

        # Tabela de detalhes dos quadrantes
        with st.expander("Detalhe dos produtos por quadrante", expanded=False):
            _tbl_quad = _quad_df.copy()
            _tbl_quad = _tbl_quad.rename(columns={
                "produto_final": "Produto", "marca_final": "Marca",
                "quadrante": "Quadrante", "_crescimento_marca": "Cresc. Marca %",
                "cobertura_dias": "Cobertura (dias)", "estoque_atual": "Estoque",
                "_receita": "Receita período", "_capital": "Capital parado",
            })
            _tbl_quad["Receita período"] = _tbl_quad["Receita período"].map(br_money)
            _tbl_quad["Capital parado"] = _tbl_quad["Capital parado"].map(br_money)
            _tbl_quad["Cresc. Marca %"] = _tbl_quad["Cresc. Marca %"].map(br_percent)
            _tbl_quad["Cobertura (dias)"] = _tbl_quad["Cobertura (dias)"].map(lambda v: br_number(min(v, 999), 0))
            _tbl_quad["Estoque"] = _tbl_quad["Estoque"].map(lambda v: br_number(v, 0))

            def _style_quad(row: pd.Series) -> list[str]:
                _qcolors = {"INVESTIR":"rgba(15,118,110,.18)", "COMPRAR":"rgba(37,99,235,.18)",
                            "LIQUIDAR":"rgba(220,38,38,.16)", "IGNORAR":"rgba(100,116,139,.14)"}
                c = _qcolors.get(str(row.get("Quadrante","")), "")
                return [f"background:{c};font-weight:700;" if c else ""] * len(row)

            st.dataframe(
                _tbl_quad[["Produto","Marca","Quadrante","Cresc. Marca %","Cobertura (dias)","Estoque","Receita período","Capital parado"]]
                .style.apply(_style_quad, axis=1),
                use_container_width=True, hide_index=True, height=440,
            )
    else:
        st.info("Sem dados de estoque suficientes para classificar quadrantes.")

    # ── BLOCO 1: GRÁFICO ESTOQUE vs VENDAS ─────────────────────────────
    render_stock_section_title("Estoque vs Vendas — Tendencia Operacional")

    if not _daily_df.empty:
        _estoque_snap = float(_daily_df["estoque_snap"].iloc[0]) if not _daily_df.empty else 0.0
        _venda_max = float(_daily_df["vendas_dia"].max())
        _cobertura_real = _estoque_snap / float(_daily_df["mm7_vendas"].mean()) if float(_daily_df["mm7_vendas"].mean()) > 0 else 0

        # Cards de contexto
        _sv_c1, _sv_c2, _sv_c3, _sv_c4 = st.columns(4)
        _sv_c1.metric("Estoque atual (total)", br_number(_estoque_snap, 0),
                      help="Soma de todos os estoques atuais no filtro selecionado")
        _sv_c2.metric("Vendas MM7 (unid/dia)", br_number(float(_daily_df["mm7_vendas"].iloc[-1]), 1),
                      help="Média de unidades vendidas por dia nos últimos 7 dias")
        _sv_c3.metric("Vendas MM30 (unid/dia)", br_number(float(_daily_df["mm30_vendas"].iloc[-1]), 1),
                      help="Média de unidades vendidas por dia nos últimos 30 dias")
        _sv_c4.metric("Cobertura estimada", f"{br_number(min(_cobertura_real, 999), 1)} dias",
                      help="Estoque atual / MM7 de vendas — dias estimados até ruptura no ritmo atual")

        # Gráfico
        _fig_sv = go.Figure()
        _fig_sv.add_trace(go.Bar(
            x=_daily_df["_data_ts"], y=_daily_df["vendas_dia"],
            name="Vendas diárias (unid.)",
            marker_color="rgba(37,99,235,0.35)",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Vendas: %{y:.0f} unid.<extra></extra>",
        ))
        _fig_sv.add_trace(go.Scatter(
            x=_daily_df["_data_ts"], y=_daily_df["mm7_vendas"],
            mode="lines", name="MM7 vendas",
            line=dict(color="#0891B2", width=2.5),
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>MM7: %{y:.1f}<extra></extra>",
        ))
        _fig_sv.add_trace(go.Scatter(
            x=_daily_df["_data_ts"], y=_daily_df["mm30_vendas"],
            mode="lines", name="MM30 vendas",
            line=dict(color="#D97706", width=2, dash="dot"),
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>MM30: %{y:.1f}<extra></extra>",
        ))
        # Linha do estoque como referência de escala (eixo secundário)
        if _estoque_snap > 0 and _venda_max > 0:
            _fig_sv.add_hline(
                y=_venda_max,
                line_dash="dash", line_color="rgba(148,163,184,.3)",
                annotation_text=f"Pico de vendas: {br_number(_venda_max, 0)} unid.",
                annotation_position="bottom right",
                annotation_font=dict(size=10, color="rgba(148,163,184,.75)"),
            )
        _fig_sv.update_layout(
            title="Volume de Vendas Diárias vs Médias Móveis",
            xaxis_title="Data", yaxis_title="Unidades",
            height=400,
            margin=dict(l=0, r=0, t=44, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(226,232,240,.92)"),
            xaxis=dict(gridcolor="rgba(148,163,184,.10)"),
            yaxis=dict(gridcolor="rgba(148,163,184,.10)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        _fig_sv.add_annotation(
            text="Barras: vendas diárias | Azul: MM7 | Laranja pontilhado: MM30",
            xref="paper", yref="paper", x=0, y=-0.10, showarrow=False,
            font=dict(size=10, color="rgba(148,163,184,.75)"), align="left",
        )
        st.plotly_chart(_fig_sv, use_container_width=True)

        # Insight de tendência
        _mm7_last = float(_daily_df["mm7_vendas"].iloc[-1])
        _mm30_last = float(_daily_df["mm30_vendas"].iloc[-1])
        if _mm30_last > 0:
            _ratio_sv = _mm7_last / _mm30_last
            if _ratio_sv >= 1.10:
                st.success(f"✅ **Vendas em aceleração** — MM7 ({br_number(_mm7_last,1)}) está {br_percent((_ratio_sv-1)*100)} acima da MM30 ({br_number(_mm30_last,1)}). Monitorar ruptura.")
            elif _ratio_sv <= 0.90:
                st.warning(f"⚠️ **Vendas desacelerando** — MM7 ({br_number(_mm7_last,1)}) está {br_percent((1-_ratio_sv)*100)} abaixo da MM30 ({br_number(_mm30_last,1)}). Avaliar ação comercial.")
    else:
        st.info("Sem dados de vendas diárias para o período selecionado.")

    # ── BLOCO 2: RANKINGS EXECUTIVOS ────────────────────────────────────
    render_stock_section_title("Rankings Executivos de Produtos")

    if not stock.empty:
        _r_col1, _r_col2, _r_col3 = st.columns(3)

        # Ranking 1 — Top por venda no período
        with _r_col1:
            st.markdown('<div class="mini-title">Top 10 por Venda</div>', unsafe_allow_html=True)
            _rank_venda = stock.nlargest(10, "quantidade_periodo")[
                ["produto_final","marca_final","quantidade_periodo","receita","margem_liquida_estimada"]
            ].copy()
            _receita_soma_total = float(stock["receita"].sum()) if float(stock["receita"].sum()) > 0 else 1
            _rank_venda["% Receita"] = (_rank_venda["receita"] / _receita_soma_total * 100).map(br_percent)
            _rank_venda["receita"] = _rank_venda["receita"].map(br_money)
            _rank_venda["quantidade_periodo"] = _rank_venda["quantidade_periodo"].map(lambda v: br_number(v,0))
            _rank_venda["Ação"] = "📈 Manter"
            _rank_venda = _rank_venda.rename(columns={
                "produto_final":"Produto","marca_final":"Marca",
                "quantidade_periodo":"Unidades","receita":"Receita",
                "margem_liquida_estimada":"Margem",
            })
            if "Margem" in _rank_venda.columns:
                _rank_venda["Margem"] = pd.to_numeric(_rank_venda["Margem"], errors="coerce").map(
                    lambda v: br_percent(v) if pd.notna(v) else "N/D"
                )
            st.dataframe(
                _rank_venda[["Produto","Marca","Unidades","Receita","% Receita","Ação"]],
                use_container_width=True, hide_index=True, height=340,
            )

        # Ranking 2 — Top capital parado
        with _r_col2:
            st.markdown('<div class="mini-title">Top 10 Capital Parado</div>', unsafe_allow_html=True)
            _rank_cap = stock[stock["estoque_atual"].fillna(0) > 0].nlargest(10, "capital_parado")[
                ["produto_final","marca_final","capital_parado","dias_sem_venda","estoque_atual"]
            ].copy()
            _cap_total = float(stock["capital_parado"].sum()) if float(stock["capital_parado"].sum()) > 0 else 1
            _rank_cap["% Capital"] = (_rank_cap["capital_parado"] / _cap_total * 100).map(br_percent)
            _rank_cap["capital_parado"] = _rank_cap["capital_parado"].map(br_money)
            _rank_cap["estoque_atual"] = _rank_cap["estoque_atual"].map(lambda v: br_number(v,0))
            _rank_cap["dias_sem_venda"] = _rank_cap["dias_sem_venda"].map(lambda v: br_number(min(v,999),0))
            _rank_cap["Ação"] = _rank_cap["dias_sem_venda"].map(
                lambda v: "🔴 Liquidar" if int(str(v).replace(",","").replace(".","")) > 30 else "🟡 Promoção"
            )
            _rank_cap = _rank_cap.rename(columns={
                "produto_final":"Produto","marca_final":"Marca",
                "capital_parado":"Capital","dias_sem_venda":"Dias s/ venda","estoque_atual":"Estoque",
            })
            st.dataframe(
                _rank_cap[["Produto","Marca","Capital","% Capital","Dias s/ venda","Estoque","Ação"]],
                use_container_width=True, hide_index=True, height=340,
            )

        # Ranking 3 — Top oportunidades (crescimento alto + estoque baixo)
        with _r_col3:
            st.markdown('<div class="mini-title">Top 10 Oportunidades</div>', unsafe_allow_html=True)
            if not _quad_df.empty:
                _rank_opp = _quad_df[_quad_df["quadrante"] == "COMPRAR"].nlargest(10, "_receita")[[
                    "produto_final","marca_final","_crescimento_marca","cobertura_dias","_receita",
                ]].copy()
                if not _rank_opp.empty:
                    _rank_opp["_crescimento_marca"] = _rank_opp["_crescimento_marca"].map(br_percent)
                    _rank_opp["cobertura_dias"] = _rank_opp["cobertura_dias"].map(lambda v: f"{br_number(min(v,999),0)} dias")
                    _rank_opp["_receita"] = _rank_opp["_receita"].map(br_money)
                    _rank_opp["Ação"] = "🔵 Comprar"
                    _rank_opp = _rank_opp.rename(columns={
                        "produto_final":"Produto","marca_final":"Marca",
                        "_crescimento_marca":"Cresc.","cobertura_dias":"Cobertura",
                        "_receita":"Receita",
                    })
                    st.dataframe(
                        _rank_opp[["Produto","Marca","Cresc.","Cobertura","Receita","Ação"]],
                        use_container_width=True, hide_index=True, height=340,
                    )
                else:
                    st.info("Nenhum produto no quadrante COMPRAR para o período.")
            else:
                st.info("Sem dados de quadrante disponíveis.")
    else:
        st.info("Sem dados de estoque para os rankings.")

    # ── CAPITAL PARADO ENRIQUECIDO ──────────────────────────────────────
    render_stock_section_title("Capital Parado — Impacto Financeiro")

    if not _capital_enriched.empty:
        _cap_tot = float(_capital_enriched["capital_parado"].sum())
        _cap_pct_fat = _cap_tot / _receita_total * 100 if _receita_total > 0 else 0.0
        _cap_acima_30 = int((_capital_enriched["dias_giro_est"].fillna(999) > 30).sum())

        _cap_c1, _cap_c2, _cap_c3, _cap_c4 = st.columns(4)
        _cap_c1.metric("Capital total parado", br_money(_cap_tot),
                       help="Estoque atual × valor unitário estimado (CMV ou preço)")
        _cap_c2.metric("% do faturamento", br_percent(_cap_pct_fat),
                       help="Capital imobilizado em relação à receita do período filtrado")
        _cap_c3.metric("Giro > 30 dias", br_number(_cap_acima_30, 0),
                       help="Produtos com dias estimados de giro acima de 30 dias")
        _cap_c4.metric("Produtos no ranking", br_number(len(_capital_enriched), 0),
                       help="Número de produtos com capital > 0 no top 20")

        # Gráfico atualizado com % do faturamento
        _fig_cap = go.Figure(go.Bar(
            x=_capital_enriched["capital_parado"],
            y=_capital_enriched["produto_final"].map(short_product_label),
            orientation="h",
            marker=dict(
                color=_capital_enriched["dias_giro_est"].clip(0, 365),
                colorscale=[[0,"#0F766E"],[0.3,"#D97706"],[1,"#DC2626"]],
                showscale=True,
                colorbar=dict(title="Dias giro est.", len=0.6, thickness=12),
            ),
            customdata=_capital_enriched[[
                "produto_final","marca_final","capital_parado","dias_giro_est",
                "estoque_atual","capital_pct_fat",
            ]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Marca: %{customdata[1]}<br>"
                "Capital parado: R$ %{x:,.2f}<br>"
                "% Faturamento: %{customdata[5]:.2f}%<br>"
                "Dias giro est.: %{customdata[3]:.0f}<br>"
                "Estoque: %{customdata[4]:.0f} unid.<extra></extra>"
            ),
        ))
        _fig_cap.update_yaxes(autorange="reversed")
        _fig_cap.update_layout(
            title="Capital Parado por Produto (cor = dias estimados de giro)",
            xaxis_title="Capital parado (R$)", yaxis_title="",
            height=460,
            margin=dict(l=0, r=80, t=44, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(226,232,240,.92)"),
            xaxis=dict(gridcolor="rgba(148,163,184,.10)"),
        )
        st.plotly_chart(_fig_cap, use_container_width=True)
        st.caption("Verde = giro rápido (< 30 dias) | Amarelo = moderado | Vermelho = lento (> 90 dias)")
    else:
        st.info("Sem produtos com capital parado para o período selecionado.")

    # ── ALERTAS EXECUTIVOS INTELIGENTES ────────────────────────────────
    render_stock_section_title("Alertas Executivos Inteligentes")
    severity_colors = {"Alta": "#DC2626", "Media": "#D97706", "Oportunidade": "#0F766E", "Saudavel": "#0F766E"}
    _smart_alerts = build_intelligent_stock_alerts(
        stock, matrix, monthly, kpis, capital_parado_total, _receita_total
    )
    _alert_html = "".join(
        f'<div class="stock-alert-card" style="--alert-color:{severity_colors.get(a["criticidade"], "#64748B")};">'
        f'<div class="stock-alert-severity">{html.escape(a["criticidade"])}</div>'
        f'<div class="stock-alert-title">{html.escape(a["titulo"])}</div>'
        f'<div class="stock-alert-detail">{html.escape(a["detalhe"])}</div>'
        "</div>"
        for a in _smart_alerts
    )
    st.markdown(f'<div class="stock-alert-grid">{_alert_html}</div>', unsafe_allow_html=True)
    score_components_html = "".join(
        f'<div class="stock-score-component"><div class="stock-score-component-label">{html.escape(label)}</div>'
        f'<div class="stock-score-component-value">{br_number(float(value), 0)}/100</div></div>'
        for label, value in dict(score_info["components"]).items()
    )
    score_left, score_right = st.columns([0.9, 1.25])
    with score_left:
        st.plotly_chart(stock_health_gauge(score_info), use_container_width=True)
        st.markdown(
            f'<div class="stock-score-status" style="--score-color:{score_info["color"]};">'
            f'Score Estoque: {br_number(float(score_info["score"]), 0)}/100 - {html.escape(str(score_info["status"]))}</div>',
            unsafe_allow_html=True,
        )
    with score_right:
        st.markdown(
            f'<div class="stock-score-panel"><div class="stock-score-title">Composicao do Score'
            f'{stock_help_icon(STOCK_KPI_TOOLTIPS["Score Saude do Estoque"])}</div>'
            f'<div class="stock-score-components">{score_components_html}</div>'
            f'<div class="stock-score-rationale">{html.escape(str(score_info["rationale"]))}</div></div>',
            unsafe_allow_html=True,
        )

    render_stock_section_title("Resumo Executivo")
    summary_cards = [
        render_stock_kpi_card("Estoque Total", br_number(kpis["estoque_total"]), "#2563EB", "Unidades disponiveis", "Monitoramento"),
        render_stock_kpi_card("Produtos sem estoque", br_number(kpis["sem_estoque"]), "#DC2626", "Risco de ruptura", "Meta zero"),
        render_stock_kpi_card("Estoque baixo", br_number(kpis["baixo"]), "#D97706", "Risco de ruptura futura", "Priorizar giro alto"),
        render_stock_kpi_card("Produtos parados", br_number(stopped_products), "#64748B", "Estoque com baixo giro", "Reduzir capital preso"),
        render_stock_kpi_card("Capital parado", br_money(capital_parado_total), "#7C3AED", "Estoque x valor unitario estimado", "Ranking abaixo"),
        render_stock_kpi_card("Cobertura media", f"{br_number(cobertura_media, 1)} dias", "#0F766E", "Estoque / venda media diaria", "Meta 30 a 75 dias"),
        render_stock_kpi_card("Alertas criticos", br_number(critical_alerts), "#DC2626", f"{br_number(due_today)} acoes para hoje", "Meta zero"),
    ]
    st.markdown(f'<div class="stock-kpi-grid">{"".join(summary_cards)}</div>', unsafe_allow_html=True)

    render_stock_section_title("Crescimento por Marca")
    insights = stock_growth_insights(monthly)
    insight_html = "".join(
        f'<div class="stock-alert-card" style="--alert-color:#0F766E;" '
        f'title="{html.escape("Formula: leitura automatica de crescimento mensal, participacao e concentracao de faturamento. Meta: crescimento verde >= 18% e amarelo >= 15%. Interpretacao: prioriza desvios relevantes. Acao recomendada: usar o heatmap e rankings abaixo para decisao.", quote=True)}">'
        f'<div class="stock-alert-severity">Insight</div>'
        f'<div class="stock-alert-title">{html.escape(text)}</div>'
        f'</div>'
        for text in insights
    )
    st.markdown(f'<div class="stock-alert-grid">{insight_html}</div>', unsafe_allow_html=True)
    st.plotly_chart(brand_growth_heatmap(monthly), use_container_width=True)
    top_growth, top_drop, starting_brands = brand_growth_rankings(monthly)
    rank_growth_col, rank_drop_col, rank_start_col = st.columns(3)
    with rank_growth_col:
        st.markdown(
            '<div class="mini-title" title="Formula: crescimento = receita atual / receita anterior - 1. '
            'Meta: verde >= 18%. Interpretacao: marcas com maior aceleracao. Acao recomendada: avaliar compra e cobertura.">'
            "Top crescimento</div>",
            unsafe_allow_html=True,
        )
        table = format_brand_growth_table(top_growth)
        if table.empty:
            st.info("Sem marcas com comparacao valida.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True, height=225)
    with rank_drop_col:
        st.markdown(
            '<div class="mini-title" title="Formula: crescimento = receita atual / receita anterior - 1. '
            'Meta: evitar queda ou crescimento abaixo de 15%. Interpretacao: marcas em perda de ritmo. Acao recomendada: revisar demanda, ruptura e preco.">'
            "Top queda</div>",
            unsafe_allow_html=True,
        )
        table = format_brand_growth_table(top_drop)
        if table.empty:
            st.info("Sem marcas com queda comparavel.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True, height=225)
    with rank_start_col:
        st.markdown(
            '<div class="mini-title" title="Formula: receita atual > 0 e receita anterior = 0. '
            'Meta: acompanhar recorrencia. Interpretacao: marcas iniciando venda sem base comparavel. Acao recomendada: monitorar antes de projetar compra.">'
            "Marcas iniciando</div>",
            unsafe_allow_html=True,
        )
        table = format_brand_growth_table(starting_brands, "starting")
        if table.empty:
            st.info("Sem marcas iniciando no mes mais recente.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True, height=225)
    with st.expander("Ver heatmap completo", expanded=False):
        st.plotly_chart(
            brand_growth_heatmap(monthly, top_n=None, title="Crescimento mensal por marca - completo"),
            use_container_width=True,
        )

    render_stock_section_title("Participacao Mensal no Faturamento por Marca")
    share_col, trend_col = st.columns([0.95, 1.2])
    with share_col:
        st.plotly_chart(brand_participation_chart(monthly), use_container_width=True)
    with trend_col:
        st.plotly_chart(brand_participation_trend_chart(monthly), use_container_width=True)

    render_stock_section_title("Matriz Estrategica de Compras")
    st.plotly_chart(purchase_matrix_chart(matrix), use_container_width=True)

    render_stock_section_title("Ranking de Marcas")
    latest = latest_brand_growth(monthly)
    col_growth, col_drop = st.columns(2)
    if latest.empty:
        col_growth.plotly_chart(empty_fig("Top crescimento"), use_container_width=True)
        col_drop.plotly_chart(empty_fig("Top queda"), use_container_width=True)
    else:
        latest_display = latest.copy()
        latest_display["crescimento_fmt"] = latest_display["crescimento"].map(lambda value: "N/D" if pd.isna(value) else br_percent(value))
        latest_display["variacao_participacao_fmt"] = latest_display["variacao_participacao"].map(
            lambda value: "N/D" if pd.isna(value) else br_pp(value)
        )
        top_growth = latest_display.dropna(subset=["crescimento"]).sort_values("crescimento", ascending=False).head(8)
        top_drop = latest_display.dropna(subset=["crescimento"]).sort_values("crescimento", ascending=True).head(8)
        col_growth.plotly_chart(
            bar_chart(top_growth.sort_values("crescimento"), "crescimento", "Marca", "Top crescimento", "h"),
            use_container_width=True,
        )
        col_drop.plotly_chart(
            bar_chart(top_drop.sort_values("crescimento"), "crescimento", "Marca", "Top queda", "h"),
            use_container_width=True,
        )

    with st.expander("Detalhes de capital parado", expanded=False):
        if capital_ranking.empty:
            st.info("Sem produtos com capital parado nos filtros atuais.")
        else:
            detail = capital_ranking[
                [
                    "produto_final",
                    "marca_final",
                    "estoque_atual",
                    "dias_sem_venda",
                    "valor_unitario_estimado",
                    "capital_parado",
                    "Link_final",
                ]
            ].rename(
                columns={
                    "produto_final": "Produto",
                    "marca_final": "Marca",
                    "estoque_atual": "Estoque",
                    "dias_sem_venda": "Dias sem venda",
                    "valor_unitario_estimado": "Valor unitario estimado",
                    "capital_parado": "Valor estimado parado",
                    "Link_final": "LinkAnuncio",
                }
            )
            st.dataframe(detail, use_container_width=True, hide_index=True, height=360)

    with st.expander("Detalhes da matriz estrategica", expanded=False):
        if matrix.empty:
            st.info("Sem matriz estrategica para os filtros atuais.")
        else:
            view = matrix[
                [
                    "Marca",
                    "classificacao",
                    "crescimento",
                    "cobertura_dias",
                    "estoque_total",
                    "capital_parado",
                    "acao_recomendada",
                ]
            ].rename(
                columns={
                    "classificacao": "Classificacao",
                    "crescimento": "Crescimento",
                    "cobertura_dias": "Cobertura dias",
                    "estoque_total": "Estoque total",
                    "capital_parado": "Capital parado",
                    "acao_recomendada": "Acao recomendada",
                }
            )
            st.dataframe(view, use_container_width=True, hide_index=True, height=360)

    with st.expander("Detalhes mensais por marca", expanded=False):
        matrices = commercial_monthly_matrices(filtered_sales)
        if not matrices:
            st.info("Sem dados mensais por marca para os filtros atuais.")
        else:
            if not monthly.empty:
                monthly_detail = monthly[
                    [
                        "Marca",
                        "mes_label",
                        "faturamento",
                        "receita_anterior",
                        "crescimento",
                        "crescimento_display",
                        "status_crescimento",
                        "participacao",
                        "variacao_participacao",
                    ]
                ].rename(
                    columns={
                        "mes_label": "Mes",
                        "faturamento": "Receita atual",
                        "receita_anterior": "Receita anterior",
                        "crescimento": "Crescimento numerico",
                        "crescimento_display": "Crescimento",
                        "status_crescimento": "Status",
                        "participacao": "Participacao",
                        "variacao_participacao": "Variacao participacao pp",
                    }
                )
                st.download_button(
                    "Baixar tabela mensal completa CSV",
                    monthly_detail.to_csv(index=False).encode("utf-8"),
                    file_name="tabela_mensal_completa_marca_estoque.csv",
                    mime="text/csv",
                )
                monthly_display = monthly_detail.copy()
                monthly_display["Receita atual"] = monthly_display["Receita atual"].map(br_money)
                monthly_display["Receita anterior"] = monthly_display["Receita anterior"].map(br_money)
                monthly_display["Crescimento numerico"] = monthly_display["Crescimento numerico"].map(
                    lambda value: "N/D" if pd.isna(value) else signed_br_percent(value)
                )
                monthly_display["Participacao"] = monthly_display["Participacao"].map(br_percent)
                monthly_display["Variacao participacao pp"] = monthly_display["Variacao participacao pp"].map(
                    lambda value: "N/D" if pd.isna(value) else br_pp(value)
                )
                st.dataframe(monthly_display, use_container_width=True, hide_index=True, height=360)
            growth_display, growth_values = matrices["growth"]
            participation_display, participation_values = matrices["participation"]
            render_commercial_matrix(
                "Crescimento de venda por marca",
                "Detalhe operacional da planilha mensal usada no heatmap executivo.",
                growth_display,
                growth_values,
                color_growth_cell,
                "crescimento_venda_marca_estoque.csv",
            )
            render_commercial_matrix(
                "Participacao mensal sobre o faturamento",
                "Detalhe operacional da participacao mensal usada no grafico executivo.",
                participation_display,
                participation_values,
                color_participation_cell,
                "participacao_mensal_marca_estoque.csv",
            )

    with st.expander("Detalhes operacionais legados", expanded=False):
        if not stock.empty:
            col1, col2 = st.columns(2)
            full_flex = stock.groupby(["FULL_final", "Flex_final"], as_index=False).size().rename(columns={"size": "anuncios"})
            col1.plotly_chart(
                bar_chart(full_flex, "anuncios", "FULL_final", "FULL/Flex por anuncios", "h", color="Flex_final"),
                use_container_width=True,
            )
            status_dist = stock.groupby("Status_final", as_index=False).size().rename(columns={"size": "anuncios"})
            col2.plotly_chart(
                bar_chart(status_dist.sort_values("anuncios"), "anuncios", "Status_final", "Status de anuncio", "h"),
                use_container_width=True,
            )
        render_estoque_giro(filtered_sales, inventory_df, filter_state, selected_period)

    with st.expander("Produtos sem cadastro/sem CMV", expanded=False):
        registration_cols = [
            "prioridade",
            "tipo_alerta",
            "MLB",
            "SKU",
            "produto",
            "marca",
            "categoria",
            "receita",
            "margem",
            "LinkAnuncio",
        ]
        if registration_alerts.empty:
            st.info("Nenhum alerta de cadastro ou CMV para os filtros atuais.")
        else:
            st.dataframe(
                style_executive_alerts(registration_alerts[registration_cols]),
                use_container_width=True,
                hide_index=True,
                height=320,
            )

    with st.expander("Plano de acao operacional", expanded=False):
        render_plano_acao(operational_alerts)


def ads_conversion_by_campaign(ads_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega conversao, cliques, unidades e receita por campanha."""
    if ads_df.empty:
        return pd.DataFrame()
    agg = (
        ads_df.groupby("campaign_name", as_index=False)
        .agg(
            cliques=("clicks", "sum"),
            unidades=("units", "sum"),
            receita=("revenue", "sum"),
            impressoes=("impressions", "sum"),
            custo=("cost", "sum"),
        )
        .sort_values("receita", ascending=False)
    )
    agg["conversao_pct"] = (agg["unidades"] / agg["cliques"].replace(0, pd.NA) * 100).fillna(0)
    agg["ctr_pct"] = (agg["cliques"] / agg["impressoes"].replace(0, pd.NA) * 100).fillna(0)
    agg["custo_por_conversao"] = (agg["custo"] / agg["unidades"].replace(0, pd.NA)).fillna(0)
    return agg.sort_values("receita", ascending=False)


def ads_clicks_trend(ads_df: pd.DataFrame) -> pd.DataFrame:
    """Prepara serie diaria de cliques com medias moveis 7d e 30d."""
    if ads_df.empty or "ads_data_ref" not in ads_df.columns or not ads_df["ads_data_ref"].notna().any():
        return pd.DataFrame()
    daily = (
        ads_df.dropna(subset=["ads_data_ref"])
        .groupby("ads_data_ref", as_index=False)
        .agg(
            cliques=("clicks", "sum"),
            impressoes=("impressions", "sum"),
            unidades=("units", "sum"),
        )
        .sort_values("ads_data_ref")
        .reset_index(drop=True)
    )
    daily["mm7"] = daily["cliques"].rolling(7, min_periods=1).mean().round(1)
    daily["mm30"] = daily["cliques"].rolling(30, min_periods=1).mean().round(1)
    return daily


def ads_trend_insight(trend_df: pd.DataFrame) -> tuple[str, str]:
    """Gera insight automatico comparando MM7 vs MM30. Retorna (status, cor)."""
    if trend_df.empty or len(trend_df) < 3:
        return "Dados insuficientes para tendência", "#64748B"
    mm7_last = float(trend_df["mm7"].iloc[-1])
    mm30_last = float(trend_df["mm30"].iloc[-1])
    if mm30_last == 0:
        return "Dados insuficientes para tendência", "#64748B"
    ratio = mm7_last / mm30_last
    if ratio >= 1.10:
        return "Tráfego em alta — MM7 acima da MM30", "#0F766E"
    if ratio <= 0.90:
        return "Tráfego em queda — MM7 abaixo da MM30", "#DC2626"
    return "Tráfego estável — MM7 próxima da MM30", "#D97706"


def ads_conversion_trend(ads_df: pd.DataFrame) -> pd.DataFrame:
    """Prepara série diária de conversão (units/clicks) com MM7 e MM30.

    Conversão = 0 quando clicks == 0 (sem divisão por zero).
    Retorna DataFrame com colunas: ads_data_ref, conversao_pct, mm7_conv, mm30_conv.
    """
    if ads_df.empty or "ads_data_ref" not in ads_df.columns or not ads_df["ads_data_ref"].notna().any():
        return pd.DataFrame()
    daily = (
        ads_df.dropna(subset=["ads_data_ref"])
        .groupby("ads_data_ref", as_index=False)
        .agg(
            clicks=("clicks", "sum"),
            units=("units", "sum"),
        )
        .sort_values("ads_data_ref")
        .reset_index(drop=True)
    )
    # Conversão segura: 0 quando sem cliques, clip para evitar outliers extremos
    daily["conversao_pct"] = (
        daily["units"] / daily["clicks"].replace(0, pd.NA) * 100
    ).fillna(0).clip(lower=0, upper=100).round(2)
    daily["mm7_conv"] = daily["conversao_pct"].rolling(7, min_periods=1).mean().round(2)
    daily["mm30_conv"] = daily["conversao_pct"].rolling(30, min_periods=1).mean().round(2)
    return daily


def ads_conversion_trend_insight(conv_df: pd.DataFrame) -> tuple[str, str]:
    """Gera insight automático de conversão comparando MM7 vs MM30."""
    if conv_df.empty or len(conv_df) < 3:
        return "Dados insuficientes para tendência de conversão", "#64748B"
    mm7 = float(conv_df["mm7_conv"].iloc[-1])
    mm30 = float(conv_df["mm30_conv"].iloc[-1])
    if mm30 == 0:
        return "Dados insuficientes para tendência de conversão", "#64748B"
    ratio = mm7 / mm30
    if ratio >= 1.10:
        return "Conversão em alta — MM7 acima da MM30", "#0F766E"
    if ratio <= 0.90:
        return "Conversão em queda — MM7 abaixo da MM30", "#DC2626"
    return "Conversão estável — MM7 próxima da MM30", "#D97706"


def build_ml_adjusted_conversion(
    ads_df: pd.DataFrame,
    financial_df: pd.DataFrame,
    conversao_ml_referencia: float = 0.0,
) -> pd.DataFrame:
    """Constrói série diária da Conversão ML Ajustada.

    Definições:
      conversao_ads (dia)   = units_ads / clicks_ads        (dados reais)
      fator_ajuste          = conversao_ml_ref - mean(conversao_ads) do período
                              (calibrado com o valor real exibido pelo ML)
      conversao_ml (dia)    = conversao_ads + fator_ajuste   (clipeado 0-100)
      mm7_ml / mm30_ml      = médias móveis da conversão ML

    Se conversao_ml_referencia == 0: fator_ajuste = 0 (sem calibração).
    Retorna DataFrame vazio se não há sobreposição de datas.
    """
    if ads_df.empty or financial_df.empty:
        return pd.DataFrame()

    # ── Preparar Ads ──────────────────────────────────────────────────
    ads_w = ads_df.copy()
    if "ads_data_ref" in ads_w.columns:
        ads_w["_data"] = ads_w["ads_data_ref"]
    elif "data_ref" in ads_w.columns:
        ads_w["_data"] = (
            pd.to_datetime(ads_w["data_ref"], errors="coerce", utc=True)
            .dt.tz_convert(APP_TIMEZONE).dt.date
        )
    else:
        return pd.DataFrame()

    ads_w["_data"] = pd.to_datetime(ads_w["_data"], errors="coerce").dt.date
    ads_w["clicks"] = pd.to_numeric(ads_w["clicks"], errors="coerce").fillna(0)
    ads_w["units"] = pd.to_numeric(ads_w["units"], errors="coerce").fillna(0)

    daily_ads = (
        ads_w.dropna(subset=["_data"])
        .groupby("_data", as_index=False)
        .agg(clicks_ads=("clicks", "sum"), units_ads=("units", "sum"))
    )
    if daily_ads.empty or daily_ads["clicks_ads"].sum() == 0:
        return pd.DataFrame()

    # ── Conversão Ads diária ─────────────────────────────────────────
    daily_ads["conversao_ads"] = (
        daily_ads["units_ads"] / daily_ads["clicks_ads"].replace(0, pd.NA) * 100
    ).fillna(0).clip(0, 100).round(2)

    # ── Fator de ajuste (constante no período) ────────────────────────
    media_ads = float(daily_ads["conversao_ads"].mean())
    if conversao_ml_referencia > 0:
        fator_ajuste = conversao_ml_referencia - media_ads
    else:
        fator_ajuste = 0.0

    daily_ads["fator_ajuste"] = round(fator_ajuste, 4)
    daily_ads["conversao_ml"] = (
        daily_ads["conversao_ads"] + fator_ajuste
    ).clip(0, 100).round(2)

    # ── Médias móveis ─────────────────────────────────────────────────
    daily_ads = daily_ads.sort_values("_data").reset_index(drop=True)
    daily_ads["mm7_ml"]  = daily_ads["conversao_ml"].rolling(7,  min_periods=1).mean().round(2)
    daily_ads["mm30_ml"] = daily_ads["conversao_ml"].rolling(30, min_periods=1).mean().round(2)
    daily_ads["mm7_ads"] = daily_ads["conversao_ads"].rolling(7,  min_periods=1).mean().round(2)

    daily_ads["_data_ts"] = pd.to_datetime(daily_ads["_data"])
    return daily_ads


def build_sku_traffic_conversion(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    top_n: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estima visitas por SKU distribuindo cliques diários proporcionalmente às vendas.

    Retorna:
        sku_summary  — DataFrame com Top N produtos agregados (para tabela)
        sku_daily    — DataFrame diário por produto (para gráficos)

    Método:
        Para cada dia com dados de Ads:
            visitas_sku = (units_sku_dia / units_total_dia) * clicks_dia
            conversao_sku = units_sku_dia / visitas_sku  (0 se visitas == 0)
    """
    if financial_df.empty or ads_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # ---------- preparar base financeira ----------
    fin = financial_df.copy()
    if "date_created" in fin.columns and fin["date_created"].notna().any():
        fin["_data"] = (
            pd.to_datetime(fin["date_created"], errors="coerce", utc=True)
            .dt.tz_convert(APP_TIMEZONE)
            .dt.date
        )
    elif "date" in fin.columns:
        fin["_data"] = pd.to_datetime(fin["date"], errors="coerce").dt.date
    else:
        return pd.DataFrame(), pd.DataFrame()

    fin = fin.dropna(subset=["_data", "item_id"]).copy()
    fin["item_id"] = fin["item_id"].astype(str).str.strip()
    fin["quantity"] = pd.to_numeric(fin.get("quantity", 0), errors="coerce").fillna(0)
    fin["receita"] = pd.to_numeric(fin.get("receita", 0), errors="coerce").fillna(0)

    # nome curto: preferir produto, fallback item_id
    fin["_produto"] = fin.get("produto", fin["item_id"]).fillna(fin["item_id"]).astype(str)
    fin["_produto"] = fin["_produto"].map(lambda s: s[:45] + "…" if len(s) > 45 else s)

    # ---------- top N produtos por receita ----------
    top_items_df = (
        fin.groupby(["item_id", "_produto"], as_index=False)
        .agg(receita_total=("receita", "sum"), unidades_total=("quantity", "sum"))
        .sort_values("receita_total", ascending=False)
        .head(top_n)
    )
    top_ids = set(top_items_df["item_id"].tolist())

    fin_top = fin[fin["item_id"].isin(top_ids)].copy()

    # ---------- cliques diários de Ads ----------
    ads_w = ads_df.copy()
    if "ads_data_ref" in ads_w.columns:
        ads_w["_data"] = ads_w["ads_data_ref"]
    elif "data_ref" in ads_w.columns:
        ads_w["_data"] = (
            pd.to_datetime(ads_w["data_ref"], errors="coerce", utc=True)
            .dt.tz_convert(APP_TIMEZONE)
            .dt.date
        )
    else:
        return pd.DataFrame(), pd.DataFrame()

    ads_w["_data"] = pd.to_datetime(ads_w["_data"], errors="coerce").dt.date
    ads_w["clicks"] = pd.to_numeric(ads_w["clicks"], errors="coerce").fillna(0)
    daily_clicks = (
        ads_w.dropna(subset=["_data"])
        .groupby("_data", as_index=False)["clicks"]
        .sum()
        .rename(columns={"clicks": "clicks_dia"})
    )

    # ---------- vendas diárias por produto ----------
    daily_sku = (
        fin_top.groupby(["_data", "item_id", "_produto"], as_index=False)
        .agg(units_sku=("quantity", "sum"), receita_sku=("receita", "sum"))
    )
    # total de unidades vendidas por dia (todos os produtos, não apenas top)
    daily_total_units = (
        fin.groupby("_data", as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "units_total_dia"})
    )

    # ---------- join ----------
    daily = daily_sku.merge(daily_clicks, on="_data", how="left")
    daily = daily.merge(daily_total_units, on="_data", how="left")
    daily["clicks_dia"] = daily["clicks_dia"].fillna(0)
    daily["units_total_dia"] = daily["units_total_dia"].fillna(0)

    # proporcional: se não há dados de Ads naquele dia, visitas = 0
    daily["participacao"] = (
        daily["units_sku"] / daily["units_total_dia"].replace(0, pd.NA)
    ).fillna(0).clip(0, 1)
    daily["visitas_est"] = (daily["participacao"] * daily["clicks_dia"]).round(1)
    daily["conversao_pct"] = (
        daily["units_sku"] / daily["visitas_est"].replace(0, pd.NA) * 100
    ).fillna(0).clip(0, 100).round(2)

    # médias móveis por produto
    daily = daily.sort_values(["item_id", "_data"]).reset_index(drop=True)
    daily["mm7_visitas"] = (
        daily.groupby("item_id")["visitas_est"]
        .transform(lambda s: s.rolling(7, min_periods=1).mean().round(1))
    )
    daily["mm7_conv"] = (
        daily.groupby("item_id")["conversao_pct"]
        .transform(lambda s: s.rolling(7, min_periods=1).mean().round(2))
    )
    daily["mm30_conv"] = (
        daily.groupby("item_id")["conversao_pct"]
        .transform(lambda s: s.rolling(30, min_periods=1).mean().round(2))
    )

    # ---------- resumo por produto (para tabela) ----------
    avg_conv = daily.groupby("item_id")["conversao_pct"].mean()
    mm7_last = daily.groupby("item_id").last()["mm7_conv"]
    mm30_last = daily.groupby("item_id").last()["mm30_conv"]
    visitas_total = daily.groupby("item_id")["visitas_est"].sum()

    summary = top_items_df.copy()
    summary["visitas_est"] = summary["item_id"].map(visitas_total).fillna(0).round(0)
    summary["conversao_media"] = summary["item_id"].map(avg_conv).fillna(0).round(2)
    summary["mm7_conv_last"] = summary["item_id"].map(mm7_last).fillna(0)
    summary["mm30_conv_last"] = summary["item_id"].map(mm30_last).fillna(0)

    # badge de tendência
    def _tendencia(row: pd.Series) -> str:
        mm7, mm30 = row["mm7_conv_last"], row["mm30_conv_last"]
        if mm30 == 0:
            return "—"
        r = mm7 / mm30
        if r >= 1.10:
            return "↑ Crescendo"
        if r <= 0.90:
            return "↓ Caindo"
        return "→ Estável"

    # badge de conversão vs média geral
    mean_conv = float(summary["conversao_media"].mean()) if not summary.empty else 0.0

    def _badge_conv(v: float) -> str:
        if mean_conv == 0:
            return "—"
        if v >= mean_conv:
            return "🟢 Alta"
        if v >= mean_conv * 0.5:
            return "🟡 Média"
        return "🔴 Baixa"

    summary["tendencia"] = summary.apply(_tendencia, axis=1)
    summary["badge_conv"] = summary["conversao_media"].map(_badge_conv)

    return summary, daily


def render_ads_performance(
    ads_df: pd.DataFrame,
    ads_filter_info: dict[str, object] | None = None,
    selected_period: tuple[date, date] | None = None,
    financial_df: pd.DataFrame | None = None,
    all_ads_df: pd.DataFrame | None = None,
) -> None:
    """Renderiza visao executiva de publicidade e rentabilidade."""

    ads = ads_df.copy()
    financial_base = financial_df if financial_df is not None else pd.DataFrame()
    coverage = ads_temporal_coverage(ads, selected_period)
    kpis = calculate_ads_kpis_adjusted(ads, coverage)
    campaign = ads_campaign_summary(ads)
    ads_daily = ads_daily_summary(ads)
    margin_impact_pct = ads_margin_impact(kpis, financial_base)
    alerts = build_ads_alerts_executive(campaign, kpis, coverage, margin_impact_pct, ads_daily)
    score_info = ads_health_score(kpis, coverage)
    margin_contribution = ads_margin_contribution(kpis, financial_base, ads, selected_period, all_ads_df)
    radar_items = ads_opportunity_radar(kpis, coverage, campaign)

    if ads.empty:
        if ads_filter_info and ads_filter_info.get("status") not in {None, "empty"}:
            st.info("Sem dados de Ads para o periodo selecionado.")
        else:
            st.info("Base de Ads vazia ou indisponivel. Gere primeiro data/ml_ads_metrics.csv.")

    if str(coverage["status_cobertura_ads"]) == "Parcial":
        st.warning(
            "Ads parcial no periodo selecionado: "
            f"{coverage['dias_cobertos']} dias cobertos e {coverage['dias_faltantes']} dias faltantes. "
            "O investimento usa estimativa por media diaria."
        )
    elif str(coverage["status_cobertura_ads"]) == "Sem dados":
        st.warning("Sem dados reais de Ads para o periodo filtrado; valores estimados nao foram inventados.")

    coverage_detail = (
        f"{coverage['dias_cobertos']} de {coverage['dias_periodo']} dias | "
        f"Fonte: {coverage['ads_fonte']}"
    )
    roas_status, roas_color, roas_meta = ads_goal_status("ROAS", float(kpis["roas_adjusted"]))
    acos_status, acos_color, acos_meta = ads_goal_status("ACOS", float(kpis["acos_adjusted"]))
    ctr_status, ctr_color, ctr_meta = ads_goal_status("CTR", float(kpis["ctr"]))
    conv_status, conv_color, conv_meta = ads_goal_status("Conversao", float(kpis["conversion_rate"]))
    coverage_status, coverage_color, coverage_meta = ads_goal_status(
        "Cobertura dos Dados", float(coverage["cobertura_ads_percentual"])
    )
    impact_status, impact_color, impact_meta = ads_goal_status("Impacto na Margem", margin_impact_pct)
    summary_cards = [
        render_ads_kpi_card(
            "Investimento Ads",
            br_money(kpis["cost_adjusted"]),
            "#7C3AED",
            f"Real {br_money(kpis['cost_real'])}; estimado {br_money(kpis['estimated_cost'])}",
            "Monitoramento",
            "Referencia: ate 3% da receita total",
        ),
        render_ads_kpi_card(
            "Receita Atribuida",
            br_money(kpis["revenue"]),
            "#0F766E",
            "Receita atribuida pela API ML",
            "Monitoramento",
            "Crescer com ROAS saudavel",
        ),
        render_ads_kpi_card("ROAS", br_number(kpis["roas_adjusted"], 2), roas_color, "Calculado por totais", roas_status, roas_meta),
        render_ads_kpi_card("ACOS", br_percent(kpis["acos_adjusted"]), acos_color, "Calculado por totais", acos_status, acos_meta),
        render_ads_kpi_card("CTR", br_percent(kpis["ctr"]), ctr_color, "Cliques / impressoes", ctr_status, ctr_meta),
        render_ads_kpi_card("CPC", br_money(kpis["cpc_adjusted"]), "#7C3AED", "Investimento / cliques", "Monitoramento", "Sem meta fixa"),
        render_ads_kpi_card("Conversao", br_percent(kpis["conversion_rate"]), conv_color, "Conversoes / cliques", conv_status, conv_meta),
        render_ads_kpi_card(
            "Cobertura dos Dados",
            br_percent(float(coverage["cobertura_ads_percentual"]), 0),
            coverage_color,
            coverage_detail,
            coverage_status,
            coverage_meta,
        ),
        render_ads_kpi_card("Impacto na Margem", br_percent(margin_impact_pct), impact_color, "Investimento como % da receita total", impact_status, impact_meta),
    ]
    st.markdown(
        """
<style>
.ads-score-layout{display:grid;grid-template-columns:minmax(260px,.9fr) minmax(0,1.25fr);gap:.85rem;align-items:stretch;margin-bottom:1rem;}
.ads-score-panel{border:1px solid rgba(148,163,184,.18);border-radius:8px;padding:.75rem .9rem;background:rgba(15,23,42,.18);}
.ads-score-title{display:flex;align-items:center;color:rgba(226,232,240,.98);font-size:.95rem;font-weight:950;margin-bottom:.3rem;}
.ads-score-status{color:var(--score-color);font-size:1rem;font-weight:950;margin-top:-.2rem;text-align:center;}
.ads-score-components{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem;}
.ads-score-component{border:1px solid rgba(148,163,184,.16);border-radius:8px;padding:.65rem;background:rgba(2,6,23,.18);}
.ads-score-component-label{color:rgba(148,163,184,.98);font-size:.7rem;font-weight:900;text-transform:uppercase;}
.ads-score-component-value{color:rgba(226,232,240,.98);font-size:1.05rem;font-weight:950;margin-top:.22rem;}
.ads-kpi-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin-bottom:1rem;}
.ads-kpi-card{border:1px solid rgba(148,163,184,.18);border-top:4px solid var(--ads-color);border-radius:8px;padding:.9rem;background:linear-gradient(180deg,color-mix(in srgb,var(--ads-color) 9%,transparent),rgba(15,23,42,.12));min-height:142px;}
.ads-kpi-label{display:flex;align-items:center;color:rgba(148,163,184,.96);font-size:.72rem;font-weight:900;text-transform:uppercase;margin-bottom:.4rem;}
.ads-kpi-value{color:var(--ads-color);font-size:1.35rem;line-height:1.08;font-weight:950;}
.ads-kpi-detail{color:rgba(148,163,184,.98);font-size:.78rem;font-weight:720;margin-top:.45rem;line-height:1.35;}
.ads-kpi-status{color:rgba(226,232,240,.96);font-size:.72rem;font-weight:900;margin-top:.58rem;}
.ads-kpi-meta{color:rgba(148,163,184,.92);font-size:.7rem;font-weight:720;margin-top:.18rem;}
.ads-status-badge{display:inline-flex;border:1px solid color-mix(in srgb,var(--ads-status-color) 52%,transparent);background:color-mix(in srgb,var(--ads-status-color) 12%,transparent);color:var(--ads-status-color);border-radius:999px;padding:.16rem .48rem;font-size:.68rem;font-weight:900;text-transform:uppercase;}
.ads-funnel{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin-bottom:1rem;}
.ads-funnel-step{border:1px solid rgba(148,163,184,.18);border-radius:8px;padding:.82rem .9rem;background:rgba(15,23,42,.18);}
.ads-funnel-label{color:rgba(148,163,184,.96);font-size:.72rem;text-transform:uppercase;font-weight:900;}
.ads-funnel-value{color:rgba(226,232,240,.98);font-size:1.18rem;font-weight:930;margin-top:.25rem;}
.ads-opportunity-note{border:1px solid rgba(148,163,184,.18);border-radius:8px;padding:.82rem .9rem;background:rgba(15,23,42,.18);color:rgba(148,163,184,.98);font-size:.82rem;font-weight:720;margin-bottom:.7rem;}
.ads-radar-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.7rem;margin-bottom:1rem;}
.ads-radar-card{border:1px solid rgba(148,163,184,.18);border-left:4px solid var(--radar-color);border-radius:8px;padding:.82rem .9rem;background:color-mix(in srgb,var(--radar-color) 8%,transparent);min-height:104px;}
.ads-radar-level{color:var(--radar-color);font-size:.68rem;text-transform:uppercase;font-weight:900;margin-bottom:.35rem;}
.ads-radar-point{color:rgba(226,232,240,.96);font-weight:900;line-height:1.22;margin-bottom:.35rem;}
.ads-radar-detail{color:rgba(148,163,184,.98);font-size:.8rem;font-weight:680;line-height:1.35;}
.ads-alert-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.7rem;margin-bottom:1rem;}
.ads-alert-card{border:1px solid rgba(148,163,184,.18);border-left:4px solid var(--alert-color);border-radius:8px;padding:.82rem .9rem;background:color-mix(in srgb,var(--alert-color) 8%,transparent);min-height:126px;}
.ads-alert-severity{color:var(--alert-color);font-size:.68rem;text-transform:uppercase;font-weight:900;margin-bottom:.35rem;}
.ads-alert-title{color:rgba(226,232,240,.96);font-weight:900;line-height:1.22;margin-bottom:.35rem;}
.ads-alert-detail{color:rgba(148,163,184,.98);font-size:.8rem;font-weight:680;line-height:1.35;}
.ads-conv-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.7rem;margin-bottom:1rem;}
.ads-conv-card{border:1px solid rgba(148,163,184,.18);border-left:4px solid var(--conv-color);border-radius:8px;padding:.82rem .9rem;background:color-mix(in srgb,var(--conv-color) 8%,transparent);}
.ads-conv-label{color:rgba(148,163,184,.96);font-size:.72rem;font-weight:900;text-transform:uppercase;margin-bottom:.35rem;}
.ads-conv-value{color:var(--conv-color);font-size:1.35rem;font-weight:950;line-height:1.08;}
.ads-conv-detail{color:rgba(148,163,184,.98);font-size:.78rem;font-weight:720;margin-top:.45rem;line-height:1.35;}
@media(max-width:900px){.ads-score-layout,.ads-kpi-grid,.ads-funnel{grid-template-columns:1fr;}}
</style>
        """,
        unsafe_allow_html=True,
    )

    # ================================================================
    # BLOCO 1 — RESUMO EXECUTIVO: 6 CARDS ESTRATÉGICOS
    # ================================================================
    render_ads_section_title("Resumo Executivo Ads")

    # ── Input: Conversão ML real (painel ML, não calculável via API) ──
    _col_input, _col_note = st.columns([1, 2])
    with _col_input:
        _conv_ml_ref = st.number_input(
            "Conversao ML (painel ML, %)",
            min_value=0.0, max_value=100.0,
            value=st.session_state.get("_conv_ml_ref", 0.0),
            step=0.1, format="%.2f",
            key="_conv_ml_ref",
            help=(
                "Vendas totais / visitas totais da loja (organico + Ads). "
                "Fonte: painel Mercado Livre — nao e exportado pela API. "
                "Informe manualmente para ativar o Gap ML vs Ads."
            ),
        )
    with _col_note:
        if _conv_ml_ref == 0:
            st.caption(
                "ℹ️ Informe o valor do painel ML para calcular Gap ML vs Ads e trafego organico estimado."
            )
        else:
            st.caption(
                f"✅ Conversao ML calibrada em **{_conv_ml_ref:.2f}%**. "
                "Gap ML vs Ads = contribuicao estimada do trafego organico."
            )

    _conv_ads_pct = float(kpis.get("conversion_rate") or 0.0)
    _gap_ml_ads   = _conv_ml_ref - _conv_ads_pct if _conv_ml_ref > 0 else None
    _roas_val     = float(kpis.get("roas_adjusted") or 0.0)
    _cpc_val      = float(kpis.get("cpc_adjusted") or 0.0)

    # ── Alertas automáticos executivos ───────────────────────────────
    _alerts_inline = []
    if _conv_ads_pct > 0 and _conv_ml_ref > 0 and _conv_ads_pct < _conv_ml_ref * 0.50:
        _alerts_inline.append(
            f"⚠️ **Ads ineficiente** — Conv. Ads ({br_percent(_conv_ads_pct)}) "
            f"abaixo de 50% da Conv. ML ({br_percent(_conv_ml_ref)}). Revisar segmentacao e criativos."
        )
    if _roas_val > 0 and _roas_val < 3:
        _alerts_inline.append(
            f"⚠️ **ROAS baixo** ({br_number(_roas_val, 2)}x) — revisar campanhas antes de escalar investimento."
        )
    if _cpc_val > 2:
        _alerts_inline.append(
            f"⚠️ **CPC elevado** ({br_money(_cpc_val)}/clique) — custo de aquisicao acima do referencial."
        )
    if not _alerts_inline:
        _alerts_inline.append("✅ Sem alertas criticos de Ads para o periodo selecionado.")
    for _al in _alerts_inline:
        if _al.startswith("✅"):
            st.success(_al)
        else:
            st.warning(_al)

    # ── 6 Cards estratégicos ─────────────────────────────────────────
    _gap_txt  = (("+" if (_gap_ml_ads or 0) >= 0 else "") + br_percent(_gap_ml_ads)) if _gap_ml_ads is not None else "Informe Conv. ML"
    _gap_cor  = "#0F766E" if (_gap_ml_ads or 0) > 0 else "#64748B"
    _gap_sub  = "Forca do trafego organico" if (_gap_ml_ads or 0) > 0 else "Informe valor ML acima"

    summary_cards = [
        render_ads_kpi_card(
            "Conversao ML",
            br_percent(_conv_ml_ref) if _conv_ml_ref > 0 else "—",
            "#F8FAFC",
            "Vendas totais / visitas totais (organico + Ads). Fonte: painel ML — informado manualmente.",
            "Referencia loja" if _conv_ml_ref > 0 else "Nao informado",
            "Painel Mercado Livre",
        ),
        render_ads_kpi_card(
            "Conversao Ads",
            br_percent(_conv_ads_pct),
            "#2563EB",
            "Unidades atribuidas a Ads / cliques em anuncios pagos.",
            conv_status, conv_meta,
        ),
        render_ads_kpi_card(
            "Gap ML vs Ads",
            _gap_txt,
            _gap_cor,
            "Diferenca entre Conv. ML (loja total) e Conv. Ads (pago). "
            "Representa a forca do trafego organico. Quanto maior, mais a loja converte sem depender de Ads.",
            _gap_sub,
            "Conv. ML - Conv. Ads",
        ),
        render_ads_kpi_card(
            "ROAS",
            br_number(_roas_val, 2) + "x",
            roas_color,
            "Receita atribuida Ads / investimento ajustado. Meta: acima de 6.",
            roas_status, roas_meta,
        ),
        render_ads_kpi_card(
            "CPC",
            br_money(_cpc_val),
            "#7C3AED",
            "Custo medio por clique. Investimento / total de cliques.",
            "Monitoramento", "Sem meta fixa",
        ),
        render_ads_kpi_card(
            "Investimento Ads",
            br_money(kpis["cost_adjusted"]),
            "#DC2626" if margin_impact_pct > 3 else "#0F766E",
            "Total investido em campanhas. Referencia: ate 3% da receita total.",
            impact_status, impact_meta,
        ),
    ]
    st.markdown(f'<div class="ads-kpi-grid">{"".join(summary_cards)}</div>', unsafe_allow_html=True)

    # ================================================================
    # BLOCO 2 — EFICIÊNCIA DE FUNIL: ADS vs ORGÂNICO ESTIMADO
    # ================================================================
    render_ads_section_title("Eficiencia de Funil — Ads vs Organico")

    _total_clicks   = float(kpis.get("clicks") or 0.0)
    _total_impr     = float(kpis.get("impressions") or 0.0)
    _units_ads      = float(kpis.get("conversions") or 0.0)
    _revenue_ads    = float(kpis.get("revenue") or 0.0)

    # Orgânico estimado: usa Conv. ML informada para inferir visitas totais
    if _conv_ml_ref > 0 and _conv_ads_pct >= 0:
        _pedidos_totais   = float(financial_base["order_id"].nunique()) if not financial_base.empty and "order_id" in financial_base.columns else 0
        _visitas_totais   = _pedidos_totais / (_conv_ml_ref / 100) if _conv_ml_ref > 0 else 0
        _visitas_org_est  = max(_visitas_totais - _total_clicks, 0)
        _units_org_est    = max(float(financial_base["quantity"].sum() if not financial_base.empty else 0) - _units_ads, 0)
        _conv_org_est     = _units_org_est / _visitas_org_est * 100 if _visitas_org_est > 0 else 0
        _tem_organico     = True
    else:
        _visitas_totais = _visitas_org_est = _units_org_est = _conv_org_est = 0
        _tem_organico = False

    _fcol1, _fcol2 = st.columns(2)

    with _fcol1:
        st.markdown(
            '<div class="section-title" style="color:#2563EB;">🔵 Trafego Pago (Ads)</div>',
            unsafe_allow_html=True,
        )
        _ads_funnel = [
            ("Impressoes", br_number(_total_impr, 0),
             "Quantidade de vezes que o anuncio apareceu no feed."),
            ("Cliques", br_number(_total_clicks, 0),
             "Cliques em anuncios pagos — trafego gerado pelos Ads."),
            ("Conversoes Ads", br_number(_units_ads, 0),
             "Unidades vendidas atribuidas as campanhas pelo ML."),
            ("Receita Ads", br_money(_revenue_ads),
             "Receita atribuida pelo ML as campanhas ativas."),
            ("Conversao Ads", br_percent(_conv_ads_pct),
             "Unidades Ads / cliques. Meta: acima de 2,5%."),
            ("CTR", br_percent(float(kpis.get("ctr") or 0.0)),
             "Cliques / impressoes. Meta: acima de 0,25%."),
        ]
        for _lbl, _val, _tip in _ads_funnel:
            st.metric(_lbl, _val, help=_tip)

    with _fcol2:
        st.markdown(
            '<div class="section-title" style="color:#0F766E;">🟢 Trafego Organico (estimado)</div>',
            unsafe_allow_html=True,
        )
        if _tem_organico:
            st.caption(
                "Dados organicos estimados a partir da diferenca entre total ML e Ads. "
                "Requer Conversao ML informada acima."
            )
            _org_funnel = [
                ("Visitas totais ML (est.)", br_number(_visitas_totais, 0),
                 "Pedidos totais / Conv. ML informada. Estimativa de visitas da loja."),
                ("Visitas organicas (est.)", br_number(_visitas_org_est, 0),
                 "Visitas totais - cliques Ads. Estimativa de trafego organico."),
                ("Vendas organicas (est.)", br_number(_units_org_est, 0),
                 "Unidades totais - unidades Ads. Vendas nao atribuidas a campanhas."),
                ("Conversao organica (est.)", br_percent(_conv_org_est),
                 "Vendas organicas / visitas organicas estimadas."),
            ]
            for _lbl, _val, _tip in _org_funnel:
                st.metric(_lbl, _val, help=_tip)
        else:
            st.info(
                "Informe a Conversao ML acima para estimar o trafego organico. "
                "Formula: visitas_org = visitas_totais - cliques_ads."
            )

    # ================================================================
    # BLOCO 3 — QUADRANTE DE CAMPANHAS (visual de decisão)
    # ================================================================
    render_ads_section_title("Quadrante de Campanhas")
    st.plotly_chart(ads_campaign_quadrant_chart(campaign), use_container_width=True)
    st.caption(
        "ROAS > 6 e ACOS < 10% → Escalar. "
        "ROAS < 3 → Pausar ou revisar. "
        "ROAS muito acima da escala pode ser limitado visualmente; valor real no hover."
    )

    render_ads_section_title("Participacao dos Investimentos")
    st.plotly_chart(ads_budget_share_chart(campaign), use_container_width=True)

    # ================================================================
    # BLOCO 4 — ALERTAS EXECUTIVOS
    # ================================================================
    render_ads_section_title("Alertas de Ads")
    severity_colors = {"Alta": "#DC2626", "Media": "#D97706", "Oportunidade": "#0F766E", "Saudavel": "#0F766E"}
    alert_html = "".join(
        f'<div class="ads-alert-card" style="--alert-color:{severity_colors.get(alert["criticidade"], "#64748B")};">'
        f'<div class="ads-alert-severity">{html.escape(alert["criticidade"])}</div>'
        f'<div class="ads-alert-title">{html.escape(alert["alerta"])}</div>'
        f'<div class="ads-alert-detail">Impacto: {html.escape(alert["impacto"])}<br>{html.escape(alert["recomendacao"])}</div>'
        "</div>"
        for alert in alerts
    )
    st.markdown(f'<div class="ads-alert-grid">{alert_html}</div>', unsafe_allow_html=True)

    # ================================================================
    # BLOCO 5 — RENTABILIDADE E IMPACTO
    # ================================================================
    render_ads_section_title("Rentabilidade Ads")
    rent_cards = [
        render_ads_kpi_card("ROAS", br_number(kpis["roas_adjusted"], 2) + "x", roas_color, "Receita Ads / investimento ajustado. Meta: acima de 6.", roas_status, roas_meta),
        render_ads_kpi_card("ACOS", br_percent(kpis["acos_adjusted"]), acos_color, "Investimento / receita Ads x 100. Meta: abaixo de 15%.", acos_status, acos_meta),
        render_ads_kpi_card("Impacto na Margem", br_percent(margin_impact_pct), "#DC2626" if margin_impact_pct > 3 else "#0F766E", "Investimento como % da receita total da loja. Meta: ate 3%.", impact_status, impact_meta),
        render_ads_kpi_card("Margem Gerada", br_money(margin_contribution["margem_gerada"]), "#2563EB", "Receita Ads - Investimento Ads. Contribuicao liquida das campanhas.", "Monitoramento", "Deve ser positiva"),
    ]
    st.markdown(f'<div class="ads-kpi-grid">{"".join(rent_cards)}</div>', unsafe_allow_html=True)

    render_ads_section_title("Conciliacao com Financeiro Executivo")
    if financial_base.empty:
        st.info("Base financeira indisponivel para conciliacao neste contexto.")
    else:
        reconciliation = build_ads_financial_reconciliation(kpis, financial_base, ads, selected_period, all_ads_df)
        reconciliation_display = reconciliation.copy()
        for column in ["Ads & Performance", "Financeiro Executivo", "Diferenca"]:
            reconciliation_display[column] = reconciliation_display[column].map(br_money)
        st.dataframe(reconciliation_display, use_container_width=True, hide_index=True, height=90)

    # ================================================================
    # BLOCO 6 — CAMPANHAS (expanders)
    # ================================================================
    render_ads_section_title("Campanhas")
    if campaign.empty:
        st.info("Sem campanhas de Ads para o periodo selecionado.")
    else:
        campaign_display = campaign.copy()
        campaign_display["status"] = campaign_display["status_campanha"]
        display_columns = [
            "campaign_name", "cost", "revenue", "roas", "acos",
            "clicks", "impressions", "ctr", "cpc", "status", "acao_recomendada",
        ]
        formatted_campaign = campaign_display[display_columns].rename(
            columns={
                "campaign_name": "Campanha", "cost": "Investimento", "revenue": "Receita",
                "roas": "ROAS", "acos": "ACOS", "clicks": "Cliques",
                "impressions": "Impressoes", "ctr": "CTR", "cpc": "CPC",
                "status": "Status", "acao_recomendada": "Acao recomendada",
            }
        )
        for column in ["Investimento", "Receita", "CPC"]:
            formatted_campaign[column] = formatted_campaign[column].map(br_money)
        for column in ["ACOS", "CTR"]:
            formatted_campaign[column] = formatted_campaign[column].map(br_percent)
        formatted_campaign["ROAS"] = formatted_campaign["ROAS"].map(lambda value: br_number(value, 2))
        formatted_campaign["Cliques"] = formatted_campaign["Cliques"].map(lambda value: br_number(value, 0))
        formatted_campaign["Impressoes"] = formatted_campaign["Impressoes"].map(lambda value: br_number(value, 0))
        with st.expander("Tabela de campanhas", expanded=False):
            st.dataframe(formatted_campaign, use_container_width=True, hide_index=True, height=320)

        with st.expander("Rankings de campanhas", expanded=False):
            rankings = [
                ("Top campanhas por receita atribuida", campaign.sort_values("revenue", ascending=False).head(10), "revenue"),
                ("Top campanhas por ROAS", campaign[campaign["roas"] > 0].sort_values("roas", ascending=False).head(10), "roas"),
                ("Campanhas com maior gasto", campaign.sort_values("cost", ascending=False).head(10), "cost"),
                ("Campanhas com pior ACOS", campaign[campaign["acos"] > 0].sort_values("acos", ascending=False).head(10), "acos"),
            ]
            for title, data, metric in rankings:
                st.plotly_chart(
                    bar_chart(data.sort_values(metric), metric, "campaign_name", title, "h")
                    if not data.empty else empty_fig(title),
                    use_container_width=True,
                )

        with st.expander("Auditoria da fonte Ads", expanded=False):
            audit = pd.DataFrame(
            [
                ("Investimento Total Ads", "data/ml_ads_metrics.csv", "cost", "sum(cost)", "Alta se cobertura completa; estimada se parcial"),
                ("Receita Atribuida Ads", "data/ml_ads_metrics.csv", "revenue", "sum(revenue)", "Alta para dias cobertos pela API"),
                ("ROAS", "data/ml_ads_metrics.csv", "revenue/cost", "sum(revenue)/sum(cost ajustado)", "Ponderado por totais"),
                ("ACOS", "data/ml_ads_metrics.csv", "cost/revenue", "sum(cost ajustado)/sum(revenue)*100", "Ponderado por totais"),
                ("CTR", "data/ml_ads_metrics.csv", "clicks/impressions", "sum(clicks)/sum(impressions)*100", "Ponderado por totais"),
                ("CPC", "data/ml_ads_metrics.csv", "cost/clicks", "sum(cost ajustado)/sum(clicks)", "Ponderado por totais"),
                ("Conversao", "data/ml_ads_metrics.csv", "units/clicks", "sum(units)/sum(clicks)*100", "Ponderado por totais"),
                ("Cliques", "data/ml_ads_metrics.csv", "clicks", "sum(clicks)", "Alta para dias cobertos"),
                ("Impressoes", "data/ml_ads_metrics.csv", "impressions", "sum(impressions)", "Alta para dias cobertos"),
            ],
            columns=["KPI", "Fonte", "Coluna", "Formula", "Confiabilidade"],
        )
        st.dataframe(audit, use_container_width=True, hide_index=True, height=330)
        st.caption(
            "Origem API: Mercado Livre Product Ads em teste_ml_ads_metrics.py, endpoints "
            "/advertising/MLB/product_ads/campaigns/{campaign_id} e "
            "/advertising/MLB/advertisers/{advertiser_id}/product_ads/campaigns/search."
        )

    st.download_button(
        "Download CSV de Ads",
        data=ads.to_csv(index=False, encoding="utf-8-sig"),
        file_name="ml_ads_metrics_filtrado.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_alertas_executivos(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> None:
    """Renderiza monitor executivo consolidado de alertas."""

    bundle = build_all_alerts_bundle(filtered_sales, inventory_df, ads_df, filter_state)
    financial_alerts = bundle["financial"]
    ads_alerts = bundle["ads"]
    stock_alerts = bundle["stock_alerts"]
    registration_alerts = bundle["registration"]
    all_alerts = bundle["all"]
    financial_mode = str(filtered_sales.attrs.get("financial_mode", FINANCIAL_MODE_HYBRID))
    critical_total = int((all_alerts["nivel"] == "critico").sum()) if not all_alerts.empty else 0
    attention_total = int((all_alerts["nivel"] == "atencao").sum()) if not all_alerts.empty else 0
    products_at_risk = int(
        all_alerts.loc[all_alerts["MLB"].fillna("N/D") != "N/D", "MLB"].nunique()
    ) if not all_alerts.empty else 0
    campaigns_at_risk = int(
        all_alerts.loc[all_alerts["campanha"].fillna("N/D") != "N/D", "campanha"].nunique()
    ) if not all_alerts.empty else 0
    stock_critical = int((stock_alerts["nivel"] == "critico").sum()) if not stock_alerts.empty else 0
    negative_profit_total = (
        float(financial_alerts.loc[financial_alerts["tipo_alerta"] == "Lucro negativo", "lucro"].fillna(0).sum())
        if not financial_alerts.empty
        else 0.0
    )
    high_priority_total = int((all_alerts["prioridade"] == "Alta").sum()) if not all_alerts.empty else 0
    medium_priority_total = int((all_alerts["prioridade"] == "Media").sum()) if not all_alerts.empty else 0
    low_priority_total = int((all_alerts["prioridade"] == "Baixa").sum()) if not all_alerts.empty else 0
    estimated_impact_total = (
        float(all_alerts["impacto_financeiro_estimado"].fillna(0).sum())
        if not all_alerts.empty
        else 0.0
    )

    summary_values = [
        ("Total alertas criticos", br_number(critical_total)),
        ("Total alertas atencao", br_number(attention_total)),
        ("Produtos em risco", br_number(products_at_risk)),
        ("Campanhas em risco", br_number(campaigns_at_risk)),
        ("Estoque critico", br_number(stock_critical)),
        ("Lucro negativo total", br_money(negative_profit_total)),
        ("Alertas alta prioridade", br_number(high_priority_total)),
        ("Alertas media prioridade", br_number(medium_priority_total)),
        ("Alertas baixa prioridade", br_number(low_priority_total)),
        ("Impacto financeiro total estimado", br_money(estimated_impact_total)),
    ]
    for start in range(0, len(summary_values), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, summary_values[start : start + 4]):
            with col:
                kpi_card(label, value, financial_mode)

    cards = [
        ("Financeiro", len(financial_alerts), "critico" if not financial_alerts.empty else "saudavel"),
        ("Ads", len(ads_alerts), "critico" if not ads_alerts.empty else "saudavel"),
        ("Estoque", len(stock_alerts), "critico" if not stock_alerts.empty else "saudavel"),
        ("Cadastro", len(registration_alerts), "atencao" if not registration_alerts.empty else "saudavel"),
    ]
    cols = st.columns(4)
    for col, (label, count, level) in zip(cols, cards):
        color = {"critico": "#DC2626", "atencao": "#D97706", "saudavel": "#0F766E"}[level]
        with col:
            st.markdown(
                f"""
                <div class="kpi-card" style="border-top: 4px solid {color};">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{count}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    consolidated_columns = [
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "MLB",
        "SKU",
        "produto",
        "marca",
        "categoria",
        "receita",
        "lucro",
        "margem",
        "estoque",
        "campanha",
        "ACOS",
        "ROAS",
        "LinkAnuncio",
    ]
    st.markdown('<div class="section-title">Todos os alertas priorizados</div>', unsafe_allow_html=True)
    st.download_button(
        "Download CSV - Todos os alertas priorizados",
        data=all_alerts[consolidated_columns].to_csv(index=False, encoding="utf-8-sig"),
        file_name="todos_alertas_priorizados.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if all_alerts.empty:
        st.info("Nenhum alerta para os filtros atuais.")
    else:
        st.dataframe(
            style_executive_alerts(all_alerts[consolidated_columns]),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

    render_plano_acao(all_alerts)

    sections = [
        ("Financeiro", financial_alerts, "alertas_financeiros.csv"),
        ("Ads", ads_alerts, "alertas_ads.csv"),
        ("Estoque", stock_alerts, "alertas_estoque_executivo.csv"),
        ("Cadastro", registration_alerts, "alertas_cadastro.csv"),
    ]
    view_columns = [
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "nivel",
        "MLB",
        "SKU",
        "produto",
        "marca",
        "categoria",
        "receita",
        "margem",
        "lucro",
        "estoque",
        "campanha",
        "ACOS",
        "ROAS",
        "LinkAnuncio",
    ]
    for title, alerts_df, file_name in sections:
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        st.download_button(
            f"Download CSV - {title}",
            data=alerts_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
            key=f"download_alert_{title.lower()}",
        )
        if alerts_df.empty:
            st.info("Nenhum alerta para os filtros atuais.")
        else:
            st.dataframe(
                style_executive_alerts(prioritize_alerts(alerts_df)[view_columns]),
                use_container_width=True,
                hide_index=True,
                height=320,
            )


def render_plano_acao(all_alerts: pd.DataFrame) -> None:
    """Renderiza o modulo operacional do plano de acao."""

    st.markdown('<div class="section-title">Plano de Acao</div>', unsafe_allow_html=True)
    plan = enrich_action_plan(prioritize_alerts(all_alerts))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        priorities = st.multiselect(
            "Prioridade",
            sorted(plan["prioridade"].dropna().unique()) if not plan.empty else [],
            key="plan_prioridade",
        )
    with col2:
        owners = st.multiselect(
            "Responsavel",
            sorted(plan["responsavel_sugerido"].dropna().unique()) if not plan.empty else [],
            key="plan_responsavel",
        )
    with col3:
        deadlines = st.multiselect(
            "Prazo",
            ["Hoje", "24h", "7 dias"],
            key="plan_prazo",
        )
    with col4:
        alert_types = st.multiselect(
            "Tipo de alerta",
            sorted(plan["tipo_alerta"].dropna().unique()) if not plan.empty else [],
            key="plan_tipo_alerta",
        )

    filtered_plan = plan.copy()
    if priorities:
        filtered_plan = filtered_plan[filtered_plan["prioridade"].isin(priorities)]
    if owners:
        filtered_plan = filtered_plan[filtered_plan["responsavel_sugerido"].isin(owners)]
    if deadlines:
        filtered_plan = filtered_plan[filtered_plan["prazo_sugerido"].isin(deadlines)]
    if alert_types:
        filtered_plan = filtered_plan[filtered_plan["tipo_alerta"].isin(alert_types)]

    pending_total = int((filtered_plan["status_acao"] == "Pendente").sum()) if not filtered_plan.empty else 0
    due_today = int((filtered_plan["prazo_sugerido"] == "Hoje").sum()) if not filtered_plan.empty else 0
    due_24h = int((filtered_plan["prazo_sugerido"] == "24h").sum()) if not filtered_plan.empty else 0
    due_7d = int((filtered_plan["prazo_sugerido"] == "7 dias").sum()) if not filtered_plan.empty else 0
    pending_impact = (
        float(filtered_plan.loc[filtered_plan["status_acao"] == "Pendente", "impacto_financeiro_estimado"].sum())
        if not filtered_plan.empty
        else 0.0
    )

    action_values = [
        ("Acoes pendentes", br_number(pending_total)),
        ("Acoes para hoje", br_number(due_today)),
        ("Acoes 24h", br_number(due_24h)),
        ("Acoes 7 dias", br_number(due_7d)),
        ("Impacto financeiro pendente", br_money(pending_impact)),
    ]
    for start in range(0, len(action_values), 5):
        cols = st.columns(5)
        for col, (label, value) in zip(cols, action_values[start : start + 5]):
            with col:
                kpi_card(label, value)

    plan_columns = [
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "acao_recomendada",
        "responsavel_sugerido",
        "status_acao",
        "prazo_sugerido",
        "MLB",
        "SKU",
        "produto",
        "marca",
        "categoria",
        "receita",
        "lucro",
        "margem",
        "estoque",
        "campanha",
        "ACOS",
        "ROAS",
        "LinkAnuncio",
    ]
    st.download_button(
        "Download CSV - Plano de Acao",
        data=filtered_plan[plan_columns].to_csv(index=False, encoding="utf-8-sig"),
        file_name="plano_acao_alertas.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if filtered_plan.empty:
        st.info("Nenhuma acao encontrada para os filtros selecionados.")
    else:
        st.dataframe(
            style_action_plan(filtered_plan[plan_columns]),
            use_container_width=True,
            hide_index=True,
            height=520,
        )


def render_resumo_executivo_diario(
    filtered_sales: pd.DataFrame,
    inventory_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    filter_state: dict[str, object],
) -> None:
    """Renderiza a primeira tela de gestao diaria."""

    bundle = build_all_alerts_bundle(filtered_sales, inventory_df, ads_df, filter_state)
    all_alerts = bundle["all"]
    ads_alerts = bundle["ads"]
    stock_alerts = bundle["stock_alerts"]
    registration_alerts = bundle["registration"]
    financial_mode = str(filtered_sales.attrs.get("financial_mode", FINANCIAL_MODE_HYBRID))

    post_ads = calculate_post_ads_values(filtered_sales, ads_df)
    faturamento = post_ads["faturamento"]
    lucro_liquido = post_ads["lucro_liquido_estimado"]
    margem_liquida = (lucro_liquido / faturamento * 100) if faturamento else 0.0
    margem_pos_ads = post_ads["margem_pos_ads"]
    high_priority_count = int((all_alerts["prioridade"] == "Alta").sum()) if not all_alerts.empty else 0
    impact_total = (
        float(all_alerts["impacto_financeiro_estimado"].fillna(0).sum())
        if not all_alerts.empty
        else 0.0
    )
    due_today_count = int((all_alerts["prazo_sugerido"] == "Hoje").sum()) if not all_alerts.empty else 0
    campaigns_at_risk = int(
        ads_alerts.loc[ads_alerts["campanha"].fillna("N/D") != "N/D", "campanha"].nunique()
    ) if not ads_alerts.empty else 0

    top_values = [
        ("Faturamento", br_money(faturamento)),
        ("Lucro liquido estimado", br_money(lucro_liquido)),
        ("Margem liquida estimada", br_percent(margem_liquida)),
        ("Margem pos Ads", br_percent(margem_pos_ads)),
        ("Alertas alta prioridade", br_number(high_priority_count)),
        ("Impacto financeiro estimado", br_money(impact_total)),
        ("Acoes para hoje", br_number(due_today_count)),
        ("Campanhas em risco", br_number(campaigns_at_risk)),
    ]
    for start in range(0, len(top_values), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, top_values[start : start + 4]):
            with col:
                kpi_card(label, value, financial_mode)

    top_financial = all_alerts[
        (all_alerts["prioridade"] == "Alta")
        & all_alerts["tipo_alerta"].isin(["Margem liquida negativa", "Lucro negativo"])
    ].sort_values("impacto_financeiro_estimado", ascending=False).head(10)
    urgent_today = all_alerts[
        (all_alerts["prazo_sugerido"] == "Hoje")
        & (all_alerts["prioridade"] == "Alta")
    ].sort_values("impacto_financeiro_estimado", ascending=False).head(10)
    campaigns_review = ads_alerts[
        ads_alerts["tipo_alerta"].isin(["Gasto sem conversao", "ACOS muito alto", "ROAS ruim"])
    ].head(10)
    restock_products = stock_alerts[
        stock_alerts["tipo_alerta"].isin(
            ["Estoque zerado com vendas recentes", "Estoque baixo com alta venda"]
        )
    ].head(10)
    registration_fix = registration_alerts[
        registration_alerts["tipo_alerta"].isin(
            ["Produto sem CMV", "Produto sem marca", "Produto sem categoria"]
        )
    ].head(10)

    summary_exports = pd.concat(
        [
            top_financial.assign(secao="Top riscos financeiros"),
            urgent_today.assign(secao="Acoes urgentes hoje"),
            campaigns_review.assign(secao="Campanhas para revisar"),
            restock_products.assign(secao="Produtos para repor"),
            registration_fix.assign(secao="Produtos para corrigir cadastro"),
        ],
        ignore_index=True,
    )
    export_columns = [
        "secao",
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "MLB",
        "SKU",
        "produto",
        "marca",
        "categoria",
        "receita",
        "lucro",
        "margem",
        "estoque",
        "campanha",
        "ACOS",
        "ROAS",
        "LinkAnuncio",
    ]
    st.download_button(
        "Download CSV - Resumo Executivo Diario",
        data=summary_exports[export_columns].to_csv(index=False, encoding="utf-8-sig"),
        file_name="resumo_executivo_diario.csv",
        mime="text/csv",
        use_container_width=True,
    )

    short_columns = [
        "prioridade",
        "tipo_alerta",
        "impacto_financeiro_estimado",
        "produto",
        "campanha",
        "receita",
        "lucro",
        "margem",
        "estoque",
        "ACOS",
        "ROAS",
    ]
    sections = [
        ("Top 10 maiores riscos financeiros", top_financial),
        ("Top 10 acoes urgentes para hoje", urgent_today),
        ("Campanhas para pausar ou revisar", campaigns_review),
        ("Produtos para repor", restock_products),
        ("Produtos para corrigir CMV/cadastro", registration_fix),
    ]
    for title, section_df in sections:
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        if section_df.empty:
            st.info("Nenhum item para os filtros atuais.")
        else:
            st.dataframe(
                style_executive_alerts(section_df[short_columns]),
                use_container_width=True,
                hide_index=True,
                height=260,
            )


def compare_period_value(df: pd.DataFrame, metric: str, days: int) -> float | None:
    """Compara o ultimo ponto contra a media da janela temporal anterior."""

    if df.empty or len(df) < 2 or metric not in df.columns:
        return None

    ordered = df.sort_values("data").copy()
    ordered["data_ts"] = pd.to_datetime(ordered["data"])
    latest_row = ordered.iloc[-1]
    latest_date = latest_row["data_ts"]
    current = float(latest_row[metric]) if pd.notna(latest_row[metric]) else None
    previous_window = ordered[
        (ordered["data_ts"] >= latest_date - pd.Timedelta(days=days))
        & (ordered["data_ts"] < latest_date)
    ][metric].dropna()
    if current is None or previous_window.empty:
        return None

    previous = float(previous_window.mean())
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def compare_with_previous_day(df: pd.DataFrame, metric: str) -> float | None:
    """Compara o ultimo snapshot com o snapshot do dia anterior real."""

    if df.empty or metric not in df.columns:
        return None

    ordered = df.sort_values("data").copy()
    ordered["data_ts"] = pd.to_datetime(ordered["data"])
    latest_row = ordered.iloc[-1]
    previous_date = latest_row["data_ts"] - pd.Timedelta(days=1)
    previous_rows = ordered[ordered["data_ts"] == previous_date]
    if previous_rows.empty or pd.isna(latest_row[metric]) or pd.isna(previous_rows.iloc[-1][metric]):
        return None

    current = float(latest_row[metric])
    previous = float(previous_rows.iloc[-1][metric])
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def trend_label(value: float | None) -> str:
    """Formata variacao percentual curta."""

    return "N/D" if value is None else br_percent(value)


def build_historical_insights(df: pd.DataFrame) -> list[str]:
    """Gera insights automaticos a partir da serie historica."""

    if len(df) < 2:
        return ["Historico ainda curto para detectar tendencias confiaveis."]

    insights: list[str] = []
    revenue_change = compare_period_value(df, "faturamento", min(7, len(df) - 1))
    margin_change = compare_period_value(df, "margem_liquida", min(7, len(df) - 1))
    roas_change = compare_period_value(df, "roas", min(7, len(df) - 1))
    ads_change = compare_period_value(df, "investimento_ads", min(7, len(df) - 1))
    stock_change = compare_period_value(df, "estoque_total", min(7, len(df) - 1))

    if revenue_change is not None:
        insights.append(
            f"Tendencia de {'crescimento' if revenue_change >= 0 else 'queda'} no faturamento: {trend_label(revenue_change)}."
        )
    if margin_change is not None:
        insights.append(
            f"{'Melhora' if margin_change >= 0 else 'Piora'} de margem liquida: {trend_label(margin_change)}."
        )
    if roas_change is not None:
        insights.append(f"{'Melhora' if roas_change >= 0 else 'Piora'} de ROAS: {trend_label(roas_change)}.")
    if ads_change is not None:
        insights.append(
            f"Investimento em Ads {'aumentando' if ads_change >= 0 else 'reduzindo'}: {trend_label(ads_change)}."
        )
    if stock_change is not None:
        insights.append(
            f"Estoque total {'aumentando' if stock_change >= 0 else 'reduzindo'}: {trend_label(stock_change)}."
        )
    return insights or ["Historico insuficiente para insights automaticos adicionais."]


def render_historico_tendencias(selected_period: tuple[date, date]) -> None:
    """Renderiza a aba temporal baseada em DuckDB historico."""

    history = load_historical_data(str(DUCKDB_PATH))
    if history.empty:
        st.info("Historico ainda indisponivel. Execute a rotina de snapshots para alimentar esta aba.")
        return

    start_date, end_date = selected_period
    history = history[
        (history["data"] >= start_date)
        & (history["data"] <= end_date)
    ].copy()
    if history.empty:
        st.info(
            "Sem snapshots historicos para o periodo selecionado "
            f"({start_date:%d/%m/%Y} a {end_date:%d/%m/%Y})."
        )
        return

    latest = history.iloc[-1]
    cards = [
        ("Faturamento", br_money(latest["faturamento"])),
        ("Lucro liquido estimado", br_money(latest["lucro_liquido_estimado"])),
        ("Margem liquida", br_percent(latest["margem_liquida"])),
        ("Margem pos Ads", br_percent(latest["margem_pos_ads"])),
        ("Investimento Ads", br_money(latest["investimento_ads"])),
        ("ROAS", br_number(latest["roas"], 2)),
        ("ACOS", br_percent(latest["acos"])),
        ("Estoque total", br_number(latest["estoque_total"])),
        ("Pedidos", br_number(latest["pedidos"])),
        ("Ticket medio", br_money(latest["ticket_medio"])),
    ]
    for start in range(0, len(cards), 5):
        cols = st.columns(5)
        for col, (label, value) in zip(cols, cards[start : start + 5]):
            with col:
                kpi_card(label, value)

    yesterday_change = compare_with_previous_day(history, "faturamento")
    week_change = compare_period_value(history, "faturamento", 7)
    month_change = compare_period_value(history, "faturamento", 30)
    best_day = history.loc[history["faturamento"].idxmax()] if not history.empty else None
    worst_day = history.loc[history["faturamento"].idxmin()] if not history.empty else None

    compare_values = [
        ("Hoje vs ontem", trend_label(yesterday_change)),
        ("Ultimos 7 dias", trend_label(week_change)),
        ("Ultimos 30 dias", trend_label(month_change)),
        (
            "Melhor dia",
            f"{clean_date_label(best_day['data'])} | {br_money(best_day['faturamento'])}" if best_day is not None else "N/D",
        ),
        (
            "Pior dia",
            f"{clean_date_label(worst_day['data'])} | {br_money(worst_day['faturamento'])}" if worst_day is not None else "N/D",
        ),
    ]
    cols = st.columns(5)
    for col, (label, value) in zip(cols, compare_values):
        with col:
            kpi_card(label, value)

    insights = build_historical_insights(history)
    st.markdown('<div class="section-title">Insights automaticos</div>', unsafe_allow_html=True)
    for insight in insights:
        st.markdown(f"- {insight}")

    col1, col2 = st.columns(2)
    col1.plotly_chart(temporal_line_chart(history, "data", "faturamento", "Evolucao diaria de faturamento"), use_container_width=True)
    col2.plotly_chart(
        temporal_line_chart(history, "data", "lucro_liquido_estimado", "Evolucao diaria de lucro"),
        use_container_width=True,
    )

    col3, col4 = st.columns(2)
    col3.plotly_chart(temporal_line_chart(history, "data", "margem_liquida", "Evolucao diaria de margem"), use_container_width=True)
    col4.plotly_chart(temporal_line_chart(history, "data", "margem_pos_ads", "Evolucao diaria pos Ads"), use_container_width=True)

    ads_long = history.melt(
        id_vars="data",
        value_vars=["investimento_ads", "receita_ads", "roas"],
        var_name="metrica",
        value_name="valor",
    )
    col5, col6 = st.columns(2)
    col5.plotly_chart(
        temporal_line_chart(ads_long, "data", "valor", "Evolucao Ads", color="metrica"),
        use_container_width=True,
    )
    col6.plotly_chart(temporal_line_chart(history, "data", "estoque_total", "Evolucao estoque total"), use_container_width=True)

    col7, col8 = st.columns(2)
    col7.plotly_chart(temporal_line_chart(history, "data", "pedidos", "Evolucao pedidos"), use_container_width=True)
    monthly = history.copy()
    monthly["mes"] = pd.to_datetime(monthly["data"]).dt.to_period("M").astype(str)
    monthly = monthly.sort_values("data").drop_duplicates(subset=["mes"], keep="last")
    col8.plotly_chart(
        temporal_line_chart(monthly, "data", "faturamento", "Ultimo snapshot mensal de faturamento"),
        use_container_width=True,
    )

    heat_margin = history.assign(dia=history["data"]).pivot_table(
        index="dia",
        values="margem_liquida",
        aggfunc="mean",
    )
    heat_revenue = history.assign(dia=history["data"]).pivot_table(
        index="dia",
        values="faturamento",
        aggfunc="sum",
    )
    heat_margin = clean_temporal_pivot_axis(heat_margin.T, columns=True)
    heat_revenue = clean_temporal_pivot_axis(heat_revenue.T, columns=True)
    col9, col10 = st.columns(2)
    col9.plotly_chart(
        heatmap_from_pivot(heat_margin, "Heatmap temporal: data x margem", "Margem", "RdYlGn"),
        use_container_width=True,
    )
    col10.plotly_chart(
        heatmap_from_pivot(heat_revenue, "Heatmap temporal: data x faturamento", "Faturamento", "Tealgrn"),
        use_container_width=True,
    )


def financial_board(df: pd.DataFrame, ads_df: pd.DataFrame) -> pd.DataFrame:
    """Cria quadro financeiro mensal no estilo relatorio executivo."""

    if df.empty:
        return pd.DataFrame()

    board = (
        df.groupby("month", as_index=False)
        .agg(
            Receita_Liquida=("receita", "sum"),
            Lucro_Bruto=("lucro_bruto", "sum"),
            EBITDA_Ecommerce=("lucro_operacional", "sum"),
            Lucro_Liquido_Estimado=("lucro_liquido_estimado", "sum"),
            CMV=("CMV total", "sum"),
            Comissao_ML=("sale_fee", "sum"),
            Frete=("custo_frete_final", "sum"),
            Impostos=("imposto", "sum"),
            Custo_Fixo=("custo_fixo", "sum"),
            Extra=("extra", "sum"),
            Pedidos=("order_id", "nunique"),
            Itens=("quantity", "sum"),
        )
        .sort_values("month")
    )
    board["Receita Liquida"] = board["Receita_Liquida"]
    board["EBITDA Ecommerce"] = board["EBITDA_Ecommerce"]
    board["Lucro Liquido Estimado"] = board["Lucro_Liquido_Estimado"]
    board["Margem Bruta"] = board["Lucro_Bruto"] / board["Receita Liquida"].replace(0, pd.NA) * 100
    board["Margem EBITDA"] = board["EBITDA Ecommerce"] / board["Receita Liquida"].replace(0, pd.NA) * 100
    board["Margem Liquida Estimada"] = (
        board["Lucro Liquido Estimado"] / board["Receita Liquida"].replace(0, pd.NA) * 100
    )
    board["Ads total"] = 0.0
    if not ads_df.empty and "cost" in ads_df.columns:
        if "ads_data_ref" in ads_df.columns and ads_df["ads_data_ref"].notna().any():
            ads_monthly = ads_df.copy()
            ads_monthly["month"] = pd.to_datetime(ads_monthly["ads_data_ref"]).dt.to_period("M").astype(str)
            ads_monthly = ads_monthly.groupby("month", as_index=False).agg(Ads_total=("cost", "sum"))
            board = board.merge(ads_monthly, on="month", how="left")
            board["Ads total"] = board["Ads_total"].fillna(0.0)
            board = board.drop(columns=["Ads_total"])
        else:
            ads_total = float(ads_df["cost"].fillna(0).sum())
            board.loc[board.index[-1], "Ads total"] = ads_total
    board["Publicidade"] = board["Ads total"]
    board["Lucro pos Ads"] = board["Lucro Liquido Estimado"] - board["Ads total"]
    board["Margem pos Ads"] = board["Lucro pos Ads"] / board["Receita Liquida"].replace(0, pd.NA) * 100
    board["FCL Ecommerce"] = board["EBITDA Ecommerce"]
    board["Capital Empatado"] = pd.NA
    board["Giro de Estoque"] = pd.NA
    board["Crescimento mensal"] = board["Receita Liquida"].pct_change() * 100
    return board[
        [
            "month",
            "Receita Liquida",
            "EBITDA Ecommerce",
            "Lucro_Bruto",
            "Margem Bruta",
            "Margem EBITDA",
            "CMV",
            "Comissao_ML",
            "Frete",
            "Impostos",
            "Custo_Fixo",
            "Extra",
            "Publicidade",
            "Ads total",
            "Lucro Liquido Estimado",
            "Margem Liquida Estimada",
            "Lucro pos Ads",
            "Margem pos Ads",
            "FCL Ecommerce",
            "Capital Empatado",
            "Giro de Estoque",
            "Crescimento mensal",
        ]
    ]


def render_quadro_financeiro(df: pd.DataFrame, ads_df: pd.DataFrame) -> None:
    board = financial_board(df, ads_df)
    if board.empty:
        st.info("Sem dados para o quadro financeiro.")
        return

    display = board.rename(
        columns={
            "month": "Mes",
            "Lucro_Bruto": "Lucro Bruto",
            "Comissao_ML": "Comissao ML",
            "Custo_Fixo": "Rateio Operacional Seconds",
        }
    )
    st.dataframe(style_financial_board(display), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(line_chart(board, "month", "Crescimento mensal", "Crescimento mensal"), use_container_width=True)
    col2.plotly_chart(
        line_chart(board, "month", ["Margem EBITDA", "Margem Liquida Estimada", "Margem pos Ads"], "Evolucao margem"),
        use_container_width=True,
    )
    col3.plotly_chart(line_chart(board, "month", "EBITDA Ecommerce", "Evolucao EBITDA"), use_container_width=True)


def render_financeiro_executivo(
    financial_df: pd.DataFrame,
    ads_df: pd.DataFrame,
    selected_period: tuple[date, date] | None = None,
    comparison_financial_df: pd.DataFrame | None = None,
    all_ads_df: pd.DataFrame | None = None,
) -> None:
    financial_mode = str(financial_df.attrs.get("financial_mode", FINANCIAL_MODE_HYBRID))
    financials = calculate_executive_financials(financial_df, ads_df, selected_period, all_ads_df)
    current_summary = financial_period_summary(financial_df, ads_df, selected_period, all_ads_df)
    prev_period = previous_period(selected_period)
    previous_summary = None
    previous_df = pd.DataFrame()
    if comparison_financial_df is not None and prev_period:
        previous_df = filter_financial_period(comparison_financial_df, prev_period)
        previous_ads = filter_ads_by_period(all_ads_df if all_ads_df is not None else pd.DataFrame(), prev_period)[0]
        if not previous_df.empty:
            previous_summary = financial_period_summary(previous_df, previous_ads, prev_period, all_ads_df)

    st.caption(f"Fonte Financeira ativa: {financial_mode}")
    if prev_period and previous_summary is None:
        st.caption(f"Comparativo anterior indisponivel para {format_period(prev_period)}.")

    daily_exec = executive_financials_timeseries(financial_df, ads_df, "date")
    historical = historical_summary(comparison_financial_df, all_ads_df)
    render_executive_strategy_layer(current_summary, previous_summary, historical, selected_period, daily_exec)

    render_dre_executiva(financials)
    render_commercial_operational_costs(financials)
    render_comparativo_periodo(current_summary, previous_summary)

    st.markdown('<div class="section-title">Evolucao Financeira</div>', unsafe_allow_html=True)
    col_receita, col_custos = st.columns(2)
    with col_receita:
        st.plotly_chart(financial_revenue_result_chart(daily_exec), use_container_width=True)
    with col_custos:
        st.plotly_chart(financial_cost_pressure_chart(daily_exec), use_container_width=True)

    render_horizontal_financial_funnel(financials)

    render_saude_financeira(current_summary, previous_summary, comparison_financial_df)
    render_financial_insights(current_summary, previous_summary)
    render_financial_audit_expander(financial_df)
    render_missing_cmv_products_expander(financial_df)
    render_matching_inteligente_expander(financial_df)

    with st.expander("Detalhes tecnicos e auditoria financeira", expanded=False):
        render_ml_cost_audit(financial_df, ads_df, financials)
        st.markdown('<div class="section-title">Quadro financeiro executivo</div>', unsafe_allow_html=True)
        render_quadro_financeiro(financial_df, ads_df)
        if previous_summary is None and prev_period:
            st.info(
                "Sem base anterior comparavel para o periodo selecionado. "
                "No modo Seconds Oficial, isso pode ocorrer quando o snapshot nao possui historico temporal equivalente."
            )


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Cria copia formatada para exibicao em tabelas."""

    formatted = df.copy()
    for column in formatted.columns:
        if column in MONEY_COLUMNS or column in {
            "CMV",
            "receita",
            "ticket",
            "lucro_liquido_estimado",
            "lucro_operacional",
            "lucro_bruto",
            "cost",
            "revenue",
            "cpc",
            "impacto_financeiro_estimado",
        }:
            formatted[column] = formatted[column].map(br_money)
        elif column in PERCENT_COLUMNS:
            formatted[column] = formatted[column].map(br_percent)
        elif column in {
            "quantity",
            "quantidade",
            "pedidos",
            "pedidos_ultimos_7d",
            "pedidos_30d_anteriores",
            "estoque_atual",
            "vendidos_total",
            "quantidade_periodo",
            "estoque",
            "score_risco_curva_a",
        }:
            formatted[column] = formatted[column].map(lambda value: br_number(value, 0))
    return formatted


def style_financial_board(df: pd.DataFrame):
    """Formata o quadro financeiro com positivos em verde e negativos em vermelho."""

    money_cols = [
        "Receita Liquida",
        "EBITDA Ecommerce",
        "Lucro Bruto",
        "CMV",
        "Comissao ML",
        "Impostos",
        "Rateio Operacional Seconds",
        "Extra",
        "Publicidade",
        "Ads total",
        "Frete",
        "Lucro Liquido Estimado",
        "Lucro pos Ads",
        "FCL Ecommerce",
        "Capital Empatado",
    ]
    percent_cols = [
        "Margem Bruta",
        "Margem EBITDA",
        "Margem Liquida Estimada",
        "Margem pos Ads",
        "Crescimento mensal",
    ]

    def color_value(value):
        if pd.isna(value):
            return ""
        return "color: #0F766E; font-weight: 700;" if value >= 0 else "color: #DC2626; font-weight: 700;"

    formatters = {column: br_money for column in money_cols if column in df.columns}
    formatters.update({column: br_percent for column in percent_cols if column in df.columns})
    formatters.update({"Giro de Estoque": lambda value: "N/D" if pd.isna(value) else br_number(value, 2)})

    numeric_cols = [column for column in money_cols + percent_cols if column in df.columns]
    return df.style.format(formatters).map(color_value, subset=numeric_cols)


def style_stock_alerts(df: pd.DataFrame):
    """Formata alertas de estoque com cores executivas por severidade."""

    display = format_table(df)

    def color_status(row: pd.Series) -> list[str]:
        status = safe_text(row.get("status_estoque"))
        if status == "estoque zerado":
            color = "background-color: rgba(220, 38, 38, .16); color: #991B1B; font-weight: 700;"
        elif status == "estoque baixo":
            color = "background-color: rgba(217, 119, 6, .18); color: #92400E; font-weight: 700;"
        elif status == "excesso estoque":
            color = "background-color: rgba(100, 116, 139, .18); color: #334155; font-weight: 700;"
        else:
            color = ""
        return [color] * len(row)

    return display.style.apply(color_status, axis=1)


def style_ads_alerts(df: pd.DataFrame):
    """Formata alertas de Ads com semaforo executivo."""

    display = format_table(df)

    def color_row(row: pd.Series) -> list[str]:
        alerts = safe_text(row.get("alertas", ""))
        if "Sem conversao" in alerts or "ROAS baixo" in alerts:
            color = "background-color: rgba(220, 38, 38, .16); color: #991B1B; font-weight: 700;"
        elif "ACOS alto" in alerts or "Gasto alto e receita baixa" in alerts:
            color = "background-color: rgba(217, 119, 6, .18); color: #92400E; font-weight: 700;"
        else:
            color = "background-color: rgba(15, 118, 110, .14); color: #0F766E; font-weight: 700;"
        return [color] * len(row)

    return display.style.apply(color_row, axis=1)


def style_executive_alerts(df: pd.DataFrame):
    """Formata alertas executivos por prioridade."""

    display = format_table(df)

    def color_row(row: pd.Series) -> list[str]:
        priority = safe_text(row.get("prioridade"))
        if priority == "Alta":
            color = "background-color: rgba(220, 38, 38, .16); color: #991B1B; font-weight: 700;"
        elif priority == "Media":
            color = "background-color: rgba(217, 119, 6, .18); color: #92400E; font-weight: 700;"
        elif priority == "Baixa":
            color = "background-color: rgba(100, 116, 139, .18); color: #334155; font-weight: 700;"
        else:
            color = "background-color: rgba(15, 118, 110, .14); color: #0F766E; font-weight: 700;"
        return [color] * len(row)

    return display.style.apply(color_row, axis=1)


def style_action_plan(df: pd.DataFrame):
    """Formata o plano de acao com sinais visuais por prioridade e prazo."""

    display = format_table(df)

    def style_row(row: pd.Series) -> list[str]:
        priority = safe_text(row.get("prioridade"))
        deadline = safe_text(row.get("prazo_sugerido"))
        status = safe_text(row.get("status_acao"))

        if priority == "Alta":
            base = "background-color: rgba(220, 38, 38, .14); color: #991B1B; font-weight: 700;"
        elif priority == "Media":
            base = "background-color: rgba(217, 119, 6, .16); color: #92400E; font-weight: 700;"
        else:
            base = "background-color: rgba(100, 116, 139, .16); color: #334155; font-weight: 700;"

        if deadline == "Hoje":
            base += " border-left: 4px solid #DC2626;"
        elif deadline == "24h":
            base += " border-left: 4px solid #D97706;"
        elif deadline == "7 dias":
            base += " border-left: 4px solid #2563EB;"

        if status == "Pendente":
            base += " opacity: .96;"

        return [base] * len(row)

    return display.style.apply(style_row, axis=1)


def style_recommended_actions(df: pd.DataFrame):
    """Formata a Central de Acoes Recomendadas por prioridade executiva."""

    display = format_table(df)
    if "roas" in display.columns:
        display["roas"] = df["roas"].map(lambda value: br_number(value, 2))

    def style_row(row: pd.Series) -> list[str]:
        priority = safe_text(row.get("prioridade"))
        if priority == "Cr\u00edtica":
            color = "background-color: rgba(127, 29, 29, .20); color: #7F1D1D; font-weight: 700;"
        elif priority == "Alta":
            color = "background-color: rgba(220, 38, 38, .15); color: #991B1B; font-weight: 700;"
        elif priority == "M\u00e9dia":
            color = "background-color: rgba(217, 119, 6, .16); color: #92400E; font-weight: 700;"
        elif priority == "Baixa":
            color = "background-color: rgba(15, 118, 110, .13); color: #0F766E; font-weight: 700;"
        else:
            color = "background-color: rgba(100, 116, 139, .12); color: #334155; font-weight: 700;"
        return [color] * len(row)

    return display.style.apply(style_row, axis=1)


def style_curva_a_risk(df: pd.DataFrame):
    """Formata Curva A em risco por nivel de severidade."""

    display = format_table(df)

    def style_row(row: pd.Series) -> list[str]:
        level = safe_text(row.get("nivel_risco"))
        if level == "Cr\u00edtico":
            color = "background-color: rgba(220, 38, 38, .16); color: #991B1B; font-weight: 700;"
        elif level == "Alto":
            color = "background-color: rgba(249, 115, 22, .16); color: #9A3412; font-weight: 700;"
        elif level == "M\u00e9dio":
            color = "background-color: rgba(234, 179, 8, .16); color: #854D0E; font-weight: 700;"
        else:
            color = "background-color: rgba(100, 116, 139, .16); color: #334155; font-weight: 700;"
        return [color] * len(row)

    return display.style.apply(style_row, axis=1)


def render_base_completa(df: pd.DataFrame) -> None:
    search = st.text_input("Busca textual na base filtrada", placeholder="Produto, SKU, MLB, marca, categoria...")
    show_technical_columns = st.checkbox("Mostrar colunas tecnicas", value=False)
    view = df.copy()
    if search:
        mask = pd.Series(False, index=view.index)
        for column in ["item_id", "SKU", "produto", "Marca", "Nome da Categoria", "Status"]:
            if column in view.columns:
                mask = mask | view[column].astype(str).str.contains(search, case=False, na=False)
        view = view[mask]

    st.download_button(
        "Download CSV filtrado",
        data=view.to_csv(index=False, encoding="utf-8-sig"),
        file_name="dashboard_base_filtrada.csv",
        mime="text/csv",
        use_container_width=True,
    )
    executive_columns = [
        "date",
        "order_id",
        "item_id",
        "SKU",
        "produto",
        "Marca",
        "Nome da Categoria",
        "quantity",
        "receita",
        "CMV total",
        "sale_fee",
        "custo_frete_final",
        "imposto",
        "lucro_liquido_estimado",
        "margem_liquida_estimada",
        "FULL",
        "Flex",
        "Status",
        "status_estoque",
        "LinkAnuncio",
    ]
    visible = view if show_technical_columns else view[[column for column in executive_columns if column in view.columns]]
    st.dataframe(format_table(visible), use_container_width=True, hide_index=True, height=620)


def main() -> None:
    inject_css()

    try:
        with st.spinner("Preparando dashboard executivo..."):
            df = load_data(str(DATA_PATH))
            seconds_official_df = load_seconds_official_data(str(SECONDS_OFFICIAL_PATH))
            inventory_df = load_inventory_data(str(INVENTORY_PATH))
            ads_df = load_ads_metrics(str(ADS_METRICS_PATH))
            df = enrich_sales_with_inventory(df, inventory_df)
            # log_ads_load_debug(ads_df)
    except Exception as exc:
        st.error(f"Erro ao carregar a base: {exc}")
        st.info("Gere primeiro o arquivo data/dashboard_base_final.csv.")
        return

    if df.empty:
        st.warning("A base final esta vazia.")
        return

    filtered, selected_period, base_period, filter_state, financial_mode = apply_filters(df, inventory_df)
    filtered, seconds_period_warning = apply_seconds_snapshot_period_guard(filtered, selected_period)
    financial_filtered, financial_warning = prepare_financial_view(
        filtered,
        seconds_official_df,
        selected_period,
        filter_state,
        financial_mode,
    )
    comparison_filtered = apply_non_date_filters(df, filter_state)
    financial_comparison_base, _ = prepare_financial_view(
        comparison_filtered,
        seconds_official_df,
        selected_period,
        filter_state,
        financial_mode,
    )
    render_header(selected_period, base_period, filter_state.get("requested_period"))
    seconds_official_period = get_official_seconds_period(seconds_official_df)
    if financial_mode == FINANCIAL_MODE_OFFICIAL and seconds_official_period:
        st.info(f"Fonte: Seconds Oficial — snapshot {format_period(seconds_official_period)}. O filtro de periodo nao altera os cards oficiais.")
    if seconds_period_warning:
        st.warning(seconds_period_warning)
    if financial_warning:
        st.warning(financial_warning)
    # log_financial_mode_debug(financial_filtered, financial_mode)

    if filtered.empty and financial_filtered.empty:
        start_date, end_date = selected_period
        st.warning(
            "Nenhum dado encontrado para o periodo selecionado "
            f"({start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}) e demais filtros."
        )
        return

    filtered_ads, ads_filter_info = filter_ads_by_period(ads_df, selected_period)
    if ads_filter_info.get("message"):
        st.warning(str(ads_filter_info["message"]))
    # log_post_ads_debug(filtered, filtered_ads, selected_period, ads_filter_info, filter_state)
    # ads_audit_match_debug(ads_df, filtered_ads, financial_filtered, selected_period, ads_filter_info)
    # financials_debug = calculate_executive_financials(financial_filtered, filtered_ads, selected_period, ads_df)
    # log_commercial_costs_debug(financial_filtered, filtered_ads, financials_debug, selected_period)

    tabs = st.tabs(
        [
            "Visao Geral",
            "Inteligencia Comercial",
            "Financeiro Executivo",
            "Publicidade & Performance",
            "Operacional & Estoque",
            "Base Completa",
        ]
    )

    with tabs[0]:
        render_visao_geral_executiva(
            filtered,
            financial_filtered,
            inventory_df,
            filtered_ads,
            filter_state,
            selected_period,
        )
    with tabs[1]:
        render_inteligencia_comercial(filtered, financial_filtered, inventory_df, filtered_ads, filter_state)
    with tabs[2]:
        render_financeiro_executivo(
            financial_filtered,
            filtered_ads,
            selected_period,
            financial_comparison_base,
            ads_df,
        )
    with tabs[3]:
        render_ads_performance(filtered_ads, ads_filter_info, selected_period, financial_filtered, ads_df)
    with tabs[4]:
        render_operacional_estoque(filtered, inventory_df, filtered_ads, filter_state, selected_period)
    with tabs[5]:
        render_base_completa(filtered)


if __name__ == "__main__":
    main()
