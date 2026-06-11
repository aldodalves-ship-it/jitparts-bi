<<<<<<< HEAD
# Auditoria 3 - Itens sem CMV confiavel

## 1. Resumo executivo

Base auditada: `data\dashboard_base_final.csv`.

Pedidos totais: **11.765**  
Pedidos com CMV valido: **10.929**  
Pedidos sem CMV valido: **836**  
Cobertura CMV atual: **92,89%**  
Receita sem CMV valido: **R$ 209.671,72**

Foram identificados **273 itens/item_id** com algum problema de CMV confiavel. A lista operacional foi gravada em:

- `resultado\itens_sem_cmv_completo.csv`
- `resultado\top_100_sem_cmv.csv`

## 2. Top 20 produtos mais criticos

| item_id | sku | produto | marca | categoria | motivo_sem_cmv | receita_total | pedidos | unidades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLB4411222171 | N/D | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 11.896,82 | 16 | 16 |
| MLB5148208414 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 8.480,47 | 82 | 82 |
| MLB4096955407 | N/D | Jogo Pastilha Dianteira Freelander 2 2007 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 7.625,09 | 32 | 33 |
| MLB4096861467 | N/D | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 5.310,35 | 18 | 18 |
| MLB4445439489 | N/D | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.911,08 | 2 | 4 |
| MLB6415815014 | T-508 | Polia Do Virabrequim C/damper - Amarok 3.0 Tdi V6 - T-508 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 3.596,77 | 1 | 1 |
| MLB6171701742 | N/D | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.504,57 | 2 | 3 |
| MLB4576053479 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.274,78 | 7 | 7 |
| MLB6520374496 | N/D | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.163,68 | 14 | 20 |
| MLB4449446401 | N/D | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.127,82 | 4 | 4 |
| MLB5376377560 | N/D | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.113,92 | 4 | 4 |
| MLB4604743131 | 131590ML2 | Junta Cabeçote Sob Medida 1.20mm Ka Ka+ New Fiesta | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 3.059,52 | 10 | 10 |
| MLB5755208526 | N/D | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.481,59 | 1 | 1 |
| MLB4084143565 | N/D | Par Disco Freio Dianteiro Ipanema 1.8 2.0 8v 1989 Até 1998 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.469,51 | 13 | 13 |
| MLB5416066620 | N/D | Par Disco De Freio Tras Astra Meriva Vectra 1.8 2.0 2.2 2.4 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.464,42 | 6 | 7 |
| MLB4087894455 | N/D | Par Disco Freio Dianteiro Tiida Livina D921 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.427,26 | 8 | 8 |
| MLB4053750901 | N/D | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.375,92 | 1 | 1 |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.364,00 | 1 | 1 |
| MLB6505840046 | N/D | Reservatório De Água Peugeot 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.330,57 | 24 | 24 |
| MLB4604035479 | 1212136PK | Junta Superior Cabeçote Corsa Prisma Montana Ohc 1.4 06/.. | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 2.285,84 | 17 | 18 |

## 3. Top 100 por receita

