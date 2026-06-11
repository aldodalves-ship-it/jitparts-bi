# Auditoria 2 - Conciliacao Financeira ML x Seconds

## 1. Resumo executivo

Base auditada: `data\dashboard_base_final.csv` com periodo de 01/02/2026 a 03/06/2026.

Conclusao: a receita e os pedidos estao no consolidado, mas a integridade financeira ainda depende da cobertura de parametros confiaveis da Seconds. Pedidos sem parametro confiavel continuam na DRE com receita e comissao ML, porem CMV, frete Seconds, imposto e rateio Seconds zerados. Isso nao descarta vendas, mas deixa parte da DRE com custo incompleto.

Score de integridade financeira: **91,6/100 - Excelente**.

## 2. Fluxo financeiro mapeado

| Etapa | Fonte | Chave | Linhas |
| --- | --- | --- | --- |
| Pedido Mercado Livre | data/ml_orders.csv | order_id + item_id | 11765 |
| Item vendido | data/ml_orders.csv | item_id | 1451 |
| Lookup Seconds | data/parametros_financeiros_seconds.csv | item_id normalizado MLB | 7190 |
| CMV | data/dashboard_base_final.csv | item_id + parametro_confiavel | 11765 |
| Rentabilidade | data/dashboard_base_final.csv | receita - custos unitarios Seconds | 11765 |
| Base consolidada | data/dashboard_base_final.csv | order_id | 11765 |
| DRE | app.py / calculate_executive_financials | colunas financeiras ativas | 11765 |

Regra encontrada no merge: `item_id` normalizado no padrao MLB e a chave de relacionamento com a Seconds. `SKU` e usado como identificador descritivo/executivo depois do merge.

## 3. Cobertura CMV

| Metrica | Quantidade |
| --- | --- |
| Pedidos totais | 11.765 |
| Pedidos com CMV valido | 10.929 |
| Pedidos sem CMV valido | 836 |
| Cobertura CMV (%) | 92,89% |

| Metrica | Valor |
| --- | --- |
| Receita total | R$ 2.094.004,42 |
| Receita com CMV valido | R$ 1.884.332,70 |
| Receita sem CMV valido | R$ 209.671,72 |

Meta minima informada: 99%. Status: **Abaixo da meta**.

## 4. Cobertura SKU / item_id

| Metrica | Valor |
| --- | --- |
| SKUs/item_id unicos vendidos | 1.451 |
| SKUs/item_id encontrados na Seconds | 1.293 |
| SKUs/item_id com parametro confiavel | 1.179 |
| Cobertura de match Seconds | 89,11% |
| Cobertura de parametro confiavel | 81,25% |

### Top 50 sem correspondencia Seconds

