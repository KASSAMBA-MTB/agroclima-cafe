# Evidência contextual — alerta meteorológico INMET — 2026-10-13

**Identificador da evidência:** EXT-INMET-20261013-TEMPESTADE-POCOS  
**Data de registro:** 2026-10-13  
**Tipo:** fonte externa oficial / aviso meteorológico  
**Estado no AgroClima Café:** registrado documentalmente; integração operacional não realizada nem homologada.

## Fonte primária

- **INMET — Avisos:** https://avisos.inmet.gov.br/56054
- **Página municipal que reproduz o aviso:** https://servicos.pocosdecaldas.mg.gov.br/alertas/meteorologicos/26-10-13-08-57/26-10-13-23-59/mapa/aviso-de-tempestade-com-grau-de-perigo-potencial
- **Publicação na página municipal:** 13/10/2026 às 09:00.
- **Última atualização exibida:** 13/10/2026 às 09:00.
- **Órgão/fonte indicado pela página municipal:** MAPA; o texto informa expressamente que o INMET publica o aviso.

## Conteúdo observado na fonte

- **Evento:** tempestade.
- **Severidade:** perigo potencial (amarelo).
- **Início da vigência:** 13/10/2026 às 08:57.
- **Fim da vigência:** 13/10/2026 às 23:59.
- **Chuva prevista:** 20–30 mm/h ou até 50 mm/dia.
- **Ventos previstos:** 40–60 km/h.
- **Fenômeno adicional:** possibilidade de queda de granizo.
- **Impactos potenciais descritos:** baixo risco de interrupção de energia, danos em plantações, queda de galhos e alagamentos.
- **Instruções publicadas:** evitar abrigo sob árvores durante rajadas, evitar aparelhos eletrônicos ligados à tomada e procurar Defesa Civil (199) ou Bombeiros (193) quando necessário.

## Abrangência geográfica e limite da evidência

O alerta foi localizado no portal de serviços de Poços de Caldas, MG. A solicitação que motivou este registro identifica o evento como abrangendo o Sul de Minas. A seção “Áreas Afetadas” da página consultada não apresentou a lista de localidades no conteúdo textual acessível nesta captura; portanto, este registro **não afirma** que cada um dos seis municípios monitorados pelo AgroClima Café esteja individualmente incluído no polígono oficial. A abrangência municipal exata deve ser lida na fonte oficial do INMET quando disponível.

## Tratamento correto no projeto

1. Classificar como **alerta/previsão externa**, não como observação meteorológica.
2. Preservar fonte, identificador/URL, horário de publicação/atualização, início/fim da vigência, severidade, fenômenos, valores previstos e texto original recuperado.
3. Não converter a previsão de chuva em precipitação observada.
4. Não registrar granizo como ocorrência confirmada.
5. Não inferir que os valores previstos ocorreram em qualquer município específico.
6. Não alterar automaticamente o FRI (Índice de Risco de Geada), limiares, regras homologadas, DashboardService, mapas, banco de dados ou fluxo operacional.
7. Manter este registro como documentação de evidência até existir contrato formal e revisão separada para ingestão de alertas externos.

## Texto da fonte preservado nesta captura

> INMET publica aviso iniciando em: 13/10/2026 08:57. Chuva entre 20 e 30 mm/h ou até 50 mm/dia, ventos intensos (40-60 km/h), e queda de granizo. Baixo risco de corte de energia elétrica, estragos em plantações, queda de galhos de árvores e de alagamentos.

**Nota de auditoria:** este arquivo documenta os campos que puderam ser verificados na página municipal e aponta explicitamente o limite da captura. Não substitui o registro integral/JSON da API do INMET, nem comprova ingestão no PostgreSQL, exibição no dashboard ou execução de testes.
