# Evidência contextual — alertas meteorológicos INMET — 2026-10-13

**Identificador da evidência:** EXT-INMET-20261013-TEMPESTADE-MG  
**Data de registro:** 2026-10-13  
**Tipo:** fonte externa oficial / aviso meteorológico  
**Estado no AgroClima Café:** registro documental em revisão; integração operacional não realizada nem homologada.

## Fontes verificadas

- **INMET — aviso de tempestade, perigo potencial:** https://avisos.inmet.gov.br/56048
- **INMET — painel geral de avisos:** https://avisos.inmet.gov.br/?lang=pt_BR
- **Contexto estadual e quantitativo municipal publicado em 12/10/2026:** https://agenciamg.com.br/2026/10/12/alerta-inmet-minas-gerais-12102026/
- **Página municipal inicialmente localizada:** https://servicos.pocosdecaldas.mg.gov.br/alertas/meteorologicos/26-10-13-08-57/26-10-13-23-59/mapa/aviso-de-tempestade-com-grau-de-perigo-potencial

## Aviso amarelo verificado

- **Evento:** tempestade.
- **Severidade:** perigo potencial (amarelo).
- **Vigência indicada pelo painel estadual:** 13/10/2026, de 00h a 23h.
- **Chuva prevista:** 20–30 mm/h ou até 50 mm/dia.
- **Ventos previstos:** 40–60 km/h.
- **Granizo:** possibilidade de queda.
- **Impactos potenciais:** baixo risco de interrupção de energia, danos em plantações, queda de galhos e alagamentos.
- **Abrangência regional reportada:** inclui Sul/Sudoeste de Minas.
- **Abrangência estadual reportada:** 337 municípios de Minas Gerais para este aviso amarelo, conforme notícia estadual publicada em 12/10/2026.

A página individual do INMET é uma aplicação JavaScript e o conteúdo de municípios não foi recuperado em texto por esta verificação. Portanto, não se afirma aqui que cada município monitorado pelo AgroClima Café esteja coberto pelo aviso amarelo; essa confirmação requer a lista municipal ou o polígono oficial do aviso.

## Atenção: há também um aviso laranja distinto

A notícia estadual de 12/10/2026 informa outro aviso de tempestade, **laranja (perigo)**, vigente em 13/10/2026 das 00h às 23h, abrangendo 41 municípios em regiões do Sul/Sudoeste de Minas. Esse aviso prevê chuva de 30–60 mm/h ou 50–100 mm/dia, ventos de 60–100 km/h e possibilidade de granizo. Não misturar esse aviso laranja com o aviso amarelo acima; são registros diferentes e devem ter identificadores, severidades e valores próprios.

## Tratamento correto no AgroClima Café

1. Classificar ambos como **alertas/previsões externas**, não como observações meteorológicas.
2. Preservar separadamente o identificador oficial, URL, órgão emissor, data/hora de emissão, início/fim da vigência, severidade, área abrangida, fenômenos, valores previstos e conteúdo original.
3. Não converter previsão de chuva em precipitação observada.
4. Não registrar granizo como ocorrência confirmada.
5. Não inferir que os valores previstos ocorreram em município específico.
6. Não alterar automaticamente FRI (Índice de Risco de Geada), limiares, regras homologadas, DashboardService, mapas, banco de dados ou fluxo operacional.
7. Manter o registro documental até existir contrato formal e revisão separada para ingestão de alertas externos.

## Texto do aviso amarelo preservado

> INMET publica aviso iniciando em: 13/10/2026 00:00. Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h), e queda de granizo. Baixo risco de corte de energia elétrica, estragos em plantações, queda de galhos de árvores e de alagamentos.

## Limites e rastreabilidade

Esta evidência combina a página oficial individual do INMET com informação estadual publicada sobre os avisos válidos em 13/10/2026. A página municipal inicialmente localizada não é usada isoladamente para definir o aviso oficial. A cópia textual integral/JSON da API e a confirmação do polígono municipal ainda não foram obtidas nesta revisão.

Este arquivo não comprova ingestão no PostgreSQL, exibição no dashboard, ocorrência real de granizo ou execução de testes.