| item_id | SKU | Descricao | Receita | Pedidos |
| --- | --- | --- | --- | --- |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 11.896,82 | 16 |
| MLB5148208414 |   | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | R$ 8.480,47 | 82 |
| MLB4096955407 |   | Jogo Pastilha Dianteira Freelander 2 2007 A 2015 | R$ 7.625,09 | 32 |
| MLB4096861467 |   | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | R$ 5.310,35 | 18 |
| MLB4445439489 |   | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | R$ 3.911,08 | 2 |
| MLB6171701742 |   | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | R$ 3.504,57 | 2 |
| MLB4576053479 |   | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 | R$ 3.274,78 | 7 |
| MLB6520374496 |   | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | R$ 3.163,68 | 14 |
| MLB4449446401 |   | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | R$ 3.127,82 | 4 |
| MLB5376377560 |   | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | R$ 3.113,92 | 4 |
| MLB5755208526 |   | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | R$ 2.481,59 | 1 |
| MLB4084143565 | N/D | Par Disco Freio Dianteiro Ipanema 1.8 2.0 8v 1989 Até 1998 | R$ 2.469,51 | 13 |
| MLB5416066620 | N/D | Par Disco De Freio Tras Astra Meriva Vectra 1.8 2.0 2.2 2.4 | R$ 2.464,42 | 6 |
| MLB4087894455 | N/D | Par Disco Freio Dianteiro Tiida Livina D921 | R$ 2.427,26 | 8 |
| MLB4053750901 |   | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | R$ 2.375,92 | 1 |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | R$ 2.364,00 | 1 |
| MLB6505840046 |   | Reservatório De Água Peugeot 206 207 1.4 1.6 16v Com Tampa | R$ 2.330,57 | 24 |
| MLB4084541091 | N/D | Par Disco Freio Dian Corolla 1.8 16v 08 A 13 2.0 16v 10 A 13 | R$ 2.275,96 | 6 |
| MLB4080244565 | N/D | Molas Esportivas Pro-kit Eibach Mercedes C180 C200 C250 W204 | R$ 2.245,00 | 1 |
| MLB5420786736 | N/D | Par Tambor Freio Traseiro Corsa 1.0 1.4 1.8 Frente Montana | R$ 2.098,65 | 6 |
| MLB5771132650 |   | Jogo Junta Completo Fiesta 1.0 8v Zetec Rocam Gasolina | R$ 2.088,35 | 9 |
| MLB4482750235 |   | Kit Válvula Admissão E Escape Cruze Tracker 1.8 16v Ecotec | R$ 1.843,94 | 3 |
| MLB5420670994 | N/D | Par Disco De Freio Dianteiro Sólido Kwid 1.0 2017 2018 2019 | R$ 1.809,50 | 8 |
| MLB4087944673 | N/D | Par Tambor De Freio Traseiro Ford Ka 1.0 1.3 1.6 1997 A 2014 | R$ 1.807,82 | 5 |
| MLB6502062310 |   | Cano Duplo De Água Do Motor Para Amarok 2.0 16v 2010/... Preto | R$ 1.771,88 | 9 |
| MLB5298371120 |   | Jogo Aneis 0,60 147 Uno Fiorino Premio 1.0 1.3 1.5 8v 84/95 | R$ 1.755,24 | 11 |
| MLB4430273829 |   | Kit Jg Pistao E Aneis Bravo Doblo Idea Linea 1.8 16v E-torq 0,40mm | R$ 1.744,36 | 3 |
| MLB4404425007 |   | Par Disco De Freio Dianteiro Para Volare V6 6000 2004 À 2012 | R$ 1.730,96 | 3 |
| MLB3871363101 |   | Junta Cabeçote Aço Inox Onix Plus Ecotec 1.0 12v 19/24 | R$ 1.725,79 | 9 |
| MLB5663268708 |   | Tambor Campana Freio Traseira Fusca 4 Furos C/cubo Par | R$ 1.701,24 | 4 |
| MLB4527961467 |   | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 | R$ 1.659,56 | 3 |
| MLB6143573326 |   | Jogo Junta Cabeçote Azera Santa Fé Sorento 3.3 08/21 | R$ 1.654,53 | 3 |
| MLB4404424995 |   | Par De Disco De Freio Dianteiro Sprinter 313 413 2002 À 2006 | R$ 1.652,34 | 5 |
| MLB6079848988 |   | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 Std | R$ 1.647,90 | 3 |
| MLB5762363874 |   | Bomba De Água Takao Isuzu Gmc 7.110 4.3 8v 4hf1 Sohc | R$ 1.640,88 | 4 |
| MLB5410746906 |   | Molas Eibach Pro-kit Gm Astra \| Vectra Sedan - Gt 2.0 Mec | R$ 1.636,58 | 1 |
| MLB6143663810 |   | Par Disco Freio Dianteiro Gm Tracker 1.2 2020 2021 2022 2023 | R$ 1.503,61 | 3 |
| MLB6143754498 |   | Par Disco Freio Traseiro Renault Megane 2.0 16v 2006/2009 | R$ 1.421,93 | 3 |
| MLB4249797695 |   | Par Disco Freio Dianteiro Pt Cruiser 2001 A 2010 2.0 2.4 16v | R$ 1.418,59 | 3 |
| MLB6087179454 |   | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 0,50mm | R$ 1.417,94 | 3 |
| MLB5416245032 | N/D | Par Disco Freio Traseiro Renault Master 2.3 2013 A 2018 | R$ 1.305,93 | 3 |
| MLB6505840046 |   | Reservatório De Água 206 207 1.4 1.6 16v Com Tampa | R$ 1.179,39 | 12 |
| MLB5752064294 |   | Engate Reboque Fixo Captiva 2008 A 2015 | R$ 1.175,24 | 2 |
| MLB4480143025 |   | Kit Valvula Admissao E Escape Clio Sandero Logan 1.0 16v D4d | R$ 1.165,95 | 3 |
| MLB4381396847 |   | Jogo Pistao Com Aneis Palio 1.0 8v Fiasa 1996 A 2001 Takao Std | R$ 1.093,88 | 2 |
| MLB4604567493 |   | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | R$ 1.014,55 | 10 |
| MLB5771134578 |   | Junta Comp C/ Retentores (jg) Tiggo 7 1.5 16v 2017 A 2020 | R$ 1.006,75 | 1 |
| MLB4404893661 |   | Jogo Junta Cabeçote Sentra Tiida Versa Fluence 1.8 2.0 06/19 | R$ 998,77 | 4 |
| MLB4209329255 |   | Pastilha Freio Sprinter 416 Cdi 2.2 16v 2019 Em Diante | R$ 994,18 | 4 |
| MLB4573497959 |   | Jogo Pistao 0,50 Onix Novo 1.0 8v 2017 A 2022 | R$ 953,17 | 2 |