| item_id | sku | produto | marca | categoria | motivo_sem_cmv | receita_total | pedidos | unidades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLB4411222171 | N/D | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 11.896,82 | 16 | 16 |
| MLB5148208414 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 8.480,47 | 82 | 82 |
| MLB4096955407 | N/D | Jogo Pastilha Dianteira Freelander 2 2007 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 7.625,09 | 32 | 33 |
| MLB4096861467 | N/D | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 5.310,35 | 18 | 18 |
| MLB4445439489 | N/D | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.911,08 | 2 | 4 |
| MLB6415815014 | T-508 | Polia Do Virabrequim C/damper - Amarok 3.0 Tdi V6 - T-508 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 3.596,77 | 1 | 1 |
| MLB6171701742 | N/D | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.504,57 | 2 | 3 |
| MLB4576053479 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.274,78 | 7 | 7 |
| MLB6520374496 | N/D | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.163,68 | 14 | 20 |
| MLB4449446401 | N/D | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.127,82 | 4 | 4 |
| MLB5376377560 | N/D | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.113,92 | 4 | 4 |
| MLB4604743131 | 131590ML2 | Junta Cabeçote Sob Medida 1.20mm Ka Ka+ New Fiesta | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 3.059,52 | 10 | 10 |
| MLB5755208526 | N/D | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.481,59 | 1 | 1 |
| MLB4084143565 | N/D | Par Disco Freio Dianteiro Ipanema 1.8 2.0 8v 1989 Até 1998 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.469,51 | 13 | 13 |
| MLB5416066620 | N/D | Par Disco De Freio Tras Astra Meriva Vectra 1.8 2.0 2.2 2.4 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.464,42 | 6 | 7 |
| MLB4087894455 | N/D | Par Disco Freio Dianteiro Tiida Livina D921 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.427,26 | 8 | 8 |
| MLB4053750901 | N/D | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.375,92 | 1 | 1 |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.364,00 | 1 | 1 |
| MLB6505840046 | N/D | Reservatório De Água Peugeot 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.330,57 | 24 | 24 |
| MLB4604035479 | 1212136PK | Junta Superior Cabeçote Corsa Prisma Montana Ohc 1.4 06/.. | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 2.285,84 | 17 | 18 |
| MLB4084541091 | N/D | Par Disco Freio Dian Corolla 1.8 16v 08 A 13 2.0 16v 10 A 13 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.275,96 | 6 | 6 |
| MLB4080244565 | N/D | Molas Esportivas Pro-kit Eibach Mercedes C180 C200 C250 W204 | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.245,00 | 1 | 1 |
| MLB5420786736 | N/D | Par Tambor Freio Traseiro Corsa 1.0 1.4 1.8 Frente Montana | MDS | Tambor | SEM_MATCH_SECONDS | R$ 2.098,65 | 6 | 6 |
| MLB5771132650 | N/D | Jogo Junta Completo Fiesta 1.0 8v Zetec Rocam Gasolina | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.088,35 | 9 | 9 |
| MLB6407948012 | T-431 | Polia Do Virabrequim Damper - Gran Blazer - Ford:bg1t6312-ba | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 2.079,92 | 1 | 1 |
| MLB6171701834 | 33-3153 | Filtro De Ar K&n Porsche 911 (992 E 991.2) 2019+  Kit C/2 | K&N | Filtros de Ar | PARAMETRO_NAO_CONFIAVEL | R$ 2.070,36 | 1 | 1 |
| MLB5410454620 | CE10-40-036-07-22 | Mola Eibach Pro-kit Honda Civic 10 X 1.5 T \| 2.0 Flex 2017+ | Eibach | Molas | PARAMETRO_NAO_CONFIAVEL | R$ 2.043,00 | 1 | 1 |
| MLB4482750235 | N/D | Kit Válvula Admissão E Escape Cruze Tracker 1.8 16v Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.843,94 | 3 | 3 |
| MLB5420670994 | N/D | Par Disco De Freio Dianteiro Sólido Kwid 1.0 2017 2018 2019 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 1.809,50 | 8 | 8 |
| MLB4087944673 | N/D | Par Tambor De Freio Traseiro Ford Ka 1.0 1.3 1.6 1997 A 2014 | MDS | Tambor | SEM_MATCH_SECONDS | R$ 1.807,82 | 5 | 5 |
| MLB6611111530 | 141229PK | Junta Superior Cabeçote Palio Siena Uno Fiasa 96/... | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.782,24 | 25 | 27 |
| MLB6502062310 | N/D | Cano Duplo De Água Do Motor Para Amarok 2.0 16v 2010/... Preto | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.771,88 | 9 | 9 |
| MLB5298371120 | N/D | Jogo Aneis 0,60 147 Uno Fiorino Premio 1.0 1.3 1.5 8v 84/95 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.755,24 | 11 | 11 |
| MLB4430273829 | N/D | Kit Jg Pistao E Aneis Bravo Doblo Idea Linea 1.8 16v E-torq 0,40mm | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.744,36 | 3 | 3 |
| MLB4404425007 | N/D | Par Disco De Freio Dianteiro Para Volare V6 6000 2004 À 2012 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.730,96 | 3 | 3 |
| MLB3871363101 | N/D | Junta Cabeçote Aço Inox Onix Plus Ecotec 1.0 12v 19/24 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.725,79 | 9 | 9 |
| MLB5663268708 | N/D | Tambor Campana Freio Traseira Fusca 4 Furos C/cubo Par | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.701,24 | 4 | 4 |
| MLB4614618825 | BOD20A | Bomba Oleo Sentra Novo 2.0 16v Flex 2013/2020 Mr20de | Takao | Bombas de Óleo | PARAMETRO_NAO_CONFIAVEL | R$ 1.660,74 | 2 | 2 |
| MLB4527961467 | N/D | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.659,56 | 3 | 3 |
| MLB6143573326 | N/D | Jogo Junta Cabeçote Azera Santa Fé Sorento 3.3 08/21 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.654,53 | 3 | 3 |
| MLB4404424995 | N/D | Par De Disco De Freio Dianteiro Sprinter 313 413 2002 À 2006 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.652,34 | 5 | 5 |
| MLB6079848988 | N/D | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 Std | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.647,90 | 3 | 3 |
| MLB5762363874 | N/D | Bomba De Água Takao Isuzu Gmc 7.110 4.3 8v 4hf1 Sohc | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.640,88 | 4 | 4 |
| MLB5410746906 | N/D | Molas Eibach Pro-kit Gm Astra \| Vectra Sedan - Gt 2.0 Mec | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.636,58 | 1 | 1 |
| MLB4604064777 | 1515165PK30 | Junta Cabeçote Sob Medida 2,6mm C2 C3 205 206 207 1.4 8v | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.535,64 | 7 | 15 |
| MLB6143663810 | N/D | Par Disco Freio Dianteiro Gm Tracker 1.2 2020 2021 2022 2023 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.503,61 | 3 | 3 |
| MLB6143754498 | N/D | Par Disco Freio Traseiro Renault Megane 2.0 16v 2006/2009 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.421,93 | 3 | 3 |
| MLB4249797695 | N/D | Par Disco Freio Dianteiro Pt Cruiser 2001 A 2010 2.0 2.4 16v | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.418,59 | 3 | 3 |
| MLB6087179454 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 0,50mm | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.417,94 | 3 | 3 |
| MLB5416245032 | N/D | Par Disco Freio Traseiro Renault Master 2.3 2013 A 2018 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 1.305,93 | 3 | 3 |
| MLB6505840046 | N/D | Reservatório De Água 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.179,39 | 12 | 12 |
| MLB5752064294 | N/D | Engate Reboque Fixo Captiva 2008 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.175,24 | 2 | 2 |
| MLB4480143025 | N/D | Kit Valvula Admissao E Escape Clio Sandero Logan 1.0 16v D4d | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.165,95 | 3 | 3 |
| MLB6263822942 | VADCH27 - VESCH27 | Kit Válvula Admissão (12) E Escape (12) Dodge 2.7 Journey V6 | Takao | Válvulas | PARAMETRO_NAO_CONFIAVEL | R$ 1.118,40 | 1 | 1 |
| MLB4381396847 | N/D | Jogo Pistao Com Aneis Palio 1.0 8v Fiasa 1996 A 2001 Takao Std | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.093,88 | 2 | 2 |
| MLB6611130078 | 131545PK30 | Junta Cabeçote Sob Medida 3mm Fiesta Ka 1.0 8v Zetec Rocam | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.049,08 | 12 | 12 |
| MLB4604567493 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.014,55 | 10 | 10 |
| MLB4506609417 | T-152 | Polia Do Virabrequim C/damper - Hilux 3.0 - T-152 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 1.009,57 | 1 | 1 |
| MLB5771134578 | N/D | Junta Comp C/ Retentores (jg) Tiggo 7 1.5 16v 2017 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.006,75 | 1 | 1 |
| MLB4404893661 | N/D | Jogo Junta Cabeçote Sentra Tiida Versa Fluence 1.8 2.0 06/19 | N/D | N/D | SEM_MATCH_SECONDS | R$ 998,77 | 4 | 5 |
| MLB4604058035 | 131547PK30 | Junta Cabeçote Sob Medida Ford Ecosport 1.6 8v Zetec Rocam | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 994,95 | 12 | 12 |
| MLB4209329255 | N/D | Pastilha Freio Sprinter 416 Cdi 2.2 16v 2019 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 994,18 | 4 | 4 |
| MLB4573497959 | N/D | Jogo Pistao 0,50 Onix Novo 1.0 8v 2017 A 2022 | N/D | N/D | SEM_MATCH_SECONDS | R$ 953,17 | 2 | 2 |
| MLB5751965116 | N/D | Engate Reboque Removível Veloster 2012 A 2018 | N/D | N/D | SEM_MATCH_SECONDS | R$ 907,33 | 1 | 1 |
| MLB4249774981 | N/D | Par Tambor Freio Traseiro Renault Duster 4x2 2.0 16v 2013 | N/D | N/D | SEM_MATCH_SECONDS | R$ 905,19 | 3 | 3 |
| MLB5420585658 | N/D | Par Disco Freio Dianteiro Peugeot 106/206/207/306 Xsara 8v | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 874,45 | 4 | 4 |
| MLB4445866853 | 33-5111 | Filtro Ar K&n 33-5111 Mini Cooper Jcw Countryman 2.0 / 2020 | K&N | Filtros de Ar | PARAMETRO_NAO_CONFIAVEL | R$ 870,21 | 1 | 1 |
| MLB6143572624 | N/D | Par Disco De Freio Dianteiro L200 Triton 3.2 2008 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 863,59 | 2 | 2 |
| MLB5016446608 | N/D | Junta Carter Borracha  Celta Corsa 1.0 1.6 8v Mpfi Efi | N/D | N/D | SEM_MATCH_SECONDS | R$ 850,54 | 20 | 20 |
| MLB6153696204 | N/D | Engate Reboque Outlander 2025 2026 700kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 825,84 | 1 | 1 |
| MLB5420752296 | N/D | Par Tambor Freio Montana 1.4 1.8 2004 05 06 07 08 09 10 Mds | MDS | Tambor | SEM_MATCH_SECONDS | R$ 802,92 | 3 | 3 |
| MLB5376155402 | Ad1007 | Engate Rabicho Reboque Removivel 700kg Audi Q3 2020 A 2024 Preto | Brucke | CARGA MANUAL SP_Profit_Large | PARAMETRO_NAO_CONFIAVEL | R$ 795,47 | 1 | 1 |
| MLB4196605661 | N/D | Engate Reboque Removível Audi A5 2011 Até 2017 700kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 766,14 | 1 | 1 |
| MLB4597608581 | T-607 | Polia Virabrequim Corsa Celta 94 Em Diante | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 763,22 | 2 | 2 |
| MLB4665291183 | GPSFO021 | Trocador De Calor Dodge Journey Cherokee 3.6 V6 Aluminio | Greenparts | Radiadores de Óleo | PARAMETRO_NAO_CONFIAVEL | R$ 755,21 | 1 | 1 |
| MLB6263914136 | VADCY13 - VESCY13 | Kit Válvulas Escape + Admissão Takao Chery Face 1.3 16v Gas | Takao | Válvulas | PARAMETRO_NAO_CONFIAVEL | R$ 750,11 | 1 | 1 |
| MLB4229902627 | N/D | Engate Reboque Fixo Master 2014 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 721,61 | 1 | 1 |
| MLB4419938395 | N/D | Pastilha De Freio Brembo Dianteira Up Tsi 1.0t 105hp P85041 | N/D | N/D | SEM_MATCH_SECONDS | R$ 720,96 | 2 | 2 |
| MLB6263889872 | N/D | Kit Valvula Admissao E Escape Gol G4 G5 G6 Fox 1.6 8v Ea111 | N/D | N/D | SEM_MATCH_SECONDS | R$ 711,40 | 2 | 3 |
| MLB4604036071 | 141233PK | Junta Superior Cabeçote Palio Siena Brava 1.6 16v 95/00 | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 704,34 | 6 | 6 |
| MLB4228800975 | N/D | Engate Reboque Removível Ducato Boxer Jumper 2019 A 2024 | N/D | N/D | SEM_MATCH_SECONDS | R$ 656,41 | 1 | 1 |
| MLB5016360610 | 111953CBL | Junta Carter Cortiça Fox Gol Voyage Parati 1.0 8/16v Ea111 | Bastos Juntas | Juntas | SEM_MATCH_SECONDS | R$ 651,53 | 18 | 18 |
| MLB4045987807 | VW5004 | Engate Fixo Saveiro G5 G6 G7 G8 G9 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 633,38 | 1 | 1 |
| MLB6171623388 | N/D | Jogo Anéis Motor Stander Parati Gol Saveiro Ap 1.6 1.8 8v | N/D | N/D | SEM_MATCH_SECONDS | R$ 626,09 | 4 | 4 |
| MLB6612401208 | N/D | Junta Cabeçote Aço Inox Onix Plus Ecotec 1.0 12v 19/24 | N/D | N/D | SEM_MATCH_SECONDS | R$ 606,01 | 3 | 3 |
| MLB5298316606 | BCH18A/STD | Jogo Bronzina Mancal Std Cr-v Civic Hr-v 1.8 2.0 16v  06/20 | Takao | Bronzinas | PARAMETRO_NAO_CONFIAVEL | R$ 598,14 | 3 | 3 |
| MLB5686798932 | 379216SP | Kit Amortecedor Traseiro, Fiat Uno Way 1.4 2015 | MONROE,REVIAM | Kits Completos Amortecedores | PARAMETRO_NAO_CONFIAVEL | R$ 580,00 | 1 | 1 |
| MLB5716939928 | N/D | Pastilha Freio Mini Countryman Cooper S All4 2016 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 575,02 | 3 | 3 |
| MLB4229915339 | N/D | Engate Reboque Fixo Megane Grand Tour X-tr 2010 A 2012 | N/D | N/D | SEM_MATCH_SECONDS | R$ 573,17 | 1 | 1 |
| MLB4345296599 | N/D | Bronzina Mancal Ford Novo Ka New Fiesta 1.5 16v Sigma | N/D | N/D | SEM_MATCH_SECONDS | R$ 570,29 | 3 | 3 |
| MLB4604099641 | 141029PK | Jogo Junta Motor Palio Uno Siena Strada Fiasa 96/04 | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 563,69 | 5 | 5 |
| MLB6143703260 | N/D | Junta Superior Cabeçote Civic 1.6 16v 95/00 | N/D | N/D | SEM_MATCH_SECONDS | R$ 559,93 | 2 | 2 |
| MLB4043416789 | N/D | Engate Fixo Kombi 1997 A 2005 | N/D | N/D | SEM_MATCH_SECONDS | R$ 555,64 | 1 | 1 |
| MLB4506283343 | T-64 | Polia Do Virabrequim - Damper - Opala 4 E 6 Cc 1987... | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 546,94 | 1 | 1 |
| MLB4229128117 | GM3013 | Engate Reboque Fixo Cruze Hatch 2012 A 2016 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 532,24 | 1 | 1 |
| MLB5791136854 | N/D | Par Tambor Freio Traseiro Chevrolet S10 4x2 2021 2022 | N/D | N/D | SEM_MATCH_SECONDS | R$ 530,75 | 1 | 1 |
| MLB4505545503 | T-474 | Polia Do Virabrequim C/damper - Sandero Il Rs/duster/ T-474 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 526,05 | 1 | 1 |
| MLB5365850434 | FO2018 | Engate Fixo Focus Sedan Hatch 2009 A 2013 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 518,87 | 1 | 1 |
| MLB5298213144 | N/D | Jogo Pistão 1,00 Fielder Corolla X60 1.8 16v 02/18 | N/D | N/D | SEM_MATCH_SECONDS | R$ 518,30 | 1 | 1 |
| MLB6230829704 | N/D | Junta Tampa Válvulas Focus 2014-2019 2.0 Duratec Direct Flex | N/D | N/D | SEM_MATCH_SECONDS | R$ 517,87 | 4 | 4 |

