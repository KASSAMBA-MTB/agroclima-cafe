# DOC-006 — SOFTWARE_REQUIREMENTS_SPECIFICATION.md

**Projeto:** AgroClima Café

**Documento:** DOC-006

**Versão:** 1.0

**Status:** Em desenvolvimento

**Autor:** Walter Junio Pontes Teixeira

**Curso:** Bacharelado em Ciência de Dados – UNIVESP

**Data:** Junho de 2026

---

# 1. Introdução

## 1.1 Objetivo

Este documento especifica os requisitos funcionais e não funcionais do sistema **AgroClima Café**, servindo como referência para desenvolvimento, validação, testes e manutenção da plataforma.

---

## 1.2 Escopo

O AgroClima Café é uma plataforma web destinada ao monitoramento climático aplicado à cafeicultura.

O sistema permitirá coletar, armazenar, analisar e apresentar dados meteorológicos por meio de dashboards interativos e indicadores analíticos.

---

## 1.3 Público-alvo

Este documento destina-se a:

* Desenvolvedores
* Orientadores
* Avaliadores do TCC
* Usuários da plataforma
* Futuros colaboradores

---

# 2. Visão Geral do Sistema

A plataforma será composta pelos seguintes módulos:

* Municípios
* Clima
* Geadas
* Dashboard
* Relatórios
* Usuários
* Administração

---

# 3. Requisitos Funcionais

## RF-001 — Cadastro de Municípios

O sistema deverá permitir cadastrar e manter municípios monitorados.

Prioridade: Alta

---

## RF-002 — Cadastro Climático

O sistema deverá armazenar registros meteorológicos.

Prioridade: Alta

---

## RF-003 — Integração com APIs

O sistema deverá importar automaticamente dados climáticos provenientes da API Open-Meteo.

Prioridade: Alta

---

## RF-004 — Dashboard

O sistema deverá apresentar indicadores climáticos em tempo real.

Prioridade: Alta

---

## RF-005 — Indicadores

O Dashboard deverá apresentar:

* Temperatura média
* Precipitação acumulada
* Ocorrências de geadas
* Dias com temperatura ≤ 0°C

Prioridade: Alta

---

## RF-006 — Gráficos

O sistema deverá apresentar gráficos interativos utilizando Chart.js.

Prioridade: Alta

---

## RF-007 — Ranking Climático

O sistema deverá classificar automaticamente os municípios conforme critérios climáticos definidos.

Prioridade: Média

---

## RF-008 — Relatórios

O sistema deverá gerar relatórios em PDF.

Prioridade: Média

---

## RF-009 — Exportação

O sistema deverá permitir exportação dos dados em formato CSV.

Prioridade: Média

---

## RF-010 — Administração

O administrador deverá gerenciar municípios, registros climáticos e ocorrências de geadas por meio do Django Admin.

Prioridade: Alta

---

# 4. Requisitos Não Funcionais

## RNF-001

O sistema deverá utilizar Python e Django.

---

## RNF-002

O banco de dados oficial será PostgreSQL.

---

## RNF-003

A interface deverá ser responsiva.

---

## RNF-004

Os dashboards deverão possuir carregamento rápido.

---

## RNF-005

O código deverá seguir boas práticas de Engenharia de Software.

---

## RNF-006

O sistema deverá utilizar Git para controle de versões.

---

## RNF-007

Toda funcionalidade deverá possuir documentação correspondente.

---

## RNF-008

A arquitetura deverá ser modular.

---

## RNF-009

Os componentes deverão ser reutilizáveis.

---

## RNF-010

O sistema deverá permitir evolução futura sem necessidade de reestruturação completa.

---

# 5. Regras de Negócio

## RN-001

Cada município poderá possuir diversos registros climáticos.

---

## RN-002

Cada registro climático deverá possuir data de coleta.

---

## RN-003

As geadas deverão estar associadas a um município.

---

## RN-004

Os indicadores deverão utilizar os dados mais recentes disponíveis.

---

## RN-005

Os rankings deverão ser recalculados automaticamente sempre que novos dados forem inseridos.

---

# 6. Casos de Uso

### UC-01

Consultar Dashboard.

---

### UC-02

Atualizar dados climáticos.

---

### UC-03

Cadastrar município.

---

### UC-04

Consultar histórico climático.

---

### UC-05

Visualizar Ranking Climático.

---

### UC-06

Emitir relatório.

---

# 7. Critérios de Aceite

Cada funcionalidade será considerada concluída quando:

* Implementação finalizada.
* Testes realizados.
* Documentação atualizada.
* Código revisado.
* Commit realizado.
* Push realizado.

---

# 8. Rastreabilidade

Os requisitos deverão ser rastreados durante todo o ciclo de desenvolvimento.

Exemplo:

| Requisito | Sprint |
| --------- | ------ |
| RF-001    | Fase A |
| RF-002    | Fase B |
| RF-004    | Fase C |
| RF-007    | Fase E |
| RF-008    | Fase G |

---

# 9. Premissas Técnicas

* Django 6
* PostgreSQL
* Bootstrap 5
* Chart.js
* Open-Meteo API
* Git
* GitHub

---

# 10. Restrições

* Projeto acadêmico.
* APIs públicas.
* Infraestrutura local.
* Cronograma do TCC.

---

# 11. Evolução Prevista

Após a versão 1.0 poderão ser incorporados:

* Machine Learning;
* Alertas Inteligentes;
* Aplicativo Mobile;
* Sensores IoT;
* Novas APIs meteorológicas;
* Inteligência Artificial aplicada à previsão climática.

---

# Histórico de Revisões

| Versão | Data       | Descrição       |
| ------ | ---------- | --------------- |
| 1.0    | Junho/2026 | Criação inicial |

---

# Próximos Passos

* DOC-007 — SYSTEM_ARCHITECTURE.md
* DOC-008 — DESIGN_SYSTEM.md