## 5. CMV zerado ou suspeito

| item_id | SKU | produto | Receita | CMV | Margem | Motivo | Classificacao |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MLB6415815014 | T-508 | Polia Do Virabrequim C/damper - Amarok 3.0 Tdi V6 - T-508 | R$ 3.596,77 | R$ 0,00 | 87,00% | CMV zerado | Critico |
| MLB5755208526 |   | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | R$ 2.481,59 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB4053750901 |   | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | R$ 2.375,92 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | R$ 2.364,00 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB6171701742 |   | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | R$ 2.336,38 | R$ 0,00 | 91,50% | CMV zerado | Critico |
| MLB4080244565 | N/D | Molas Esportivas Pro-kit Eibach Mercedes C180 C200 C250 W204 | R$ 2.245,00 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB6407948012 | T-431 | Polia Do Virabrequim Damper - Gran Blazer - Ford:bg1t6312-ba | R$ 2.079,92 | R$ 0,00 | 86,50% | CMV zerado | Critico |
| MLB6171701834 | 33-3153 | Filtro De Ar K&n Porsche 911 (992 E 991.2) 2019+  Kit C/2 | R$ 2.070,36 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB5410454620 | CE10-40-036-07-22 | Mola Eibach Pro-kit Honda Civic 10 X 1.5 T \| 2.0 Flex 2017+ | R$ 2.043,00 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB4445439489 |   | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | R$ 1.955,54 | R$ 0,00 | 94,00% | CMV zerado | Critico |
| MLB4445439489 |   | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | R$ 1.955,54 | R$ 0,00 | 94,00% | CMV zerado | Critico |
| MLB5410746906 |   | Molas Eibach Pro-kit Gm Astra \| Vectra Sedan - Gt 2.0 Mec | R$ 1.636,58 | R$ 0,00 | 89,20% | CMV zerado | Critico |
| MLB6171701742 |   | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | R$ 1.168,19 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB6263822942 | VADCH27 - VESCH27 | Kit Válvula Admissão (12) E Escape (12) Dodge 2.7 Journey V6 | R$ 1.118,40 | R$ 0,00 | 92,00% | CMV zerado | Critico |
| MLB4506609417 | T-152 | Polia Do Virabrequim C/damper - Hilux 3.0 - T-152 | R$ 1.009,57 | R$ 0,00 | 87,00% | CMV zerado | Critico |
| MLB5771134578 |   | Junta Comp C/ Retentores (jg) Tiggo 7 1.5 16v 2017 A 2020 | R$ 1.006,75 | R$ 0,00 | 88,00% | CMV zerado | Critico |
| MLB5751965116 |   | Engate Reboque Removível Veloster 2012 A 2018 | R$ 907,33 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB4445866853 | 33-5111 | Filtro Ar K&n 33-5111 Mini Cooper Jcw Countryman 2.0 / 2020 | R$ 870,21 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB4614618825 | BOD20A | Bomba Oleo Sentra Novo 2.0 16v Flex 2013/2020 Mr20de | R$ 830,37 | R$ 0,00 | 88,00% | CMV zerado | Critico |
| MLB4614618825 | BOD20A | Bomba Oleo Sentra Novo 2.0 16v Flex 2013/2020 Mr20de | R$ 830,37 | R$ 0,00 | 88,00% | CMV zerado | Critico |
| MLB4604064777 | 1515165PK30 | Junta Cabeçote Sob Medida 2,6mm C2 C3 205 206 207 1.4 8v | R$ 828,00 | R$ 0,00 | 98,64% | CMV zerado | Critico |
| MLB6153696204 |   | Engate Reboque Outlander 2025 2026 700kg Removível Completo | R$ 825,84 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 806,36 | R$ 0,00 | 88,22% | CMV zerado | Critico |
| MLB4449446401 |   | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | R$ 800,60 | R$ 0,00 | 88,00% | CMV zerado | Critico |
| MLB5376155402 | Ad1007 | Engate Rabicho Reboque Removivel 700kg Audi Q3 2020 A 2024 Preto | R$ 795,47 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB5376377560 |   | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | R$ 791,38 | R$ 0,00 | 83,85% | CMV zerado | Critico |
| MLB4449446401 |   | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | R$ 776,58 | R$ 0,00 | 90,55% | CMV zerado | Critico |
| MLB4449446401 |   | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | R$ 775,32 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB4449446401 |   | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | R$ 775,32 | R$ 0,00 | 83,00% | CMV zerado | Critico |
| MLB5376377560 |   | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | R$ 774,18 | R$ 0,00 | 86,09% | CMV zerado | Critico |
| MLB5376377560 |   | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | R$ 774,18 | R$ 0,00 | 86,09% | CMV zerado | Critico |
| MLB5376377560 |   | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | R$ 774,18 | R$ 0,00 | 86,09% | CMV zerado | Critico |
| MLB4196605661 |   | Engate Reboque Removível Audi A5 2011 Até 2017 700kg | R$ 766,14 | R$ 0,00 | 86,09% | CMV zerado | Critico |
| MLB4665291183 | GPSFO021 | Trocador De Calor Dodge Journey Cherokee 3.6 V6 Aluminio | R$ 755,21 | R$ 0,00 | 89,00% | CMV zerado | Critico |
| MLB6263914136 | VADCY13 - VESCY13 | Kit Válvulas Escape + Admissão Takao Chery Face 1.3 16v Gas | R$ 750,11 | R$ 0,00 | 92,00% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 743,06 | R$ 0,00 | 90,66% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 743,06 | R$ 0,00 | 90,66% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 90,69% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 90,69% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 90,69% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 739,97 | R$ 0,00 | 90,69% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 737,08 | R$ 0,00 | 91,09% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 733,78 | R$ 0,00 | 88,00% | CMV zerado | Critico |
| MLB4411222171 |   | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | R$ 733,78 | R$ 0,00 | 88,00% | CMV zerado | Critico |