## 4. Impacto financeiro por motivo

| Motivo | Pedidos | Receita | Participacao |
| --- | --- | --- | --- |
| SEM_MATCH_SECONDS | 624 | R$ 155.311,42 | 74,07% |
| PARAMETRO_NAO_CONFIAVEL | 212 | R$ 54.360,30 | 25,93% |

## 5. Cobertura por marca

| Marca | receita_total | receita_sem_cmv | pct_sem_cmv |
| --- | --- | --- | --- |
| N/D | R$ 131.494,39 | R$ 131.494,39 | 100,00% |
| MDS | R$ 74.773,92 | R$ 18.336,42 | 24,52% |
| Bastos Juntas | R$ 541.927,84 | R$ 16.756,79 | 3,09% |
| Triade | R$ 56.672,16 | R$ 11.311,35 | 19,96% |
| Takao | R$ 322.705,42 | R$ 10.170,64 | 3,15% |
| Eibach | R$ 68.525,29 | R$ 6.652,00 | 9,71% |
| Brucke | R$ 182.755,22 | R$ 4.430,14 | 2,42% |
| OriginALLparts | R$ 260.095,93 | R$ 3.791,51 | 1,46% |
| K&N | R$ 14.267,06 | R$ 2.940,57 | 20,61% |
| Greenparts | R$ 46.036,67 | R$ 755,21 | 1,64% |
| Mann Filter | R$ 782,27 | R$ 676,92 | 86,53% |
| Ecoflex | R$ 98.928,83 | R$ 642,58 | 0,65% |
| MONROE,REVIAM | R$ 580,00 | R$ 580,00 | 100,00% |
| Sampel | R$ 316,54 | R$ 316,54 | 100,00% |
| Indisa | R$ 575,77 | R$ 259,30 | 45,04% |
| TAKAO | R$ 215,81 | R$ 215,81 | 100,00% |
| Perfect | R$ 3.873,57 | R$ 198,89 | 5,13% |
| Ecopads | R$ 2.922,76 | R$ 112,62 | 3,85% |
| SYL | R$ 30,04 | R$ 30,04 | 100,00% |
| Basto Juntas | R$ 1.998,19 | R$ 0,00 | 0,00% |
| Autotec | R$ 934,59 | R$ 0,00 | 0,00% |
| Brembo | R$ 5.270,12 | R$ 0,00 | 0,00% |
| Bastos | R$ 451,52 | R$ 0,00 | 0,00% |
| Igasa | R$ 20.154,92 | R$ 0,00 | 0,00% |
| Iveco | R$ 9.094,98 | R$ 0,00 | 0,00% |
| DriveTec | R$ 3.072,99 | R$ 0,00 | 0,00% |
| FQ4 | R$ 487,67 | R$ 0,00 | 0,00% |
| FQ4 Moto Original | R$ 42,78 | R$ 0,00 | 0,00% |
| Frontier | R$ 6.387,77 | R$ 0,00 | 0,00% |
| Magneti Marelli | R$ 298,90 | R$ 0,00 | 0,00% |

