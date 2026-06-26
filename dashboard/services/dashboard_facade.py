"""
==========================================================
AgroClima Café

Dashboard Facade

Responsável por fornecer todos os dados necessários
para o Dashboard.

A camada de apresentação (Views) nunca deve acessar
os Services diretamente.

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from dashboard.services.dashboard_service import DashboardService


class DashboardFacade:
    """
    Fachada do Dashboard.

    Centraliza o acesso aos serviços da plataforma.
    """

    def __init__(self):

        self.dashboard_service = DashboardService()

    def get_dashboard_context(self):
        """
        Retorna todo o contexto utilizado pela Home do Dashboard.
        """

        return self.dashboard_service.get_dashboard()

    def refresh(self):
        """
        Método preparado para futuras atualizações
        automáticas do Dashboard.

        Futuramente poderá:

        - atualizar cache;
        - sincronizar Open-Meteo;
        - recalcular IAC;
        - atualizar Ranking;
        - atualizar Insights.
        """

        return self.get_dashboard_context()