Classificacao usada: Critico para CMV negativo, zerado ou maior que a receita; Atencao para CMV unitario abaixo de 5% do preco unitario em parametro confiavel.

## 6. Auditoria de rentabilidade

Formula do consolidado: `lucro_liquido_estimado = receita - cmv_total - comissao_total - frete_total - imposto_total - custo_fixo_total`.

Formula de margem: `margem_liquida_estimada = lucro_liquido_estimado / receita * 100`.

Origem das colunas: `dashboard_base_final.csv`, gerado por `merge_ml_seconds.py`, com custos unitarios vindos de `parametros_financeiros_seconds.csv`.

### Top 20 inconsistencias de rentabilidade

| order_id | item_id | SKU | produto | Receita | Lucro | Margem | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2000015509900896 | MLB4482301259 | VESPG16-2 | Jogo Válvula Escape Peugeot 206 1.6 16v 2004 2005 2006 | R$ 36,74 | R$ -211,09 | -574,55% | Margem abaixo de -100% |
| 2000015310745972 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 14,25 | R$ -42,90 | -301,05% | Margem abaixo de -100% |
| 2000015272209912 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 14,25 | R$ -42,90 | -301,05% | Margem abaixo de -100% |
| 2000015296553854 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 14,25 | R$ -42,90 | -301,05% | Margem abaixo de -100% |
| 2000015306326014 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 9,50 | R$ -28,60 | -301,05% | Margem abaixo de -100% |
| 2000015289022758 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 9,50 | R$ -28,60 | -301,05% | Margem abaixo de -100% |
| 2000015304252116 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 4,75 | R$ -14,30 | -301,05% | Margem abaixo de -100% |
| 2000015306854418 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 4,75 | R$ -14,30 | -301,05% | Margem abaixo de -100% |
| 2000015311584898 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 4,75 | R$ -14,30 | -301,05% | Margem abaixo de -100% |
| 2000015294185638 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 4,75 | R$ -14,30 | -301,05% | Margem abaixo de -100% |
| 2000015277086210 | MLB4366444263 | 78514000-1 | Esguicho Com Engate Rosqueado Tramontina E Jato Regulável | R$ 4,75 | R$ -14,30 | -301,05% | Margem abaixo de -100% |
| 2000016212369962 | MLB6153058754 | 78506000-1 | Engate Rápido P/ Mangueira 1/2 Tramontina 78506000 Cor Laranja | R$ 60,00 | R$ -105,40 | -175,67% | Margem abaixo de -100% |
| 2000015622709320 | MLB6153058754 | 78506000-1 | Engate Rápido P/ Mangueira 1/2 Tramontina 78506000 Cor Laranja | R$ 30,00 | R$ -52,70 | -175,67% | Margem abaixo de -100% |
| 2000016603593236 | MLB6153058754 | 78506000-1 | Engate Rápido P/ Mangueira 1/2 Tramontina 78506000 Cor Laranja | R$ 30,00 | R$ -52,70 | -175,67% | Margem abaixo de -100% |

