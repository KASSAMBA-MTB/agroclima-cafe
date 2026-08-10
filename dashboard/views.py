"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: views.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
View principal da Dashboard Inteligente.

Responsável por:

    • Solicitar os dados à DashboardFacade
    • Encaminhar o contexto para o Template
    • Centralizar a renderização da Dashboard

Versão..........: 4.0
===============================================================================
"""

from django.shortcuts import render
from dashboard.services.dashboard_facade import DashboardFacade


class DashboardView:
    """
    View principal da Dashboard.
    """

    template_name = "dashboard/home_v3.html"

    def __init__(self):

        self.facade = DashboardFacade()

    def get_context(self):

        return self.facade.get_dashboard_data()

    def render(self, request):

        context = self.get_context()

        return render(
            request,
            self.template_name,
            context
        )


# ======================================================================
# VIEW PRINCIPAL
# ======================================================================

_dashboard = DashboardView()


def home(request):
    """
    Dashboard Principal.
    """

    return _dashboard.render(request)


# Compatibilidade

index = home
dashboard = home