"""
==========================================================
AgroClima Café

Dashboard Facade

Responsável por integrar todos os serviços do Dashboard.

==========================================================
"""

from dashboard.services.kpi_service import KPIService
from dashboard.services.chart_service import ChartService
from dashboard.services.ranking_service import RankingService

from core.intelligence.engine import IntelligenceEngine
from core.intelligence.insight_engine import InsightEngine
from core.intelligence.recommendation_engine import RecommendationEngine
from core.intelligence.alert_engine import AlertEngine


class DashboardFacade:

    def __init__(self):

        self.kpi = KPIService()
        self.chart = ChartService()
        self.ranking = RankingService()

        self.engine = IntelligenceEngine()
        self.insight = InsightEngine()
        self.recommendation = RecommendationEngine()
        self.alert = AlertEngine()

    def get_dashboard_data(self):

        kpis = self.kpi.get_kpis()

        context = {

            "temperature": kpis["temperature"],
            "humidity": kpis["humidity"],
            "wind_speed": kpis["wind_speed"],
            "altitude": kpis["altitude"],
            "precipitation": kpis["precipitation"],

            "kpis": kpis,

        }

        # Executa todas as regras
        rule_results = self.engine.evaluate(context)

        # Gera Insights
        insights = self.insight.generate(rule_results)

        # Gera Recomendações
        recommendations = self.recommendation.generate(insights)

        # Gera Alertas
        alerts = self.alert.generate(recommendations)

        return {

            # KPIs
            "temperatura_media": kpis["temperatura_media"],
            "precipitacao": kpis["precipitacao"],
            "geadas": kpis["geadas"],
            "granizo": kpis["granizo"],
            "municipios": kpis["municipios"],

            # Índice AgroClima
            "indice_agroclima": kpis["indice_agroclima"],
            "classificacao_agroclima": kpis["classificacao_agroclima"],
            "cor_agroclima": kpis["cor_agroclima"],
            "icone_agroclima": kpis["icone_agroclima"],
            "scores": kpis["scores"],

            # Dashboard
            "chart": self.chart.get_chart(),
            "ranking": self.ranking.get_ranking(),

            # Inteligência
            "insights": insights,
            "recommendations": recommendations,
            "alerts": alerts,

        }