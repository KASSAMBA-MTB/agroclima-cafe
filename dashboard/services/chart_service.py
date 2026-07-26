"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: chart_service.py

Descrição.......:
Serviço responsável pelo fornecimento dos dados utilizados pelos gráficos
do Dashboard Principal.

Versão..........: 2.0
===============================================================================
"""

from clima.services.history_service import HistoryService
from municipios.models import Municipio


class ChartService:
    """
    Serviço responsável pelos dados históricos utilizados
    nos gráficos da Dashboard.
    """

    def __init__(self):

        self.history = HistoryService()

    # ==========================================================
    # DADOS DO GRÁFICO
    # ==========================================================

    def get_chart(self, days=7):

        municipio = Municipio.objects.first()

        if municipio is None:

            return self._empty()

        data = self.history.chart_data(

            municipio,

            days

        )

        return {

            "dias": data.get("dias", []),

            "temperatura": data.get("temperatura", []),

            "precipitacao": data.get("precipitacao", []),

            "umidade": data.get("umidade", []),

            # Preparação para futuras versões
            "vento": data.get("vento", []),

            "indice_agroclima": data.get("indice_agroclima", [])

        }

    # ==========================================================
    # RETORNO PADRÃO
    # ==========================================================

    def _empty(self):

        return {

            "dias": [],

            "temperatura": [],

            "precipitacao": [],

            "umidade": [],

            "vento": [],

            "indice_agroclima": []

        }