# ☕ AgroClima Café

## Plataforma Inteligente de Monitoramento Climático para Apoio à Cafeicultura

> **Dados que cultivam decisões.**

---

# 📖 Sobre o Projeto

O **AgroClima Café** é uma plataforma web desenvolvida como Trabalho de Conclusão de Curso (TCC) do Bacharelado em Ciência de Dados da **UNIVESP – Universidade Virtual do Estado de São Paulo**.

O projeto tem como objetivo integrar dados meteorológicos provenientes de APIs públicas, armazená-los em um banco de dados PostgreSQL e disponibilizar informações estratégicas por meio de dashboards analíticos voltados ao monitoramento climático da cafeicultura.

Além de atender aos requisitos acadêmicos, o AgroClima Café é desenvolvido seguindo princípios de Engenharia de Software, Arquitetura de Sistemas, Ciência de Dados e Visualização de Dados, buscando um padrão compatível com aplicações profissionais.

---

# 🎯 Objetivos

## Objetivo Geral

Desenvolver uma plataforma inteligente para monitoramento climático aplicada à cafeicultura.

## Objetivos Específicos

* Centralizar dados climáticos dos municípios monitorados;
* Automatizar a coleta de informações meteorológicas;
* Disponibilizar indicadores climáticos em tempo real;
* Gerar visualizações gráficas para apoio à decisão;
* Monitorar ocorrências de geadas;
* Consolidar históricos climáticos para análises futuras;
* Servir como plataforma para futuras aplicações de Ciência de Dados.

---

# 🌱 Motivação

A produção de café é altamente dependente das condições climáticas.

Eventos como geadas, precipitações intensas e variações bruscas de temperatura podem impactar significativamente a produtividade.

O AgroClima Café busca transformar dados meteorológicos em informações úteis para apoiar produtores, pesquisadores e instituições na tomada de decisões.

---

# 👥 Público-Alvo

* Produtores rurais;
* Cooperativas agrícolas;
* Pesquisadores;
* Instituições de ensino;
* Órgãos públicos;
* Estudantes de Ciência de Dados;
* Desenvolvedores interessados em Agricultura Digital.

---

# 🚀 Funcionalidades

## Implementadas

* Cadastro de Municípios
* Cadastro de Dados Climáticos
* Integração com Open-Meteo
* Banco PostgreSQL
* Dashboard Dinâmico
* Gráficos Climáticos
* Controle de Geadas
* Administração via Django Admin
* Versionamento Git/GitHub

## Em desenvolvimento

* Dashboard V3
* Ranking Climático
* Tendências Climáticas
* Mapas Interativos
* Relatórios PDF
* Exportação Excel
* Inteligência Climática
* Indicadores Estatísticos

## Futuras

* Machine Learning
* Predição de Geadas
* Predição de Temperaturas
* Predição de Chuvas
* Alertas Inteligentes
* Aplicativo Mobile

---

# 🏗 Arquitetura

O sistema é desenvolvido utilizando arquitetura em camadas.

```
Usuário

↓

Dashboard

↓

Views Django

↓

Models

↓

PostgreSQL

↓

Open-Meteo API
```

---

# 💻 Tecnologias

## Backend

* Python
* Django 6
* PostgreSQL

## Front-end

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* Chart.js

## APIs

* Open-Meteo

## Controle de Versão

* Git
* GitHub

---

# 📁 Estrutura do Projeto

```
agroclima-cafe/

agroclima/

dashboard/

clima/

municipios/

geadas/

usuarios/

relatorios/

templates/

static/

docs/

design/

project-management/
```

---

# 🗄 Banco de Dados

Banco utilizado:

PostgreSQL

Principais entidades:

* Municípios
* Dados Climáticos
* Geadas
* Usuários
* Relatórios

---

# 🌎 Fonte dos Dados

Atualmente os dados meteorológicos são obtidos através da API pública **Open-Meteo**, permitindo a coleta automática de:

* Temperatura
* Umidade
* Pressão Atmosférica
* Velocidade do Vento
* Precipitação

---

# 📊 Dashboard

O Dashboard apresenta indicadores climáticos como:

* Temperatura mínima média
* Precipitação acumulada
* Ocorrências de geadas
* Dias com temperatura igual ou inferior a 0°C
* Temperaturas por município
* Ranking climático (em desenvolvimento)

---

# 🛣 Roadmap

| Versão | Status                     |
| ------ | -------------------------- |
| v0.1   | ✅ Estrutura Inicial        |
| v0.2   | ✅ Dashboard V2             |
| v0.3   | ✅ Arquitetura Dashboard V3 |
| v0.4   | 🚧 Dashboard Profissional  |
| v0.5   | ⏳ Ranking Climático        |
| v0.6   | ⏳ Inteligência Climática   |
| v0.7   | ⏳ Geoprocessamento         |
| v0.8   | ⏳ Relatórios               |
| v0.9   | ⏳ Testes e Otimizações     |
| v1.0   | 🎯 Entrega Final           |

---

# 📚 Documentação

A documentação técnica será organizada da seguinte forma:

```
docs/

design/

project-management/
```

Incluindo:

* Arquitetura
* Banco de Dados
* APIs
* Design System
* Roadmap
* ADRs
* Manual do Usuário
* Manual Técnico

---

# ⚙ Instalação

Clone o repositório:

```bash
git clone https://github.com/KASSAMBA-MTB/agroclima-cafe.git
```

Entre na pasta:

```bash
cd agroclima-cafe
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute as migrações:

```bash
python manage.py migrate
```

Inicie o servidor:

```bash
python manage.py runserver
```

---

# 📌 Filosofia de Desenvolvimento

O AgroClima Café é desenvolvido seguindo os princípios de:

* Engenharia de Software;
* Ciência de Dados;
* Arquitetura de Sistemas;
* Desenvolvimento Incremental;
* Documentação Contínua;
* Versionamento Profissional.

Toda funcionalidade implementada passa por planejamento, implementação, validação, documentação e versionamento.

---

# 📈 Status do Projeto

**Versão Atual**

v0.3.0

**Situação**

Em desenvolvimento.

---

# 👨‍💻 Autor

**Walter Junio Pontes Teixeira**

Bacharelado em Ciência de Dados

UNIVESP

2026

---

# 🤝 Agradecimentos

À Universidade Virtual do Estado de São Paulo (UNIVESP), aos professores do curso de Ciência de Dados e a todos que contribuíram direta ou indiretamente para o desenvolvimento deste projeto.

---

# 📄 Licença

Este projeto é desenvolvido para fins acadêmicos como Trabalho de Conclusão de Curso (TCC).

A definição da licença definitiva será realizada durante a fase final do desenvolvimento.