## 6. Cobertura por categoria

| Categoria | receita_total | receita_sem_cmv | pct_sem_cmv |
| --- | --- | --- | --- |
| N/D | R$ 131.494,39 | R$ 131.494,39 | 100,00% |
| Juntas de Motor | R$ 537.120,57 | R$ 16.731,36 | 3,12% |
| Disco de Freios | R$ 56.279,11 | R$ 13.627,03 | 24,21% |
| Polia de Virabrequim | R$ 55.187,42 | R$ 10.716,08 | 19,42% |
| Molas | R$ 57.549,29 | R$ 6.652,00 | 11,56% |
| Tambor | R$ 13.461,54 | R$ 4.709,39 | 34,98% |
| Pastilhas de Freios | R$ 268.318,85 | R$ 3.934,17 | 1,47% |
| Válvulas | R$ 41.287,23 | R$ 3.640,50 | 8,82% |
| Engate | R$ 164.992,15 | R$ 3.634,67 | 2,20% |
| Filtros de Ar | R$ 13.773,44 | R$ 3.092,31 | 22,45% |
| Bronzinas | R$ 21.799,34 | R$ 2.270,93 | 10,42% |
| Bombas de Óleo | R$ 38.326,55 | R$ 1.660,74 | 4,33% |
| Pistão | R$ 157.921,04 | R$ 1.308,71 | 0,83% |
| CARGA MANUAL SP_Profit_Large | R$ 61.606,95 | R$ 795,47 | 1,29% |
| Radiadores de Óleo | R$ 17.939,72 | R$ 755,21 | 4,21% |
| Juntas | R$ 651,53 | R$ 651,53 | 100,00% |
| Calhas | R$ 98.928,83 | R$ 642,58 | 0,65% |
| Kits Completos Amortecedores | R$ 580,00 | R$ 580,00 | 100,00% |
| Kits de Pistãos e Camisas | R$ 14.855,78 | R$ 506,22 | 3,41% |
| Polias para Bombas de Água | R$ 1.057,51 | R$ 472,22 | 44,65% |
| Filtros de Combustível | R$ 330,28 | R$ 330,28 | 100,00% |
| Bombas de Água | R$ 54.010,62 | R$ 259,30 | 0,48% |
| Parafusos do Cilindro | R$ 5.970,30 | R$ 198,34 | 3,32% |
| Coxins de Motor | R$ 190,04 | R$ 190,04 | 100,00% |
| Jogo de Anéis Motor | R$ 14.079,81 | R$ 174,91 | 1,24% |
| Kit de Filtros | R$ 250,94 | R$ 142,04 | 56,60% |
| Coxim de Motor | R$ 126,50 | R$ 126,50 | 100,00% |
| Polias do Alternador | R$ 273,96 | R$ 123,05 | 44,92% |
| Terminal Ponteira de Direção | R$ 222,77 | R$ 121,31 | 54,46% |
| Pivô Balança Bandeja | R$ 77,58 | R$ 77,58 | 100,00% |

## 7. Ganho potencial ao corrigir

| Cenario | Pedidos recuperados | Receita recuperada | Cobertura pedidos apos correcao | Cobertura receita apos correcao | Receita sem CMV remanescente |
| --- | --- | --- | --- | --- | --- |
| Corrigir Top 20 | 275 | R$ 80.443,37 | 95,23% | 93,83% | R$ 129.228,35 |
| Corrigir Top 50 | 423 | R$ 133.173,75 | 96,49% | 96,35% | R$ 76.497,97 |
| Corrigir Top 100 | 585 | R$ 170.777,09 | 97,87% | 98,14% | R$ 38.894,63 |

## 8. Plano recomendado para atingir 99%+

1. Corrigir primeiro os itens do `top_100_sem_cmv.csv`, priorizando a ordem por `receita_total`.
2. Para `SEM_MATCH_SECONDS`, cadastrar ou ajustar o `item_id` MLB na base de parametros da Seconds.
3. Para `PARAMETRO_NAO_CONFIAVEL`, revisar o parametro financeiro e marcar como confiavel apenas apos validar CMV, frete, imposto, comissao e custo fixo.
4. Para `CMV_ZERADO` ou `CMV_NULO`, preencher CMV unitario real e regenerar `parametros_financeiros_seconds.csv`.
5. Rodar novamente a consolidacao e esta auditoria ate a cobertura de pedidos e receita ficar acima de 99%.

## 9. Observacoes de controle

Nenhuma regra financeira, DRE, merge ou calculo foi alterado por esta auditoria. Os arquivos CSV sao listas operacionais para correcao cadastral/parametrica na Seconds.
=======
# Auditoria 3 - Itens sem CMV confiavel

## 1. Resumo executivo

Base auditada: `data\dashboard_base_final.csv`.

Pedidos totais: **11.765**  
Pedidos com CMV valido: **10.929**  
Pedidos sem CMV valido: **836**  
Cobertura CMV atual: **92,89%**  
Receita sem CMV valido: **R$ 209.671,72**

Foram identificados **273 itens/item_id** com algum problema de CMV confiavel. A lista operacional foi gravada em:

- `resultado\itens_sem_cmv_completo.csv`
- `resultado\top_100_sem_cmv.csv`

## 2. Top 20 produtos mais criticos