## 7. Pedidos descartados ou com custo fora da DRE completa

| Motivo | Pedidos | Receita |
| --- | --- | --- |
| Sem item_id no pedido ML | 0 | R$ 0,00 |
| Pedido ML fora do consolidado | 0 | R$ 0,00 |
| Sem match Seconds | 624 | R$ 155.311,42 |
| Sem parametro confiavel | 836 | R$ 209.671,72 |
| Sem CMV valido | 836 | R$ 209.671,72 |
| Sem rentabilidade confiavel | 836 | R$ 209.671,72 |

Observacao: os motivos nao sao mutuamente exclusivos. O ponto critico e que pedidos sem CMV valido nao sao descartados da receita; eles entram com custo parcial.

## 8. Conciliacao da DRE

Periodo recalculado: 01/02/2026 a 03/06/2026. Modo usado: Estimativa Hibrida ML + Seconds.

| Linha DRE | Valor Recalculado | Valor Tela | Diferenca |
| --- | --- | --- | --- |
| Receita Bruta | R$ 2.094.004,42 | R$ 2.094.004,42 | R$ 0,00 |
| Comissao | R$ 237.102,98 | R$ 237.102,98 | R$ 0,00 |
| CMV | R$ 994.136,18 | R$ 994.136,18 | R$ 0,00 |
| Frete | R$ 231.520,25 | R$ 231.520,25 | R$ 0,00 |
| Impostos | R$ 373.154,53 | R$ 373.154,53 | R$ 0,00 |
| Rateio Seconds | R$ 101.278,39 | R$ 101.278,39 | R$ 0,00 |
| Resultado Base | R$ 156.812,09 | R$ 156.812,09 | R$ 0,00 |
| Custos Operacionais | R$ 10.470,02 | R$ 10.470,02 | R$ 0,00 |
| Resultado Final | R$ 146.342,07 | R$ 146.342,07 | R$ 0,00 |

