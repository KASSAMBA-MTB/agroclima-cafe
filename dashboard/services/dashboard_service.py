from dashboard.services.kpi_service import KPIService
from dashboard.services.chart_service import ChartService
from dashboard.services.ranking_service import RankingService


class DashboardService:

    def get_dashboard(self):

        context = {}

        context.update(KPIService().get_kpis())

        context["chart"] = ChartService().get_chart()

        context["ranking"] = RankingService().get_ranking()

        return context