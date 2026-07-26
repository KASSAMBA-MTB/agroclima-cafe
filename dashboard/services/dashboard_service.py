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
Serviço responsável por consolidar todos os dados do Dashboard Principal.

Versão..........: 2.1
===============================================================================
"""

from dashboard.services.kpi_service import KPIService
from dashboard.services.chart_service import ChartService
from dashboard.services.ranking_service import RankingService
from dashboard.services.alert_service import AlertService


class DashboardService:
    """
    Facade responsável por montar todo o contexto da Dashboard.
    """

    def __init__(self):

        self.kpi_service = KPIService()

        self.chart_service = ChartService()

        self.ranking_service = RankingService()

        self.alert_service = AlertService()

    # ======================================================================
    # DASHBOARD
    # ======================================================================

    def get_dashboard(self):

        context = {}

        # ==========================================================
        # KPIs
        # ==========================================================

        kpis = self.kpi_service.get_kpis()

        # Compatibilidade com templates antigos
        context.update(kpis)

        # Dashboard V3
        context["kpis"] = kpis

        # ==========================================================
        # ALERTAS
        # ==========================================================

        context["alerts"] = self.alert_service.get_alerts(kpis)

        # ==========================================================
        # GRÁFICOS
        # ==========================================================

        context["chart"] = self.chart_service.get_chart()

        # ==========================================================
        # RANKING
        # ==========================================================

        context["ranking"] = self.ranking_service.get_ranking()

        # ==========================================================
        # PRÓXIMOS MÓDULOS
        # ==========================================================

        context["eventos"] = []

        context["insights"] = []

        context["map_points"] = []

        return context