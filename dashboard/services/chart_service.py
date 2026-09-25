"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: chart_service.py

Descrição.......:
Serviço responsável pelo fornecimento dos dados utilizados pelos gráficos
do Dashboard Principal.

Responsabilidades:
- Consolidar os períodos do gráfico;
- Usar observações meteorológicas atuais exclusivamente no período "Hoje";
- Preservar os dados fornecidos pelo HistoryService nos períodos históricos;
- Preparar o resumo correspondente a cada período;
- Preservar ocorrências reais de geada;
- Não inventar ocorrências históricas de geada;
- Não executar regras de inteligência climática.

Versão..........: 2.12 — correção da integração da ETo corrente no gráfico
===============================================================================
"""

from statistics import mean

from django.utils import timezone

from clima.models import WeatherObservation
from clima.services.history_service import HistoryService


class ChartService:
    """
    Serviço responsável pelos dados utilizados nos gráficos da Dashboard.

    Contrato de períodos:

        hoje       -> observações meteorológicas atuais do dia corrente;
        7_dias     -> HistoricalWeatherDaily / HistoryService;
        30_dias    -> HistoricalWeatherDaily / HistoryService;
        historico  -> HistoricalWeatherDaily / HistoryService.

    O frontend não deve escolher fontes de dados. Ele recebe os períodos
    já consolidados por este serviço.
    """

    def __init__(self):
        self.history = HistoryService()

    # ==========================================================
    # DADOS DO GRÁFICO
    # ==========================================================

    def get_chart(
        self,
        days=7,
    ):
        """
        Mantém compatibilidade com chamadas existentes.

        Retorna o período histórico solicitado.
        """
        data = self.history.chart_data(
            municipio=None,
            days=days,
        )

        return self._format(
            data
        )

    # ==========================================================
    # PERÍODOS DO DASHBOARD
    # ==========================================================

    def get_chart_periods(self, current_kpis=None):
        """
        Prepara todas as séries utilizadas pelos controles
        de período do gráfico.

        Regras:

        Hoje:
            utiliza somente observações meteorológicas cujo
            observation_time pertence à data atual.

        7 dias:
            últimos 7 dias do histórico diário.

        30 dias:
            últimos 30 dias do histórico diário.

        Histórico:
            todo o histórico diário disponível.
        """

        hoje = self._get_today_period(current_kpis)

        sete_dias = self.history.chart_data(
            municipio=None,
            days=7,
        )
        sete_dias = self._integrate_current_day(
            sete_dias,
            current_kpis,
        )

        trinta_dias = self.history.chart_data(
            municipio=None,
            days=30,
        )
        trinta_dias = self._integrate_current_day(
            trinta_dias,
            current_kpis,
        )

        historico = self.history.chart_data(
            municipio=None,
            days=None,
        )
        historico = self._integrate_current_day(
            historico,
            current_kpis,
        )

        return {
            "hoje": self._format(
                hoje
            ),
            "7_dias": self._format(
                sete_dias
            ),
            "30_dias": self._format(
                trinta_dias
            ),
            "historico": self._format(
                historico
            ),
        }

    def _integrate_current_day(
        self,
        data,
        current_kpis=None,
    ):
        """
        Preserva integralmente as séries históricas recebidas do
        HistoryService.

        Este método permanece como ponto de compatibilidade do fluxo
        existente, mas não substitui o valor diário do período histórico
        por KPIs correntes.

        Regra canônica:
            - 7 dias, 30 dias e Histórico são séries diárias;
            - precipitation_24h_mm é uma janela móvel de 24 horas;
            - portanto, precipitation_24h_mm não pode ocupar a posição
              de precipitação diária do dia atual;
            - temperatura corrente não substitui a temperatura média
              diária histórica;
            - ETo histórica permanece sob autoridade do HistoryService.

        O parâmetro current_kpis é mantido na assinatura para preservar
        compatibilidade com os consumidores existentes.

        Exceção controlada:
            - somente a posição correspondente ao dia atual pode receber
              a ETo corrente de current_kpis;
            - nenhuma outra série histórica é alterada;
            - se a ETo corrente for None, a ausência permanece None.
        """
        if not isinstance(data, dict):
            return data

        if not isinstance(current_kpis, dict):
            return data

        eto_current = current_kpis.get("eto_mm_day")

        if eto_current is None:
            return data

        dias = data.get("dias")
        eto_values = data.get("eto_mm_day")

        if not isinstance(dias, list):
            return data

        if not isinstance(eto_values, list):
            return data

        if not dias or not eto_values:
            return data

        hoje = timezone.localdate().strftime("%d/%m")

        if dias[-1] != hoje:
            return data

        if len(eto_values) != len(dias):
            return data

        try:
            eto_current = round(float(eto_current), 2)
        except (TypeError, ValueError):
            return data

        eto_values[-1] = eto_current
        data["eto_mm_day"] = eto_values

        return data

    # ==========================================================
    # PERÍODO "HOJE"
    # ==========================================================

    def _get_today_period(self, current_kpis=None):
        """
        Constrói exclusivamente o período "Hoje" a partir das
        observações meteorológicas reais do dia atual.

        Regra territorial:
            uma observação mais recente por município monitorado.

        Consolidação regional:
            temperatura e precipitação são calculadas pela média
            das últimas observações disponíveis de cada município.

        Importante:
            - nunca utiliza registro de outro dia;
            - nunca faz fallback para 7 dias, 30 dias ou histórico;
            - ausência de observação permanece como ausência de dado;
            - nenhum None é convertido em zero.
        """

        hoje = timezone.localdate()

        # ETo corrente vem do mesmo contrato que alimenta os KPIs.
        # O ChartService não calcula nem estima ETo.
        today_eto = (
            current_kpis.get("eto_mm_day")
            if isinstance(current_kpis, dict)
            else None
        )

        if current_kpis is not None:
            return {
                "dias": [hoje.strftime("%d/%m")],
                "temperatura": [
                    current_kpis.get("temperatura_media")
                ],
                "precipitacao": [
                    current_kpis.get("precipitacao_24h")
                ],
                "eto_mm_day": [
                    today_eto
                ],
                "umidade": [None],
                "vento": [None],
                "indice_agroclima": [],
                "geadas": self._get_today_frost_count(),
            }

        observations = (
            WeatherObservation.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                observation_time__date=hoje,
            )
            .order_by(
                "station__municipio_id",
                "-observation_time",
            )
        )

        latest_by_municipality = {}

        for observation in observations:
            municipality_id = (
                observation.station.municipio_id
            )

            if municipality_id in latest_by_municipality:
                continue

            latest_by_municipality[
                municipality_id
            ] = observation

        if not latest_by_municipality:
            return self._empty()

        latest_observations = list(
            latest_by_municipality.values()
        )

        temperatures = self._valid_numbers(
            [
                observation.temperatura
                for observation in latest_observations
            ]
        )

        precipitations = self._valid_numbers(
            [
                getattr(
                    observation,
                    "precipitacao_24h",
                    observation.precipitacao,
                )
                for observation in latest_observations
            ]
        )

        humidities = self._valid_numbers(
            [
                observation.umidade
                for observation in latest_observations
            ]
        )

        wind_speeds = self._valid_numbers(
            [
                observation.velocidade_vento
                for observation in latest_observations
            ]
        )

        if (
            not temperatures
            and not precipitations
        ):
            return self._empty()

        temperature_value = None

        if temperatures:
            temperature_value = round(
                mean(temperatures),
                1,
            )

        precipitation_value = None

        if precipitations:
            precipitation_value = round(
                mean(precipitations),
                1,
            )

        humidity_value = None

        if humidities:
            humidity_value = round(
                mean(humidities),
                1,
            )

        wind_value = None

        if wind_speeds:
            wind_value = round(
                mean(wind_speeds),
                1,
            )

        # ETo diária vem exclusivamente do HistoryService.
        # Não é calculada a partir das observações meteorológicas correntes.
        today_eto = self._get_today_eto()

        return {
            "dias": [
                hoje.strftime("%d/%m"),
            ],
            "temperatura": [
                temperature_value,
            ],
            "precipitacao": [
                precipitation_value,
            ],
            "eto_mm_day": [
                today_eto,
            ],
            "umidade": [
                humidity_value,
            ],
            "vento": [
                wind_value,
            ],
            "indice_agroclima": [],
            "geadas": self._get_today_frost_count(),
        }

    # ==========================================================
    # ETo DO DIA ATUAL
    # ==========================================================

    def _get_today_eto(self):
        """
        Retorna a ETo diária persistida para hoje quando consultada
        diretamente.

        Este método permanece disponível para compatibilidade.
        O período "Hoje", quando recebe current_kpis, usa
        current_kpis["eto_mm_day"] como fonte corrente.
        """

        data = self.history.chart_data(
            municipio=None,
            days=1,
        )

        if not data:
            return None

        valores = data.get(
            "eto_mm_day",
            [],
        )

        if not isinstance(valores, list) or not valores:
            return None

        valor = valores[0]

        if valor is None:
            return None

        try:
            return round(
                float(valor),
                1,
            )
        except (
            TypeError,
            ValueError,
        ):
            return None


    # ==========================================================
    # GEADAS DO DIA ATUAL
    # ==========================================================

    def _get_today_frost_count(self):
        """
        Obtém o número de ocorrências de geada que o
        HistoryService reconhece para o dia atual.

        Se não houver informação histórica para o dia, retorna None.
        Não transforma ausência de dados em zero.
        """

        data = self.history.chart_data(
            municipio=None,
            days=1,
        )

        if not data:
            return None

        geadas = data.get(
            "geadas",
            None,
        )

        return geadas

    # ==========================================================
    # FORMATAÇÃO
    # ==========================================================

    @classmethod
    def _format(
        cls,
        data,
    ):
        """
        Normaliza os dados recebidos e prepara o resumo
        correspondente exatamente ao período consultado.

        O valor de geadas é preservado:
            0    = nenhuma ocorrência real;
            None = ausência de informação.
        """

        if not data:
            return cls._empty()

        dias = data.get(
            "dias",
            [],
        )

        temperatura = data.get(
            "temperatura",
            [],
        )

        precipitacao = data.get(
            "precipitacao",
            [],
        )

        umidade = data.get(
            "umidade",
            [],
        )

        vento = data.get(
            "vento",
            [],
        )

        indice_agroclima = data.get(
            "indice_agroclima",
            [],
        )

        geadas = data.get(
            "geadas",
            None,
        )

        eto_mm_day = data.get(
            "eto_mm_day",
            [],
        )

        return {
            "dias": dias,
            "temperatura": temperatura,
            "precipitacao": precipitacao,
            "eto_mm_day": eto_mm_day,
            "umidade": umidade,
            "vento": vento,
            "indice_agroclima": indice_agroclima,
            "geadas": geadas,
            "resumo": cls._build_summary(
                temperatura=temperatura,
                precipitacao=precipitacao,
                eto_mm_day=eto_mm_day,
                geadas=geadas,
            ),
        }

    # ==========================================================
    # RESUMO
    # ==========================================================

    @classmethod
    def _build_summary(
        cls,
        temperatura,
        precipitacao,
        eto_mm_day=None,
        geadas=None,
    ):
        """
        Consolida os indicadores disponíveis na série.

        Regras:
        - temperatura média é calculada somente com valores reais;
        - precipitação é acumulada somente com valores reais;
        - para "Hoje", a série contém a média regional das observações
          atuais e, portanto, o resumo reproduz esse valor;
        - geadas preserva exatamente o valor recebido;
        - geadas=0 é valor válido;
        - geadas=None significa ausência de informação;
        - tendência deriva exclusivamente da série de temperatura.

        Não são criados dados artificiais.
        """

        temperaturas_validas = cls._valid_numbers(
            temperatura
        )

        precipitacoes_validas = cls._valid_numbers(
            precipitacao
        )

        eto_validos = cls._valid_numbers(
            eto_mm_day
        )

        temperatura_media = None

        if temperaturas_validas:
            temperatura_media = round(
                mean(
                    temperaturas_validas
                ),
                1,
            )

        precipitacao_total = None

        if precipitacoes_validas:
            precipitacao_total = round(
                sum(
                    precipitacoes_validas
                ),
                1,
            )

        eto_media_diaria = None

        if eto_validos:
            eto_media_diaria = round(
                mean(eto_validos),
                2,
            )

        eto_acumulada = None

        if eto_validos:
            eto_acumulada = round(
                sum(eto_validos),
                2,
            )

        geadas_resumo = None

        if geadas is not None:
            geadas_resumo = geadas

        return {
            "temperatura_media": temperatura_media,
            "precipitacao": precipitacao_total,
            "eto_media_diaria": eto_media_diaria,
            "eto_acumulada": eto_acumulada,
            "eto_dias_validos": len(eto_validos),
            "geadas": geadas_resumo,
            "tendencia": cls._temperature_trend(
                temperaturas_validas
            ),
        }

    # ==========================================================
    # TENDÊNCIA DE TEMPERATURA
    # ==========================================================

    @staticmethod
    def _temperature_trend(
        values,
    ):
        """
        Classifica a tendência da série de temperatura.

        Retorno:
            "Alta"
            "Queda"
            "Estável"
            None
        """

        if not values:
            return None

        if len(values) < 2:
            return "Estável"

        primeiro = values[0]
        ultimo = values[-1]

        diferenca = ultimo - primeiro

        if abs(diferenca) < 0.5:
            return "Estável"

        if diferenca > 0:
            return "Alta"

        return "Queda"

    # ==========================================================
    # VALIDAÇÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _valid_numbers(
        values,
    ):
        """
        Retorna somente valores numéricos válidos.

        None e valores não conversíveis são ignorados.
        """

        if not values:
            return []

        valid = []

        for value in values:
            if value is None:
                continue

            try:
                valid.append(
                    float(value)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        return valid

    # ==========================================================
    # RETORNO PADRÃO
    # ==========================================================

    @staticmethod
    def _empty():
        """
        Contrato vazio.

        Ausência de dados permanece None/estrutura vazia.
        Nunca utiliza zero como substituto de ausência.
        """

        return {
            "dias": [],
            "temperatura": [],
            "precipitacao": [],
            "umidade": [],
            "vento": [],
            "eto_mm_day": [],
            "indice_agroclima": [],
            "geadas": None,
            "resumo": {
                "temperatura_media": None,
                "precipitacao": None,
                "eto_media_diaria": None,
                "eto_acumulada": None,
                "eto_dias_validos": 0,
                "geadas": None,
                "tendencia": None,
            },
        }


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 7 — SÉRIE DE ETo
# ============================================================================
#
# Arquivo-base auditado: chart_service.py — versão 2.8.
# Tamanho original: 618 linhas.
#
# Alteração desta etapa:
#     HistoryService
#         -> chart_periods
#         -> ChartService
#         -> eto_mm_day + resumo de ETo
#
# O ChartService não calcula ETo. Apenas preserva a série diária fornecida pelo
# HistoryService e consolida média, acumulado e quantidade de dias válidos.
# None permanece None e não é convertido em zero.
#
# O período Hoje mantém ETo como None porque o contrato atual de current_kpis
# não fornece ETo corrente. Nenhum valor é inventado.
#
# FRI, indicadores térmicos, precipitação e geadas permanecem preservados.
# Nenhuma regra agronômica é criada nesta etapa.
# ============================================================================

# ============================================================================
# REGISTRO DE AUDITORIA — FASE 7 — CONTRATO VAZIO COMPLETO
# ============================================================================
#
# Correção aplicada após a validação da série de ETo no Dashboard.
#
# O contrato vazio de ``ChartService`` passa a declarar explicitamente os
# mesmos campos de resumo produzidos por ``_build_summary`` para uma série
# com dados. Isso evita contratos diferentes entre estado com dados e estado
# sem dados.
#
# Regras preservadas:
#     - ausência de ETo permanece ``None``;
#     - ``eto_dias_validos`` permanece 0 quando não há valores;
#     - nenhum valor meteorológico é inventado;
#     - nenhuma regra agroclimática é criada no frontend;
#     - FRI, geadas, temperatura e precipitação permanecem inalterados.
#
# A alteração é exclusivamente contratual e defensiva para a Fase 7.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 7 — ETo DO PERÍODO "HOJE"
# ============================================================================
#
# Base:
#     chart_service.py — versão 2.10.
#
# Problema confirmado:
#     _get_today_period() declarava eto_mm_day como [None], mesmo quando
#     a ETo diária já estava persistida e disponível pelo HistoryService.
#
# Correção:
#     o período "Hoje" passa a obter a ETo exclusivamente por
#     _get_today_eto(), cuja fonte é HistoryService.chart_data(days=1).
#
# Regras preservadas:
#     - ChartService não calcula ETo;
#     - HistoryService permanece autoridade da série diária;
#     - current_kpis não fornece nem substitui ETo;
#     - 7 dias, 30 dias e Histórico continuam inalterados;
#     - ausência de ETo permanece None;
#     - nenhum valor meteorológico é inventado.
#
# ============================================================================

# ============================================================================
# REGISTRO DE AUDITORIA — FASE MD-01 — CORREÇÃO DA SEMÂNTICA DA SÉRIE DIÁRIA
# ============================================================================
#
# Base:
#     chart_service.py — versão 2.9 / Fase 7 ETo.
#
# Problema confirmado:
#     _integrate_current_day() substituía o valor diário do dia atual nos
#     períodos 7 dias, 30 dias e Histórico por:
#
#         current_kpis["precipitacao_24h"]
#
#     Isso misturava uma janela móvel de 24 horas com uma série de
#     precipitação diária proveniente do HistoryService.
#
# Correção:
#     _integrate_current_day() deixou de modificar as séries históricas.
#
# Resultado:
#     - 7 dias, 30 dias e Histórico preservam os valores entregues pelo
#       HistoryService;
#     - precipitation_24h não é mais inserida em uma série diária;
#     - temperatura corrente não é mais inserida como temperatura média diária;
#     - ETo permanece sob autoridade do HistoryService;
#     - o parâmetro current_kpis permanece na assinatura por compatibilidade.
#
# Esta etapa NÃO implementa ainda precipitation_7d_mm/30d_mm e NÃO altera
# a política de dados ausentes do HistoryService. Essas responsabilidades
# permanecem na próxima etapa do contrato canônico.
#
# ============================================================================
