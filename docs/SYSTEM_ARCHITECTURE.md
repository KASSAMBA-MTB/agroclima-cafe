# DOC-007 — SYSTEM_ARCHITECTURE.md

**Projeto:** AgroClima Café

**Documento:** DOC-007

**Versão:** 1.0

**Status:** Em desenvolvimento

**Autor:** Walter Junio Pontes Teixeira

**Curso:** Bacharelado em Ciência de Dados – UNIVESP

**Data:** Junho de 2026

---

# 1. Objetivo

Este documento descreve a arquitetura do sistema AgroClima Café, apresentando sua organização estrutural, componentes, fluxo de dados, tecnologias utilizadas e princípios de Engenharia de Software adotados durante o desenvolvimento.

---

# 2. Visão Geral da Arquitetura

O AgroClima Café foi concebido utilizando arquitetura em camadas (Layered Architecture), baseada no padrão MTV (Model-Template-View) do Django.

```text
                Usuário
                    │
                    ▼
          Interface Web (Dashboard)
                    │
                    ▼
            Views (Django)
                    │
                    ▼
         Regras de Negócio
                    │
                    ▼
           Models (ORM Django)
                    │
                    ▼
              PostgreSQL
                    ▲
                    │
             Open-Meteo API
```

---

# 3. Arquitetura em Camadas

## Camada de Apresentação

Responsável pela interação com o usuário.

Tecnologias:

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* Chart.js

Funções:

* Dashboards
* Gráficos
* Formulários
* Navegação

---

## Camada de Aplicação

Responsável pela lógica do sistema.

Tecnologias:

* Django
* Python

Funções:

* Processamento
* Regras de negócio
* Integração entre módulos
* APIs

---

## Camada de Persistência

Responsável pelo armazenamento.

Tecnologias:

* PostgreSQL
* Django ORM

Funções:

* Persistência
* Consultas
* Atualizações
* Integridade dos dados

---

## Camada Externa

Responsável pela aquisição de dados.

Atualmente:

* Open-Meteo API

Futuramente:

* Novas APIs
* Bases públicas
* Sensores IoT

---

# 4. Arquitetura dos Módulos

A plataforma está organizada em aplicações Django independentes.

```text
AgroClima Café

│

├── usuarios
├── municipios
├── clima
├── geadas
├── dashboard
└── relatorios
```

Cada aplicação possui responsabilidades específicas, favorecendo a modularidade e a manutenção.

---

# 5. Fluxo Geral da Aplicação

```text
Open-Meteo

↓

Coleta

↓

Processamento

↓

PostgreSQL

↓

Views Django

↓

Dashboard

↓

Usuário
```

---

# 6. Fluxo de Atualização Climática

```text
Solicitação

↓

Open-Meteo

↓

Resposta JSON

↓

Parser

↓

Banco PostgreSQL

↓

Dashboard atualizado
```

---

# 7. Componentes do Sistema

## Dashboard

Responsável pela apresentação dos indicadores.

---

## Municípios

Cadastro dos municípios monitorados.

---

## Clima

Armazenamento dos registros meteorológicos.

---

## Geadas

Registro e análise de eventos de geada.

---

## Relatórios

Geração de documentos analíticos.

---

## Usuários

Controle de acesso e autenticação.

---

# 8. Estrutura do Projeto

```text
agroclima-cafe/

│

├── agroclima/
├── dashboard/
├── clima/
├── municipios/
├── geadas/
├── usuarios/
├── relatorios/

│

├── docs/
├── design/
├── project-management/

│

├── static/
├── templates/

│

├── manage.py
└── requirements.txt
```

---

# 9. Tecnologias

## Backend

* Python
* Django

## Banco

* PostgreSQL

## Front-end

* Bootstrap
* HTML5
* CSS3
* JavaScript
* Chart.js

## APIs

* Open-Meteo

## Versionamento

* Git
* GitHub

---

# 10. Princípios Arquiteturais

O desenvolvimento seguirá os princípios:

* Modularidade;
* Separação de responsabilidades;
* Baixo acoplamento;
* Alta coesão;
* Reutilização;
* Escalabilidade;
* Simplicidade;
* Documentação contínua.

---

# 11. Segurança

A plataforma utilizará:

* Autenticação Django;
* Controle de permissões;
* ORM para acesso ao banco;
* Proteção contra SQL Injection;
* Proteção CSRF;
* Sessões autenticadas.

---

# 12. Escalabilidade

A arquitetura foi planejada para permitir futura incorporação de:

* Machine Learning;
* Inteligência Artificial;
* Geoprocessamento;
* APIs adicionais;
* Aplicativos móveis;
* Serviços em nuvem.

---

# 13. Decisões Arquiteturais

As principais decisões adotadas foram:

* Django como framework principal.
* PostgreSQL como banco oficial.
* Bootstrap para interface.
* Chart.js para visualização de dados.
* Open-Meteo como fonte meteorológica.
* Arquitetura modular baseada em apps.

---

# 14. Qualidade

Toda evolução deverá preservar:

* Clareza;
* Organização;
* Manutenibilidade;
* Desempenho;
* Escalabilidade;
* Padronização.

---

# 15. Evolução da Arquitetura

A arquitetura será refinada ao longo do projeto, incorporando:

* Diagrama de Componentes.
* Diagrama de Classes.
* Modelo Entidade-Relacionamento (MER).
* Diagrama de Implantação.
* Fluxo completo dos dados.
* Arquitetura Dashboard V3.

---

# Histórico de Revisões

| Versão | Data       | Descrição                      |
| ------ | ---------- | ------------------------------ |
| 1.0    | Junho/2026 | Criação inicial da arquitetura |

---

# Próximos Passos

* DOC-008 — DESIGN_SYSTEM.md
* Diagrama UML de Componentes
* Modelo Entidade-Relacionamento (MER)
* Diagrama de Implantação
* Arquitetura Dashboard V3