O campo "Valor Tela" representa a mesma regra usada pelo app no modo hibrido: colunas financeiras ativas apos mapear `cmv_total`, `frete_total`, `imposto_total`, `custo_fixo_total` e `comissao_total`.

## 9. Integridade financeira

| Componente | Pontuacao |
| --- | --- |
| Cobertura CMV | 92,89% |
| Cobertura SKU | 89,11% |
| Cobertura Rentabilidade | 92,89% |
| Pedidos conciliados | 92,89% |
| Receita conciliada | 89,99% |

Racional: o score e a media simples de cobertura CMV, cobertura SKU, cobertura de rentabilidade, pedidos conciliados e receita conciliada.

Classificacao final: **Excelente**.

## 10. Bases auditadas

| Arquivo | Existe | Linhas | Periodo | Atualizado em |
| --- | --- | --- | --- | --- |
| data\ml_orders.csv | Sim | 11765 | 01/02/2026 a 03/06/2026 | 03/06/2026 16:01:51 |
| data\ml_shipments.csv | Sim | 11765 | 01/02/2026 a 03/06/2026 | 03/06/2026 16:02:05 |
| data\parametros_financeiros_seconds.csv | Sim | 7190 | N/D | 20/05/2026 18:29:45 |
| data\base_seconds_principal.csv | Sim | 7190 | N/D | 20/05/2026 18:11:44 |
| data\dashboard_base_final.csv | Sim | 11765 | 01/02/2026 a 03/06/2026 | 03/06/2026 16:17:40 |
| data\ml_ads_metrics.csv | Sim | 782 | N/D | 03/06/2026 16:17:37 |

## 11. Smoke tests de periodos

| Teste | Periodo | Pedidos | Cobertura CMV | Score |
| --- | --- | --- | --- | --- |
| Maio completo | 01/05/2026 a 31/05/2026 | 3.067 | 89,11% | 89,15% |
| Ultimos 30 dias | 05/05/2026 a 03/06/2026 | 2.929 | 87,40% | 87,95% |
| Periodo customizado | 01/06/2026 a 03/06/2026 | 246 | 75,61% | 79,91% |

Modos verificados no codigo: Hibrido usa `dashboard_base_final.csv`; Seconds Oficial usa `base_seconds_principal.csv` em granularidade de anuncio/snapshot e nao e uma conciliacao pedido a pedido.

## 12. Correcoes aplicadas

Nenhuma regra de negocio financeira foi alterada nesta auditoria. O dashboard recebeu apenas um expander tecnico de auditoria financeira para expor cobertura CMV, cobertura SKU, receita conciliada, pedidos conciliados e score.

## 13. Riscos remanescentes

- Cobertura CMV abaixo de 99% compromete a leitura de margem em parte da receita.
- Pedidos sem parametro confiavel ficam com CMV/frete/imposto/rateio Seconds zerados, elevando artificialmente a rentabilidade desses pedidos.
- `SKU` nao e a chave primaria do merge; divergencias de SKU devem ser corrigidas na base Seconds/parametros, mas a chave operacional e `item_id`.
- O modo Seconds Oficial nao valida DRE pedido a pedido; ele serve como snapshot financeiro agregado por anuncio.

## 14. Checklist final

- [x] Fluxo ML -> item -> item_id -> Seconds -> CMV -> DRE mapeado.
- [x] Cobertura CMV calculada.
- [x] Cobertura SKU/item_id calculada.
- [x] Pedidos sem custo financeiro confiavel identificados.
- [x] DRE recalculada contra a regra do app.
- [x] Score de integridade financeira calculado.
- [ ] Elevar cobertura CMV para no minimo 99% antes de liberar margem para diretoria sem ressalva.