| item_id | sku | produto | marca | categoria | motivo_sem_cmv | receita_total | pedidos | unidades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLB4411222171 | N/D | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 11.896,82 | 16 | 16 |
| MLB5148208414 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 8.480,47 | 82 | 82 |
| MLB4096955407 | N/D | Jogo Pastilha Dianteira Freelander 2 2007 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 7.625,09 | 32 | 33 |
| MLB4096861467 | N/D | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 5.310,35 | 18 | 18 |
| MLB4445439489 | N/D | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.911,08 | 2 | 4 |
| MLB6415815014 | T-508 | Polia Do Virabrequim C/damper - Amarok 3.0 Tdi V6 - T-508 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 3.596,77 | 1 | 1 |
| MLB6171701742 | N/D | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.504,57 | 2 | 3 |
| MLB4576053479 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.274,78 | 7 | 7 |
| MLB6520374496 | N/D | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.163,68 | 14 | 20 |
| MLB4449446401 | N/D | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.127,82 | 4 | 4 |
| MLB5376377560 | N/D | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.113,92 | 4 | 4 |
| MLB4604743131 | 131590ML2 | Junta Cabeçote Sob Medida 1.20mm Ka Ka+ New Fiesta | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 3.059,52 | 10 | 10 |
| MLB5755208526 | N/D | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.481,59 | 1 | 1 |
| MLB4084143565 | N/D | Par Disco Freio Dianteiro Ipanema 1.8 2.0 8v 1989 Até 1998 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.469,51 | 13 | 13 |
| MLB5416066620 | N/D | Par Disco De Freio Tras Astra Meriva Vectra 1.8 2.0 2.2 2.4 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.464,42 | 6 | 7 |
| MLB4087894455 | N/D | Par Disco Freio Dianteiro Tiida Livina D921 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.427,26 | 8 | 8 |
| MLB4053750901 | N/D | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.375,92 | 1 | 1 |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.364,00 | 1 | 1 |
| MLB6505840046 | N/D | Reservatório De Água Peugeot 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.330,57 | 24 | 24 |
| MLB4604035479 | 1212136PK | Junta Superior Cabeçote Corsa Prisma Montana Ohc 1.4 06/.. | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 2.285,84 | 17 | 18 |

## 3. Top 100 por receita

