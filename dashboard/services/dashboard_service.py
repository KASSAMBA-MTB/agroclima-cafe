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

Versão..........: 3.1
"""

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

        context["map_points"] = (
            self.map_service.get_points()
        )

        # ======================================================
        # CAMPOS PREENCHIDOS PELA DASHBOARDFACADE
        # ======================================================

        context["insights"] = []

        context["recommendations"] = []

        context["alerts"] = []

        return context