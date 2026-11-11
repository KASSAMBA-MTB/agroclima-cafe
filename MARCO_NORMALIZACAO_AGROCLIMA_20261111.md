# MARCO DE NORMALIZACAO AGROCLIMA - 11/11/2026

## 1. Referencia Git
- Branch: fix/hail-municipal-last-result-isolation
- Commit consolidado: d92a4ecd5685153a0e6b3ec7e0e130753f558fc9
- Sincronizacao local/remota: confirmada em 11/11/2026

## 2. Validacoes executadas
- Django System Check: aprovado.
- ORM classificacao experimental de granizo: 3 testes OK.
- Integracao Dashboard/Granizo: 18 testes OK.
- Total: 21 testes aprovados.

## 3. Estado do desenvolvimento
- Isolamento municipal dos resultados de granizo validado.
- Contrato hail_project_context preservado.
- Dados insuficientes permanecem sem classificacao.
- Painel Atmosfera apresenta avaliacao experimental sem classificacao operacional.
- Nenhuma homologacao cientifica ou operacional foi concedida.

## 4. Normalizacao
- Commit chore(normalize): consolidate agroclimate additions.
- 11 arquivos consolidados.
- 443 insercoes e 8 remocoes.
- Branch local e remota sincronizadas.

## 5. Pendencias locais preservadas
- Alteracao nao consolidada: dashboard/templates/dashboard/components/map_panel.html.
- Backups e pacotes experimentais preservados.
- Comando exportar_cobertura_iac.py duplicado em dashboard/management/commands permanece fora do commit.
- CSVs de pesquisa permanecem fora do commit.

## 6. Limitacao historica do IAC
A serie historica ainda nao possui cobertura suficiente para calcular integralmente o IAC.
Temperatura e precipitacao possuem dados; umidade, geada e granizo nao possuem cobertura historica adequada.
A ausencia de dados nao deve ser preenchida artificialmente.

## 7. Proximo ciclo
1. Retomar deste marco, sem repetir auditorias anteriores.
2. Definir e executar a implementacao historica do IAC com dados e cobertura verificaveis.
3. Preservar a arquitetura backend-authoritative.
4. Manter granizo experimental isolado de alertas, recomendacoes e classificacoes operacionais.
5. Avancar para validacao cientifica documentada, sem confundir testes de software com homologacao cientifica.

## 8. Regra de continuidade
Este documento e o ponto de partida oficial da retomada em 11/11/2026.