| item_id | sku | produto | marca | categoria | motivo_sem_cmv | receita_total | pedidos | unidades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MLB4411222171 | N/D | Engate Reboque Gwm Poer 2025 2026 2100kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 11.896,82 | 16 | 16 |
| MLB5148208414 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 8.480,47 | 82 | 82 |
| MLB4096955407 | N/D | Jogo Pastilha Dianteira Freelander 2 2007 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 7.625,09 | 32 | 33 |
| MLB4096861467 | N/D | Pastilha Freio Dianteira Suzuki Vitara / S-cross Após 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 5.310,35 | 18 | 18 |
| MLB4445439489 | N/D | Filtro Ar K&n - Mercedes C63 C 63 Amg / S / 4.0 / 2016 2017 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.911,08 | 2 | 4 |
| MLB6415815014 | T-508 | Polia Do Virabrequim C/damper - Amarok 3.0 Tdi V6 - T-508 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 3.596,77 | 1 | 1 |
| MLB6171701742 | N/D | Filtro Ar K&n E-0660 - Porsche Macan 2.0 / 3.0 / 3.6 / 2014+ | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.504,57 | 2 | 3 |
| MLB4576053479 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.274,78 | 7 | 7 |
| MLB6520374496 | N/D | Biela Motor Chevrolet Cruze 1.8 16v 2012 Até 2016 Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.163,68 | 14 | 20 |
| MLB4449446401 | N/D | Jogo Pistao 0,50 Toro Tigershark 2.4 16v 2016 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.127,82 | 4 | 4 |
| MLB5376377560 | N/D | Ponteira De Engate Maciça Ranger 2024/2025 Removível 3500kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 3.113,92 | 4 | 4 |
| MLB4604743131 | 131590ML2 | Junta Cabeçote Sob Medida 1.20mm Ka Ka+ New Fiesta | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 3.059,52 | 10 | 10 |
| MLB5755208526 | N/D | Engate Reboque Removível Xtreme Hilux 2005 A 2025 | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.481,59 | 1 | 1 |
| MLB4084143565 | N/D | Par Disco Freio Dianteiro Ipanema 1.8 2.0 8v 1989 Até 1998 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.469,51 | 13 | 13 |
| MLB5416066620 | N/D | Par Disco De Freio Tras Astra Meriva Vectra 1.8 2.0 2.2 2.4 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.464,42 | 6 | 7 |
| MLB4087894455 | N/D | Par Disco Freio Dianteiro Tiida Livina D921 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.427,26 | 8 | 8 |
| MLB4053750901 | N/D | Engate Rabicho L200 Triton 2017 2018 2019 Remov 5000 Kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.375,92 | 1 | 1 |
| MLB5410760486 | N/D | Molas Eibach Pro-kit Ford Fusion 2.0 Ecoboost Fwd Awd 2013+ | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.364,00 | 1 | 1 |
| MLB6505840046 | N/D | Reservatório De Água Peugeot 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.330,57 | 24 | 24 |
| MLB4604035479 | 1212136PK | Junta Superior Cabeçote Corsa Prisma Montana Ohc 1.4 06/.. | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 2.285,84 | 17 | 18 |
| MLB4084541091 | N/D | Par Disco Freio Dian Corolla 1.8 16v 08 A 13 2.0 16v 10 A 13 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 2.275,96 | 6 | 6 |
| MLB4080244565 | N/D | Molas Esportivas Pro-kit Eibach Mercedes C180 C200 C250 W204 | Eibach | Molas | SEM_MATCH_SECONDS | R$ 2.245,00 | 1 | 1 |
| MLB5420786736 | N/D | Par Tambor Freio Traseiro Corsa 1.0 1.4 1.8 Frente Montana | MDS | Tambor | SEM_MATCH_SECONDS | R$ 2.098,65 | 6 | 6 |
| MLB5771132650 | N/D | Jogo Junta Completo Fiesta 1.0 8v Zetec Rocam Gasolina | N/D | N/D | SEM_MATCH_SECONDS | R$ 2.088,35 | 9 | 9 |
| MLB6407948012 | T-431 | Polia Do Virabrequim Damper - Gran Blazer - Ford:bg1t6312-ba | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 2.079,92 | 1 | 1 |
| MLB6171701834 | 33-3153 | Filtro De Ar K&n Porsche 911 (992 E 991.2) 2019+  Kit C/2 | K&N | Filtros de Ar | PARAMETRO_NAO_CONFIAVEL | R$ 2.070,36 | 1 | 1 |
| MLB5410454620 | CE10-40-036-07-22 | Mola Eibach Pro-kit Honda Civic 10 X 1.5 T \| 2.0 Flex 2017+ | Eibach | Molas | PARAMETRO_NAO_CONFIAVEL | R$ 2.043,00 | 1 | 1 |
| MLB4482750235 | N/D | Kit Válvula Admissão E Escape Cruze Tracker 1.8 16v Ecotec | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.843,94 | 3 | 3 |
| MLB5420670994 | N/D | Par Disco De Freio Dianteiro Sólido Kwid 1.0 2017 2018 2019 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 1.809,50 | 8 | 8 |
| MLB4087944673 | N/D | Par Tambor De Freio Traseiro Ford Ka 1.0 1.3 1.6 1997 A 2014 | MDS | Tambor | SEM_MATCH_SECONDS | R$ 1.807,82 | 5 | 5 |
| MLB6611111530 | 141229PK | Junta Superior Cabeçote Palio Siena Uno Fiasa 96/... | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.782,24 | 25 | 27 |
| MLB6502062310 | N/D | Cano Duplo De Água Do Motor Para Amarok 2.0 16v 2010/... Preto | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.771,88 | 9 | 9 |
| MLB5298371120 | N/D | Jogo Aneis 0,60 147 Uno Fiorino Premio 1.0 1.3 1.5 8v 84/95 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.755,24 | 11 | 11 |
| MLB4430273829 | N/D | Kit Jg Pistao E Aneis Bravo Doblo Idea Linea 1.8 16v E-torq 0,40mm | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.744,36 | 3 | 3 |
| MLB4404425007 | N/D | Par Disco De Freio Dianteiro Para Volare V6 6000 2004 À 2012 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.730,96 | 3 | 3 |
| MLB3871363101 | N/D | Junta Cabeçote Aço Inox Onix Plus Ecotec 1.0 12v 19/24 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.725,79 | 9 | 9 |
| MLB5663268708 | N/D | Tambor Campana Freio Traseira Fusca 4 Furos C/cubo Par | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.701,24 | 4 | 4 |
| MLB4614618825 | BOD20A | Bomba Oleo Sentra Novo 2.0 16v Flex 2013/2020 Mr20de | Takao | Bombas de Óleo | PARAMETRO_NAO_CONFIAVEL | R$ 1.660,74 | 2 | 2 |
| MLB4527961467 | N/D | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.659,56 | 3 | 3 |
| MLB6143573326 | N/D | Jogo Junta Cabeçote Azera Santa Fé Sorento 3.3 08/21 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.654,53 | 3 | 3 |
| MLB4404424995 | N/D | Par De Disco De Freio Dianteiro Sprinter 313 413 2002 À 2006 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.652,34 | 5 | 5 |
| MLB6079848988 | N/D | Jogo Pistao Com Aneis Gm Cruze 1.8 16v Ecotec 2011 A 2016 Std | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.647,90 | 3 | 3 |
| MLB5762363874 | N/D | Bomba De Água Takao Isuzu Gmc 7.110 4.3 8v 4hf1 Sohc | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.640,88 | 4 | 4 |
| MLB5410746906 | N/D | Molas Eibach Pro-kit Gm Astra \| Vectra Sedan - Gt 2.0 Mec | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.636,58 | 1 | 1 |
| MLB4604064777 | 1515165PK30 | Junta Cabeçote Sob Medida 2,6mm C2 C3 205 206 207 1.4 8v | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.535,64 | 7 | 15 |
| MLB6143663810 | N/D | Par Disco Freio Dianteiro Gm Tracker 1.2 2020 2021 2022 2023 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.503,61 | 3 | 3 |
| MLB6143754498 | N/D | Par Disco Freio Traseiro Renault Megane 2.0 16v 2006/2009 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.421,93 | 3 | 3 |
| MLB4249797695 | N/D | Par Disco Freio Dianteiro Pt Cruiser 2001 A 2010 2.0 2.4 16v | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.418,59 | 3 | 3 |
| MLB6087179454 | N/D | Jogo Pistao C/ Aneis Gol G5 G6 Voyage Fox 1.0 8v 2008 A 2016 0,50mm | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.417,94 | 3 | 3 |
| MLB5416245032 | N/D | Par Disco Freio Traseiro Renault Master 2.3 2013 A 2018 | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 1.305,93 | 3 | 3 |
| MLB6505840046 | N/D | Reservatório De Água 206 207 1.4 1.6 16v Com Tampa | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.179,39 | 12 | 12 |
| MLB5752064294 | N/D | Engate Reboque Fixo Captiva 2008 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.175,24 | 2 | 2 |
| MLB4480143025 | N/D | Kit Valvula Admissao E Escape Clio Sandero Logan 1.0 16v D4d | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.165,95 | 3 | 3 |
| MLB6263822942 | VADCH27 - VESCH27 | Kit Válvula Admissão (12) E Escape (12) Dodge 2.7 Journey V6 | Takao | Válvulas | PARAMETRO_NAO_CONFIAVEL | R$ 1.118,40 | 1 | 1 |
| MLB4381396847 | N/D | Jogo Pistao Com Aneis Palio 1.0 8v Fiasa 1996 A 2001 Takao Std | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.093,88 | 2 | 2 |
| MLB6611130078 | 131545PK30 | Junta Cabeçote Sob Medida 3mm Fiesta Ka 1.0 8v Zetec Rocam | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 1.049,08 | 12 | 12 |
| MLB4604567493 | N/D | Junta Superior Cabeçote Apolo Gol Logus Mi Ap 1.6 1.8 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.014,55 | 10 | 10 |
| MLB4506609417 | T-152 | Polia Do Virabrequim C/damper - Hilux 3.0 - T-152 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 1.009,57 | 1 | 1 |
| MLB5771134578 | N/D | Junta Comp C/ Retentores (jg) Tiggo 7 1.5 16v 2017 A 2020 | N/D | N/D | SEM_MATCH_SECONDS | R$ 1.006,75 | 1 | 1 |
| MLB4404893661 | N/D | Jogo Junta Cabeçote Sentra Tiida Versa Fluence 1.8 2.0 06/19 | N/D | N/D | SEM_MATCH_SECONDS | R$ 998,77 | 4 | 5 |
| MLB4604058035 | 131547PK30 | Junta Cabeçote Sob Medida Ford Ecosport 1.6 8v Zetec Rocam | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 994,95 | 12 | 12 |
| MLB4209329255 | N/D | Pastilha Freio Sprinter 416 Cdi 2.2 16v 2019 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 994,18 | 4 | 4 |
| MLB4573497959 | N/D | Jogo Pistao 0,50 Onix Novo 1.0 8v 2017 A 2022 | N/D | N/D | SEM_MATCH_SECONDS | R$ 953,17 | 2 | 2 |
| MLB5751965116 | N/D | Engate Reboque Removível Veloster 2012 A 2018 | N/D | N/D | SEM_MATCH_SECONDS | R$ 907,33 | 1 | 1 |
| MLB4249774981 | N/D | Par Tambor Freio Traseiro Renault Duster 4x2 2.0 16v 2013 | N/D | N/D | SEM_MATCH_SECONDS | R$ 905,19 | 3 | 3 |
| MLB5420585658 | N/D | Par Disco Freio Dianteiro Peugeot 106/206/207/306 Xsara 8v | MDS | Disco de Freios | SEM_MATCH_SECONDS | R$ 874,45 | 4 | 4 |
| MLB4445866853 | 33-5111 | Filtro Ar K&n 33-5111 Mini Cooper Jcw Countryman 2.0 / 2020 | K&N | Filtros de Ar | PARAMETRO_NAO_CONFIAVEL | R$ 870,21 | 1 | 1 |
| MLB6143572624 | N/D | Par Disco De Freio Dianteiro L200 Triton 3.2 2008 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 863,59 | 2 | 2 |
| MLB5016446608 | N/D | Junta Carter Borracha  Celta Corsa 1.0 1.6 8v Mpfi Efi | N/D | N/D | SEM_MATCH_SECONDS | R$ 850,54 | 20 | 20 |
| MLB6153696204 | N/D | Engate Reboque Outlander 2025 2026 700kg Removível Completo | N/D | N/D | SEM_MATCH_SECONDS | R$ 825,84 | 1 | 1 |
| MLB5420752296 | N/D | Par Tambor Freio Montana 1.4 1.8 2004 05 06 07 08 09 10 Mds | MDS | Tambor | SEM_MATCH_SECONDS | R$ 802,92 | 3 | 3 |
| MLB5376155402 | Ad1007 | Engate Rabicho Reboque Removivel 700kg Audi Q3 2020 A 2024 Preto | Brucke | CARGA MANUAL SP_Profit_Large | PARAMETRO_NAO_CONFIAVEL | R$ 795,47 | 1 | 1 |
| MLB4196605661 | N/D | Engate Reboque Removível Audi A5 2011 Até 2017 700kg | N/D | N/D | SEM_MATCH_SECONDS | R$ 766,14 | 1 | 1 |
| MLB4597608581 | T-607 | Polia Virabrequim Corsa Celta 94 Em Diante | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 763,22 | 2 | 2 |
| MLB4665291183 | GPSFO021 | Trocador De Calor Dodge Journey Cherokee 3.6 V6 Aluminio | Greenparts | Radiadores de Óleo | PARAMETRO_NAO_CONFIAVEL | R$ 755,21 | 1 | 1 |
| MLB6263914136 | VADCY13 - VESCY13 | Kit Válvulas Escape + Admissão Takao Chery Face 1.3 16v Gas | Takao | Válvulas | PARAMETRO_NAO_CONFIAVEL | R$ 750,11 | 1 | 1 |
| MLB4229902627 | N/D | Engate Reboque Fixo Master 2014 A 2015 | N/D | N/D | SEM_MATCH_SECONDS | R$ 721,61 | 1 | 1 |
| MLB4419938395 | N/D | Pastilha De Freio Brembo Dianteira Up Tsi 1.0t 105hp P85041 | N/D | N/D | SEM_MATCH_SECONDS | R$ 720,96 | 2 | 2 |
| MLB6263889872 | N/D | Kit Valvula Admissao E Escape Gol G4 G5 G6 Fox 1.6 8v Ea111 | N/D | N/D | SEM_MATCH_SECONDS | R$ 711,40 | 2 | 3 |
| MLB4604036071 | 141233PK | Junta Superior Cabeçote Palio Siena Brava 1.6 16v 95/00 | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 704,34 | 6 | 6 |
| MLB4228800975 | N/D | Engate Reboque Removível Ducato Boxer Jumper 2019 A 2024 | N/D | N/D | SEM_MATCH_SECONDS | R$ 656,41 | 1 | 1 |
| MLB5016360610 | 111953CBL | Junta Carter Cortiça Fox Gol Voyage Parati 1.0 8/16v Ea111 | Bastos Juntas | Juntas | SEM_MATCH_SECONDS | R$ 651,53 | 18 | 18 |
| MLB4045987807 | VW5004 | Engate Fixo Saveiro G5 G6 G7 G8 G9 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 633,38 | 1 | 1 |
| MLB6171623388 | N/D | Jogo Anéis Motor Stander Parati Gol Saveiro Ap 1.6 1.8 8v | N/D | N/D | SEM_MATCH_SECONDS | R$ 626,09 | 4 | 4 |
| MLB6612401208 | N/D | Junta Cabeçote Aço Inox Onix Plus Ecotec 1.0 12v 19/24 | N/D | N/D | SEM_MATCH_SECONDS | R$ 606,01 | 3 | 3 |
| MLB5298316606 | BCH18A/STD | Jogo Bronzina Mancal Std Cr-v Civic Hr-v 1.8 2.0 16v  06/20 | Takao | Bronzinas | PARAMETRO_NAO_CONFIAVEL | R$ 598,14 | 3 | 3 |
| MLB5686798932 | 379216SP | Kit Amortecedor Traseiro, Fiat Uno Way 1.4 2015 | MONROE,REVIAM | Kits Completos Amortecedores | PARAMETRO_NAO_CONFIAVEL | R$ 580,00 | 1 | 1 |
| MLB5716939928 | N/D | Pastilha Freio Mini Countryman Cooper S All4 2016 Em Diante | N/D | N/D | SEM_MATCH_SECONDS | R$ 575,02 | 3 | 3 |
| MLB4229915339 | N/D | Engate Reboque Fixo Megane Grand Tour X-tr 2010 A 2012 | N/D | N/D | SEM_MATCH_SECONDS | R$ 573,17 | 1 | 1 |
| MLB4345296599 | N/D | Bronzina Mancal Ford Novo Ka New Fiesta 1.5 16v Sigma | N/D | N/D | SEM_MATCH_SECONDS | R$ 570,29 | 3 | 3 |
| MLB4604099641 | 141029PK | Jogo Junta Motor Palio Uno Siena Strada Fiasa 96/04 | Bastos Juntas | Juntas de Motor | PARAMETRO_NAO_CONFIAVEL | R$ 563,69 | 5 | 5 |
| MLB6143703260 | N/D | Junta Superior Cabeçote Civic 1.6 16v 95/00 | N/D | N/D | SEM_MATCH_SECONDS | R$ 559,93 | 2 | 2 |
| MLB4043416789 | N/D | Engate Fixo Kombi 1997 A 2005 | N/D | N/D | SEM_MATCH_SECONDS | R$ 555,64 | 1 | 1 |
| MLB4506283343 | T-64 | Polia Do Virabrequim - Damper - Opala 4 E 6 Cc 1987... | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 546,94 | 1 | 1 |
| MLB4229128117 | GM3013 | Engate Reboque Fixo Cruze Hatch 2012 A 2016 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 532,24 | 1 | 1 |
| MLB5791136854 | N/D | Par Tambor Freio Traseiro Chevrolet S10 4x2 2021 2022 | N/D | N/D | SEM_MATCH_SECONDS | R$ 530,75 | 1 | 1 |
| MLB4505545503 | T-474 | Polia Do Virabrequim C/damper - Sandero Il Rs/duster/ T-474 | Triade | Polia de Virabrequim | PARAMETRO_NAO_CONFIAVEL | R$ 526,05 | 1 | 1 |
| MLB5365850434 | FO2018 | Engate Fixo Focus Sedan Hatch 2009 A 2013 | Brucke | Engate | PARAMETRO_NAO_CONFIAVEL | R$ 518,87 | 1 | 1 |
| MLB5298213144 | N/D | Jogo Pistão 1,00 Fielder Corolla X60 1.8 16v 02/18 | N/D | N/D | SEM_MATCH_SECONDS | R$ 518,30 | 1 | 1 |
| MLB6230829704 | N/D | Junta Tampa Válvulas Focus 2014-2019 2.0 Duratec Direct Flex | N/D | N/D | SEM_MATCH_SECONDS | R$ 517,87 | 4 | 4 |

