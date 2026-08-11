"""
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

Versão..........: 3.3
"""

from clima.models import WeatherObservation

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

    A camada de Inteligência é responsabilidade da
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
        # RANKING
        # ======================================================

        context["ranking"] = (
            self.ranking_service.get_ranking()
        )

        # ======================================================
        # EVENTOS
        # ======================================================

        context["eventos"] = (
            self.events_service.get_events(kpis)
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
        Adiciona aos pontos geográficos os dados da última
        observação meteorológica disponível para cada município.

        Este método fornece somente dados estruturados.

        Não calcula FRI.
        Não classifica risco.
        Não executa regras de inteligência.
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

        observations = (
            WeatherObservation.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                station__municipio__nome__in=municipality_names
            )
            .order_by(
                "station__municipio__nome",
                "-observation_time",
            )
        )

        latest_by_municipality = {}

        for observation in observations:

            municipality = (
                observation.station.municipio.nome
            )

            if municipality in latest_by_municipality:
                continue

            latest_by_municipality[
                municipality
            ] = observation

        enriched_points = []

        for point in map_points:

            enriched = dict(point)

            municipality = point.get("nome")

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

                    enriched["observation_time"] = (
                        observation.observation_time.isoformat()
                    )

            enriched_points.append(
                enriched
            )

        return enriched_points

    # ==========================================================
    # CONVERSÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _to_float(value):

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None