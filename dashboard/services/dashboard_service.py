"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: dashboard_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
Serviço responsável por consolidar todos os dados estruturados
da Dashboard Principal.

Responsabilidades:
    • Consolidar KPIs, gráficos, ranking, eventos e mapa.
    • Enriquecer os pontos geográficos com dados meteorológicos.
    • Disponibilizar ocorrências históricas reais de geada.
    • Disponibilizar indicadores históricos estruturados para a
      camada de Inteligência.
    • Não executar regras de Inteligência.

Versão..........: 3.6
===============================================================================
"""

from datetime import timedelta

from clima.models import (
    HistoricalWeatherDaily,
    WeatherObservation,
)

from dashboard.services.kpi_service import KPIService
from dashboard.services.chart_service import ChartService
from dashboard.services.ranking_service import RankingService
from dashboard.services.events_service import EventsService
from dashboard.services.map_service import MapService


class DashboardService:
    """
    Consolida todos os dados estruturados utilizados pela
    Dashboard.

    Não executa regras de negócio inteligentes.

    A camada de Inteligência permanece responsabilidade da
    DashboardFacade.
    """

    def __init__(self):

        self.kpi_service = KPIService()

        self.chart_service = ChartService()

        self.ranking_service = RankingService()

        self.events_service = EventsService()

        self.map_service = MapService()

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def get_dashboard(self):
        """
        Consolida os dados estruturados da Dashboard.
        """

        context = {}

        # ======================================================
        # KPIs
        # ======================================================

        kpis = self.kpi_service.get_kpis()

        # Compatibilidade com templates legados
        context.update(kpis)

        # Dashboard V3
        context["kpis"] = kpis

        # ======================================================
        # GRÁFICOS
        # ======================================================

        context["chart"] = (
            self.chart_service.get_chart()
        )

        # ======================================================
        # PERÍODOS DO GRÁFICO
        #
        # Disponibiliza separadamente:
        #
        #   Hoje
        #   7 dias
        #   30 dias
        #   Histórico
        #
        # O frontend apenas alterna entre os dados
        # já consolidados pelo ChartService.
        # ======================================================

        context["chart_periods"] = (
            self.chart_service.get_chart_periods(
                current_kpis=kpis
            )
        )

        # ======================================================
        # RANKING
        # ======================================================

        context["ranking"] = (
            self.ranking_service.get_ranking()
        )

        # ======================================================
        # EVENTOS
        # ======================================================

        context["eventos"] = (
            self.events_service.get_events(
                kpis
            )
        )

        # ======================================================
        # MAPA
        # ======================================================

        map_points = (
            self.map_service.get_points()
        )

        # ======================================================
        # DADOS CLIMÁTICOS DOS MUNICÍPIOS
        #
        # Somente dados estruturados.
        #
        # Nenhuma regra de inteligência é executada aqui.
        # ======================================================

        map_points = self._attach_climate_data(
            map_points
        )

        context["map_points"] = map_points

        # ======================================================
        # CAMPOS PREENCHIDOS PELA DASHBOARDFACADE
        # ======================================================

        context["insights"] = []

        context["recommendations"] = []

        context["alerts"] = []

        return context

    # ==========================================================
    # DADOS CLIMÁTICOS DO MAPA
    # ==========================================================

    def _attach_climate_data(
        self,
        map_points,
    ):
        """
        Adiciona aos pontos geográficos os dados estruturados
        disponíveis para cada município.

        Dados meteorológicos:
            • temperatura;
            • umidade;
            • vento;
            • cobertura de nuvens;
            • precipitação;
            • horário da observação.

        Dados históricos de geada:
            • ocorrência;
            • quantidade de ocorrências;
            • quantidade total de registros históricos;
            • frequência histórica de geada;
            • quantidade de episódios de geada;
            • última data de ocorrência;
            • temperatura mínima da última ocorrência;
            • menor temperatura registrada em ocorrência de geada.

        Critério objetivo para ocorrência histórica de geada:

            temperatura_minima <= 0 °C

        Este método NÃO:
            • calcula FRI;
            • classifica risco;
            • calcula confiança;
            • gera alertas;
            • gera recomendações;
            • executa regras de Inteligência.

        Os indicadores históricos adicionados aqui constituem
        evidência estruturada para a etapa posterior da FrostRule.
        """

        if not map_points:

            return []

        municipality_names = [
            point.get("nome")
            for point in map_points
            if point.get("nome")
        ]

        if not municipality_names:

            return map_points

        # ======================================================
        # ÚLTIMA OBSERVAÇÃO METEOROLÓGICA
        # ======================================================

        observations = (
            WeatherObservation.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                station__municipio__nome__in=(
                    municipality_names
                )
            )
            .order_by(
                "station__municipio__nome",
                "-observation_time",
            )
        )

        latest_by_municipality = {}

        for observation in observations:

            municipality = (
                observation.station
                .municipio
                .nome
            )

            if municipality in (
                latest_by_municipality
            ):

                continue

            latest_by_municipality[
                municipality
            ] = observation

        # ======================================================
        # HISTÓRICO REAL DE GEADAS
        #
        # Fonte:
        # HistoricalWeatherDaily
        #
        # Somente registros persistidos são considerados.
        # Não utiliza previsão.
        # ======================================================

        historical_records = (
            HistoricalWeatherDaily.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                station__municipio__nome__in=(
                    municipality_names
                ),
                temperatura_minima__isnull=False,
            )
            .order_by(
                "station__municipio__nome",
                "data",
            )
        )

        historical_by_municipality = {}

        for record in historical_records:

            municipality = (
                record.station
                .municipio
                .nome
            )

            summary = historical_by_municipality.setdefault(
                municipality,
                {
                    "total_records": 0,
                    "frost_records": 0,
                    "frost_dates": [],
                    "last_date": None,
                    "last_minimum": None,
                    "minimum_temperature": None,
                },
            )

            summary["total_records"] += 1

            minimum = self._to_float(
                record.temperatura_minima
            )

            if minimum is None:
                continue

            if (
                summary["minimum_temperature"] is None
                or minimum < summary["minimum_temperature"]
            ):
                summary["minimum_temperature"] = minimum

            # Critério real de geada.
            if minimum <= 0:

                summary["frost_records"] += 1

                if record.data:
                    summary["frost_dates"].append(
                        record.data
                    )

                # O queryset está em ordem crescente; portanto,
                # o último registro de geada é o mais recente.
                summary["last_date"] = (
                    record.data.isoformat()
                    if record.data
                    else None
                )

                summary["last_minimum"] = minimum

        # ======================================================
        # ENRIQUECIMENTO DOS PONTOS
        # ======================================================

        enriched_points = []

        for point in map_points:

            enriched = dict(point)

            municipality = point.get(
                "nome"
            )

            observation = (
                latest_by_municipality.get(
                    municipality
                )
            )

            # ==================================================
            # PADRÃO SEM DADO
            # ==================================================

            enriched["temperature"] = None

            enriched["humidity"] = None

            enriched["wind_speed"] = None

            enriched["cloud_cover"] = None

            enriched["precipitation"] = None

            enriched["observation_time"] = None

            # ==================================================
            # DADOS DA OBSERVAÇÃO
            # ==================================================

            if observation:

                enriched["temperature"] = (
                    self._to_float(
                        observation.temperatura
                    )
                )

                enriched["humidity"] = (
                    self._to_float(
                        observation.umidade
                    )
                )

                enriched["wind_speed"] = (
                    self._to_float(
                        observation.velocidade_vento
                    )
                )

                enriched["cloud_cover"] = (
                    self._to_float(
                        observation.cobertura_nuvens
                    )
                )

                enriched["precipitation"] = (
                    self._to_float(
                        observation.precipitacao
                    )
                )

                if observation.observation_time:

                    enriched[
                        "observation_time"
                    ] = (
                        observation
                        .observation_time
                        .isoformat()
                    )

            # ==================================================
            # HISTÓRICO REAL DE GEADA
            # ==================================================

            historical = (
                historical_by_municipality.get(
                    municipality
                )
            )

            if historical is None:

                enriched["frost"] = False
                enriched["frost_occurrences"] = 0
                enriched["frost_last_date"] = None
                enriched["frost_temperature_minimum"] = None
                enriched["historical_frost"] = False

                # Evidência histórica estruturada.
                enriched["historical_total_days"] = 0
                enriched["historical_frost_days"] = 0
                enriched["historical_frost_frequency"] = 0.0
                enriched["historical_frost_episodes"] = 0
                enriched["historical_min_temperature"] = None

            else:

                frost_dates = historical["frost_dates"]
                total_days = historical["total_records"]
                frost_days = historical["frost_records"]

                enriched["frost"] = (
                    frost_days > 0
                )

                enriched["frost_occurrences"] = frost_days
                enriched["frost_last_date"] = historical["last_date"]
                enriched["frost_temperature_minimum"] = historical["last_minimum"]
                enriched["historical_frost"] = (
                    frost_days > 0
                )

                enriched["historical_total_days"] = total_days
                enriched["historical_frost_days"] = frost_days
                enriched["historical_frost_frequency"] = (
                    frost_days / total_days
                    if total_days > 0
                    else 0.0
                )
                enriched["historical_frost_episodes"] = (
                    self._count_frost_episodes(
                        frost_dates
                    )
                )
                enriched["historical_min_temperature"] = (
                    historical["minimum_temperature"]
                )

            enriched_points.append(
                enriched
            )

        return enriched_points

    # ==========================================================
    # EPISÓDIOS HISTÓRICOS DE GEADA
    # ==========================================================

    @staticmethod
    def _count_frost_episodes(
        frost_dates,
    ):
        """
        Conta episódios distintos de geada.

        Dias consecutivos pertencem ao mesmo episódio.
        Dias separados por pelo menos um dia sem geada
        iniciam novo episódio.

        Não calcula risco. Apenas estrutura a evidência
        histórica para a camada de Inteligência.
        """

        if not frost_dates:
            return 0

        ordered_dates = sorted(
            set(frost_dates)
        )

        episodes = 1
        previous_date = ordered_dates[0]

        for current_date in ordered_dates[1:]:

            if current_date != previous_date + timedelta(days=1):
                episodes += 1

            previous_date = current_date

        return episodes

    # ==========================================================
    # CONVERSÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _to_float(
        value,
    ):

        if value is None:

            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None