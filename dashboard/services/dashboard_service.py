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
    • Não executar regras de Inteligência.

Versão..........: 3.5
===============================================================================
"""

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
            • última data de ocorrência;
            • temperatura mínima da última ocorrência.

        Critério objetivo para ocorrência histórica de geada:

            temperatura_minima <= 0 °C

        Este método NÃO:
            • calcula FRI;
            • classifica risco;
            • calcula confiança;
            • gera alertas;
            • gera recomendações;
            • executa regras de Inteligência.
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

        frost_records = (
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
                temperatura_minima__lte=0,
            )
            .order_by(
                "station__municipio__nome",
                "-data",
            )
        )

        frost_by_municipality = {}

        for record in frost_records:

            municipality = (
                record.station
                .municipio
                .nome
            )

            summary = frost_by_municipality.setdefault(
                municipality,
                {
                    "occurrences": 0,
                    "last_date": None,
                    "last_minimum": None,
                },
            )

            summary["occurrences"] += 1

            # O queryset está ordenado da ocorrência mais
            # recente para a mais antiga. Portanto, o primeiro
            # registro representa a última ocorrência registrada.
            if summary["last_date"] is None:

                summary["last_date"] = (
                    record.data.isoformat()
                    if record.data
                    else None
                )

                summary["last_minimum"] = (
                    self._to_float(
                        record.temperatura_minima
                    )
                )

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
            # GEADA HISTÓRICA REAL
            # ==================================================

            frost = frost_by_municipality.get(
                municipality
            )

            if frost is None:

                enriched["frost"] = False

                enriched["frost_occurrences"] = 0

                enriched["frost_last_date"] = None

                enriched[
                    "frost_temperature_minimum"
                ] = None

            else:

                enriched["frost"] = True

                enriched["frost_occurrences"] = (
                    frost["occurrences"]
                )

                enriched["frost_last_date"] = (
                    frost["last_date"]
                )

                enriched[
                    "frost_temperature_minimum"
                ] = frost["last_minimum"]

            enriched_points.append(
                enriched
            )

        return enriched_points

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