## 4. Impacto financeiro por motivo

| Motivo | Pedidos | Receita | Participacao |
| --- | --- | --- | --- |
| SEM_MATCH_SECONDS | 624 | R$ 155.311,42 | 74,07% |
| PARAMETRO_NAO_CONFIAVEL | 212 | R$ 54.360,30 | 25,93% |

## 5. Cobertura por marca

| Marca | receita_total | receita_sem_cmv | pct_sem_cmv |
| --- | --- | --- | --- |
| N/D | R$ 131.494,39 | R$ 131.494,39 | 100,00% |
| MDS | R$ 74.773,92 | R$ 18.336,42 | 24,52% |
| Bastos Juntas | R$ 541.927,84 | R$ 16.756,79 | 3,09% |
| Triade | R$ 56.672,16 | R$ 11.311,35 | 19,96% |
| Takao | R$ 322.705,42 | R$ 10.170,64 | 3,15% |
| Eibach | R$ 68.525,29 | R$ 6.652,00 | 9,71% |
| Brucke | R$ 182.755,22 | R$ 4.430,14 | 2,42% |
| OriginALLparts | R$ 260.095,93 | R$ 3.791,51 | 1,46% |
| K&N | R$ 14.267,06 | R$ 2.940,57 | 20,61% |
| Greenparts | R$ 46.036,67 | R$ 755,21 | 1,64% |
| Mann Filter | R$ 782,27 | R$ 676,92 | 86,53% |
| Ecoflex | R$ 98.928,83 | R$ 642,58 | 0,65% |
| MONROE,REVIAM | R$ 580,00 | R$ 580,00 | 100,00% |
| Sampel | R$ 316,54 | R$ 316,54 | 100,00% |
| Indisa | R$ 575,77 | R$ 259,30 | 45,04% |
| TAKAO | R$ 215,81 | R$ 215,81 | 100,00% |
| Perfect | R$ 3.873,57 | R$ 198,89 | 5,13% |
| Ecopads | R$ 2.922,76 | R$ 112,62 | 3,85% |
| SYL | R$ 30,04 | R$ 30,04 | 100,00% |
| Basto Juntas | R$ 1.998,19 | R$ 0,00 | 0,00% |
| Autotec | R$ 934,59 | R$ 0,00 | 0,00% |
| Brembo | R$ 5.270,12 | R$ 0,00 | 0,00% |
| Bastos | R$ 451,52 | R$ 0,00 | 0,00% |
| Igasa | R$ 20.154,92 | R$ 0,00 | 0,00% |
| Iveco | R$ 9.094,98 | R$ 0,00 | 0,00% |
| DriveTec | R$ 3.072,99 | R$ 0,00 | 0,00% |
| FQ4 | R$ 487,67 | R$ 0,00 | 0,00% |
| FQ4 Moto Original | R$ 42,78 | R$ 0,00 | 0,00% |
| Frontier | R$ 6.387,77 | R$ 0,00 | 0,00% |
| Magneti Marelli | R$ 298,90 | R$ 0,00 | 0,00% |

