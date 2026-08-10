"""
AgroClima Café

Dashboard Facade

Responsável por integrar os serviços da Dashboard
com a camada de Inteligência.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.2
"""

from dashboard.services.dashboard_service import DashboardService
from core.intelligence.engine import IntelligenceEngine


class DashboardFacade:
    """
    Camada de orquestração da Dashboard.

    Responsável por:

    - Obter os dados estruturados
    - Preparar o contexto da Inteligência
    - Executar a Inteligência
    - Consolidar o contexto final enviado ao Template
    """

    def __init__(self):
        self.dashboard_service = DashboardService()
        self.intelligence = IntelligenceEngine()

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def get_dashboard_data(self):
        """
        Retorna o contexto completo utilizado pela Dashboard.
        """

        # ======================================================
        # DADOS ESTRUTURADOS
        # ======================================================

        context = self.dashboard_service.get_dashboard()

        # ======================================================
        # KPIs
        # ======================================================

        kpis = context.get(
            "kpis",
            {}
        )

        # ======================================================
        # CONTEXTO DA INTELIGÊNCIA
        # ======================================================

        intelligence_context = {
            "temperature": kpis.get(
                "temperature"
            ),

            "humidity": kpis.get(
                "humidity"
            ),

            "wind_speed": kpis.get(
                "wind_speed"
            ),

            "cloud_cover": kpis.get(
                "cloud_cover"
            ),

            "altitude": kpis.get(
                "altitude"
            ),

            "historical_frost": kpis.get(
                "historical_frost"
            ),

            "analysis_date": kpis.get(
                "analysis_date"
            ),
        }

        # ======================================================
        # INTELIGÊNCIA
        # ======================================================

        intelligence = self.intelligence.process(
            intelligence_context
        )

        # ======================================================
        # FROST RISK INDEX
        # ======================================================

        context["frost"] = intelligence.get(
            "frost",
            {
                "score": 0,
                "severity": "none",
                "confidence": 0,
                "factors": [],
            },
        )

        # ======================================================
        # RESULTADOS DAS REGRAS
        # ======================================================

        context["rule_results"] = intelligence.get(
            "rule_results",
            [],
        )

        # ======================================================
        # INSIGHTS
        # ======================================================

        context["insights"] = intelligence.get(
            "insights",
            [],
        )

        # ======================================================
        # RECOMENDAÇÕES
        # ======================================================

        context["recommendations"] = intelligence.get(
            "recommendations",
            [],
        )

        # ======================================================
        # ALERTAS
        # ======================================================

        context["alerts"] = intelligence.get(
            "alerts",
            [],
        )

        # ======================================================
        # EXPLICABILIDADE
        # ======================================================

        context["explainability"] = intelligence.get(
            "explainability",
            {},
        )

        return context