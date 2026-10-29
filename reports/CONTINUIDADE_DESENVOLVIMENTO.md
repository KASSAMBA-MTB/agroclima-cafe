# AgroClima Café — Registro de continuidade

## Sessão: 2026-10-29

### Ponto inicial
- Branch: `main`
- Commit base local e remoto: `fc77c12bc206c552de98815c189757b853631b26`
- Estado inicial: local e `origin/main` sincronizados.
- Arquivos não rastreados preexistentes: preservados; não incluídos neste incremento.

### Objetivo deste incremento
Criar o esqueleto isolado da validação científica das condições meteorológicas associadas ao evento granizo.

### Arquivos deste incremento
- `core/intelligence/hail_scientific_validation.py`
- `core/intelligence/test_hail_scientific_validation.py`
- `reports/CONTINUIDADE_DESENVOLVIMENTO.md`

### Limites funcionais
- Consome resultados experimentais já produzidos pelo MP-01.12.
- Compara estatisticamente, de forma descritiva, referências de granizo confirmado e períodos de controle.
- Registra erros de qualidade e mantém valores ausentes como ausentes.
- Não define limiares, não calcula probabilidade e não classifica potencial operacional.
- Não altera DashboardService, FRI, contratos MP-01.11/MP-01.12 nem a aquisição Open-Meteo/INMET.
- Não declara homologação científica.

### Fechamento desta sessão
O commit definitivo e o resultado dos testes devem ser registrados após a execução local do script. Se os testes falharem, não fazer commit nem push; registrar a falha e preservar os arquivos para correção.

### Próxima retomada
1. Consultar este arquivo e o SHA do último commit.
2. Conferir o resultado real dos testes e o estado Git.
3. Evoluir a montagem do conjunto pareado com os dados e referências já validados no projeto.
4. Somente depois, implementar análises científicas adicionais justificadas pelos dados disponíveis.

## Incremento MP-01.13.1 — Montador do conjunto científico

- Ponto de partida: commit `9106a1d7fd4a9ddd1fdc0b618493d1971081d42c`.
- Escopo: novo montador isolado para manifesto, RAW, MP-01.11 e MP-01.12.
- Arquivos adicionados:
  - `core/intelligence/hail_scientific_dataset_builder.py`
  - `core/intelligence/test_hail_scientific_dataset_builder.py`
  - `tools/build_hail_scientific_validation_dataset.py`
  - `reports/g74_p0/hail_scientific_reference_manifest.example.csv`
- O manifesto exige rótulo e referência independentes; nenhum rótulo é inferido do modelo.
- O pareamento exige horário UTC exato, unidade esperada e coordenadas da requisição RAW coincidentes após arredondamento a quatro casas decimais.
- Não há interpolação espacial, janela temporal aproximada, limiar operacional ou alteração de componentes existentes.
- Comando de execução após preencher o manifesto com referências verificadas:
  `python tools/build_hail_scientific_validation_dataset.py --manifest research_inputs/hail_scientific_reference_manifest.csv`
- Os testes e o resultado de commit/push devem ser registrados ao final da execução local.