## 6. Cobertura por categoria

| Categoria | receita_total | receita_sem_cmv | pct_sem_cmv |
| --- | --- | --- | --- |
| N/D | R$ 131.494,39 | R$ 131.494,39 | 100,00% |
| Juntas de Motor | R$ 537.120,57 | R$ 16.731,36 | 3,12% |
| Disco de Freios | R$ 56.279,11 | R$ 13.627,03 | 24,21% |
| Polia de Virabrequim | R$ 55.187,42 | R$ 10.716,08 | 19,42% |
| Molas | R$ 57.549,29 | R$ 6.652,00 | 11,56% |
| Tambor | R$ 13.461,54 | R$ 4.709,39 | 34,98% |
| Pastilhas de Freios | R$ 268.318,85 | R$ 3.934,17 | 1,47% |
| Válvulas | R$ 41.287,23 | R$ 3.640,50 | 8,82% |
| Engate | R$ 164.992,15 | R$ 3.634,67 | 2,20% |
| Filtros de Ar | R$ 13.773,44 | R$ 3.092,31 | 22,45% |
| Bronzinas | R$ 21.799,34 | R$ 2.270,93 | 10,42% |
| Bombas de Óleo | R$ 38.326,55 | R$ 1.660,74 | 4,33% |
| Pistão | R$ 157.921,04 | R$ 1.308,71 | 0,83% |
| CARGA MANUAL SP_Profit_Large | R$ 61.606,95 | R$ 795,47 | 1,29% |
| Radiadores de Óleo | R$ 17.939,72 | R$ 755,21 | 4,21% |
| Juntas | R$ 651,53 | R$ 651,53 | 100,00% |
| Calhas | R$ 98.928,83 | R$ 642,58 | 0,65% |
| Kits Completos Amortecedores | R$ 580,00 | R$ 580,00 | 100,00% |
| Kits de Pistãos e Camisas | R$ 14.855,78 | R$ 506,22 | 3,41% |
| Polias para Bombas de Água | R$ 1.057,51 | R$ 472,22 | 44,65% |
| Filtros de Combustível | R$ 330,28 | R$ 330,28 | 100,00% |
| Bombas de Água | R$ 54.010,62 | R$ 259,30 | 0,48% |
| Parafusos do Cilindro | R$ 5.970,30 | R$ 198,34 | 3,32% |
| Coxins de Motor | R$ 190,04 | R$ 190,04 | 100,00% |
| Jogo de Anéis Motor | R$ 14.079,81 | R$ 174,91 | 1,24% |
| Kit de Filtros | R$ 250,94 | R$ 142,04 | 56,60% |
| Coxim de Motor | R$ 126,50 | R$ 126,50 | 100,00% |
| Polias do Alternador | R$ 273,96 | R$ 123,05 | 44,92% |
| Terminal Ponteira de Direção | R$ 222,77 | R$ 121,31 | 54,46% |
| Pivô Balança Bandeja | R$ 77,58 | R$ 77,58 | 100,00% |

## 7. Ganho potencial ao corrigir

| Cenario | Pedidos recuperados | Receita recuperada | Cobertura pedidos apos correcao | Cobertura receita apos correcao | Receita sem CMV remanescente |
| --- | --- | --- | --- | --- | --- |
| Corrigir Top 20 | 275 | R$ 80.443,37 | 95,23% | 93,83% | R$ 129.228,35 |
| Corrigir Top 50 | 423 | R$ 133.173,75 | 96,49% | 96,35% | R$ 76.497,97 |
| Corrigir Top 100 | 585 | R$ 170.777,09 | 97,87% | 98,14% | R$ 38.894,63 |

## 8. Plano recomendado para atingir 99%+

1. Corrigir primeiro os itens do `top_100_sem_cmv.csv`, priorizando a ordem por `receita_total`.
2. Para `SEM_MATCH_SECONDS`, cadastrar ou ajustar o `item_id` MLB na base de parametros da Seconds.
3. Para `PARAMETRO_NAO_CONFIAVEL`, revisar o parametro financeiro e marcar como confiavel apenas apos validar CMV, frete, imposto, comissao e custo fixo.
4. Para `CMV_ZERADO` ou `CMV_NULO`, preencher CMV unitario real e regenerar `parametros_financeiros_seconds.csv`.
5. Rodar novamente a consolidacao e esta auditoria ate a cobertura de pedidos e receita ficar acima de 99%.

## 9. Observacoes de controle

Nenhuma regra financeira, DRE, merge ou calculo foi alterado por esta auditoria. Os arquivos CSV sao listas operacionais para correcao cadastral/parametrica na Seconds.
>>>>>>> 4fc9cde76df43099c9e6324e589be74941777010
