# DOC-002 — PROJECT_CHARTER.md

**Projeto:** AgroClima Café

**Versão:** 1.0

**Documento:** DOC-002

**Data:** Junho de 2026

**Status:** Aprovado

**Autor:** Walter Junio Pontes Teixeira

**Curso:** Bacharelado em Ciência de Dados

**Instituição:** Universidade Virtual do Estado de São Paulo (UNIVESP)

---

# 1. Apresentação

O **AgroClima Café** é uma plataforma inteligente de monitoramento climático desenvolvida como Trabalho de Conclusão de Curso (TCC) do Bacharelado em Ciência de Dados da UNIVESP.

O projeto integra Engenharia de Software, Ciência de Dados, Banco de Dados, Visualização de Dados e Meteorologia, oferecendo uma solução capaz de coletar, armazenar, analisar e apresentar informações climáticas relevantes para a cafeicultura.

Seu desenvolvimento segue princípios de arquitetura de software, documentação contínua e evolução incremental.

---

# 2. Justificativa

A cafeicultura possui elevada dependência das condições climáticas.

Temperaturas extremas, geadas, precipitações e variações meteorológicas podem impactar significativamente a produtividade das lavouras.

Embora existam diversas fontes públicas de dados climáticos, essas informações normalmente encontram-se dispersas e pouco integradas.

O AgroClima Café surge como uma proposta para centralizar essas informações em uma plataforma única, disponibilizando indicadores e visualizações que apoiem a tomada de decisão.

---

# 3. Problema

Produtores, pesquisadores e estudantes frequentemente necessitam consultar diversas fontes distintas para obter informações meteorológicas.

Essa fragmentação dificulta análises históricas, comparações entre municípios e identificação rápida de eventos climáticos críticos.

---

# 4. Objetivo Geral

Desenvolver uma plataforma inteligente para monitoramento climático da cafeicultura, integrando dados meteorológicos, indicadores analíticos e visualizações interativas.

---

# 5. Objetivos Específicos

* Automatizar a coleta de dados climáticos.
* Armazenar informações em PostgreSQL.
* Disponibilizar dashboards analíticos.
* Monitorar ocorrências de geadas.
* Gerar indicadores climáticos.
* Apoiar futuras análises estatísticas.
* Servir como plataforma para aplicações de Ciência de Dados.

---

# 6. Escopo

O projeto contempla:

* Cadastro de municípios.
* Coleta automática de dados climáticos.
* Armazenamento histórico.
* Dashboard interativo.
* Indicadores climáticos.
* Ranking climático.
* Relatórios.
* Geoprocessamento (fase futura).
* Inteligência analítica (fase futura).

---

# 7. Fora do Escopo

Nesta versão do projeto não serão contemplados:

* Aplicativo móvel.
* Controle financeiro agrícola.
* Gestão de propriedades rurais.
* Integração com sensores IoT.
* Modelos de Machine Learning em produção.

Esses itens poderão compor versões futuras da plataforma.

---

# 8. Stakeholders

## Principal

Walter Junio Pontes Teixeira

## Instituição

Universidade Virtual do Estado de São Paulo (UNIVESP)

## Usuários potenciais

* Produtores rurais
* Cooperativas
* Pesquisadores
* Instituições de ensino
* Estudantes
* Desenvolvedores

---

# 9. Premissas

* Disponibilidade da API Open-Meteo.
* Disponibilidade do PostgreSQL.
* Acesso à internet para coleta dos dados.
* Ambiente Django operacional.
* Dados públicos confiáveis.

---

# 10. Restrições

* Projeto desenvolvido no contexto de um TCC.
* Tempo limitado pelo cronograma acadêmico.
* Dependência de APIs públicas.
* Recursos computacionais locais.

---

# 11. Critérios de Sucesso

O projeto será considerado bem-sucedido quando:

* Coletar dados automaticamente.
* Armazenar dados corretamente.
* Exibir dashboards funcionais.
* Apresentar indicadores consistentes.
* Possuir documentação completa.
* Seguir boas práticas de Engenharia de Software.
* Atender aos objetivos do TCC.

---

# 12. Entregáveis

* Plataforma Web.
* Dashboard Analítico.
* Banco de Dados PostgreSQL.
* Documentação Técnica.
* Código-fonte versionado.
* Relatório Final.
* Apresentação do TCC.

---

# 13. Principais Riscos

| Risco                 | Mitigação                                                  |
| --------------------- | ---------------------------------------------------------- |
| API indisponível      | Uso de tratamento de exceções e novas tentativas de coleta |
| Alterações na API     | Camada de adaptação para integração                        |
| Crescimento do escopo | Controle por roadmap e Sprints                             |
| Retrabalho            | Planejamento e documentação contínuos                      |
| Perda de código       | Versionamento com Git e GitHub                             |

---

# 14. Organização do Projeto

O desenvolvimento seguirá um processo incremental baseado em Sprints, contemplando:

* Planejamento
* Arquitetura
* Implementação
* Validação
* Documentação
* Versionamento
* Lições Aprendidas

Cada Sprint produzirá entregas completas e documentadas.

---

# 15. Cronograma Macro

| Fase                     | Status            |
| ------------------------ | ----------------- |
| Planejamento Estratégico | ✅ Concluído       |
| Fundação Documental      | 🔄 Em andamento   |
| Dashboard V3             | ⏳ Planejado       |
| Ranking Climático        | ⏳ Planejado       |
| Inteligência Climática   | ⏳ Planejado       |
| Geoprocessamento         | ⏳ Planejado       |
| Relatórios               | ⏳ Planejado       |
| Versão 1.0               | 🎯 Objetivo Final |

---

# 16. Aprovação

Este documento formaliza oficialmente o início do desenvolvimento do projeto **AgroClima Café**, estabelecendo seus objetivos, escopo, organização e critérios de sucesso.

A partir desta aprovação, todas as decisões técnicas e funcionais deverão estar alinhadas às diretrizes aqui estabelecidas.

---

# Histórico de Revisões

| Versão | Data       | Descrição                    |
| ------ | ---------- | ---------------------------- |
| 1.0    | Junho/2026 | Criação inicial do documento |

---

# Próximos Passos

* DOC-003 — PRODUCT_VISION.md
* DOC-004 — ROADMAP.md
* DOC-005 — CHANGELOG.md
* DOC-006 — SOFTWARE_REQUIREMENTS_SPECIFICATION.md
* DOC-007 — SYSTEM_ARCHITECTURE.md
