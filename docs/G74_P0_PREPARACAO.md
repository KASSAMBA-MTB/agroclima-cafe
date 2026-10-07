# G7.4 / P0 — Preparação de execução

## Estado

Preparação concluída. O instrumento foi criado para executar o P0 sem alterar
o código de produção do AgroClima Café.

## Arquivo

`tools/g74_p0_probe.py`

## Estrutura de evidência

```text
tools/
  g74_p0_probe.py

raw/
  g74_p0/
    <uma evidência por tentativa>

reports/
  g74_p0/
    <relatório consolidado>
```

## Protocolo congelado

- API: Previous Runs
- Modelo: ECMWF IFS 0.25°
- Lead: `previous_day1`
- Timezone: `GMT`
- Janela: `2026-01-15` a `2026-01-21`
- `cell_selection=land`
- Limite CONFIRMADO: 95%
- Blocos: A → B → C
- Erro HTTP/API: INCONCLUSIVO
- HTTP 200 + variável presente + 100% null: AUSENTE
- HTTP 200 + variável presente + completude >= 95%: CONFIRMADO
- Entre os dois: PARCIAL
- Nenhuma variável equivalente será substituída silenciosamente.
- Nenhum cálculo meteorológico de granizo será executado.

## Bloco A

- `cape_previous_day1`
- `convective_inhibition_previous_day1`
- `wind_speed_10m_previous_day1`
- `wind_direction_10m_previous_day1`
- `surface_pressure_previous_day1`

## Bloco B

Para cada nível:

`1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400 hPa`

- `temperature_<level>hPa_previous_day1`
- `relative_humidity_<level>hPa_previous_day1`

## Bloco C

Nos mesmos 11 níveis:

- `wind_speed_<level>hPa_previous_day1`
- `wind_direction_<level>hPa_previous_day1`
- `geopotential_height_<level>hPa_previous_day1`

## Garantias

Antes da requisição:

1. todas as variáveis são geradas programaticamente;
2. todas devem terminar em `_previous_day1`;
3. o URL e os parâmetros são registrados.

Durante a requisição:

1. o retorno bruto é salvo primeiro;
2. somente depois ocorre o parsing;
3. erros 400/429 e outros erros de consulta não são classificados como AUSENTE.

Após o retorno:

1. latitude;
2. longitude;
3. elevação;
4. `utc_offset_seconds`;
5. timezone;
6. unidades;
7. `generationtime_ms`;
8. série temporal;
9. PASSO_GRID;
10. PASSO_DADOS;
11. primeiro/último timestamp com valor;
12. último timestamp do grid;
13. presença/ausência do último valor esperado.

## Ponto ainda obrigatório antes da execução

As coordenadas de Poços de Caldas ainda precisam ser inseridas no script a
partir do ponto de referência municipal previamente congelado/citável.

O script deliberadamente NÃO aceita coordenadas vazias ou inventadas.

## Execução

No ambiente do projeto:

```powershell
python tools\g74_p0_probe.py
```

O script não depende do Django.

## Resultado esperado desta etapa

O P0 NÃO decide ainda a viabilidade do índice de granizo.

Ele somente produz evidência sobre:

> quais campos do IFS 0.25° / previous_day1 estão realmente disponíveis,
> com que completude, passo e metadados, para o ponto e janela congelados.

A decisão G7.4 somente será tomada depois da análise dos resultados reais.
