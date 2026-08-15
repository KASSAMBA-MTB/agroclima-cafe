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

Versão..........: 2.2
===============================================================================
"""

from clima.services.history_service import HistoryService


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

    def get_chart(
        self,
        days=7,
    ):
        """
        Mantém compatibilidade com chamadas existentes.

        Retorna o período solicitado.
        """

        data = self.history.chart_data(

            municipio=None,

            days=days,

        )

        return self._format(
            data
        )

    # ==========================================================
    # PERÍODOS DO DASHBOARD
    # ==========================================================

    def get_chart_periods(self):
        """
        Prepara todas as séries utilizadas pelos controles
        de período do gráfico.

        Hoje:
            somente o dia atual.

        7 dias:
            últimos 7 dias.

        30 dias:
            últimos 30 dias.

        Histórico:
            todo o histórico disponível no banco.
        """

        hoje = self.history.chart_data(

            municipio=None,

            days=1,

        )

        sete_dias = self.history.chart_data(

            municipio=None,

            days=7,

        )

        trinta_dias = self.history.chart_data(

            municipio=None,

            days=30,

        )

        historico = self.history.chart_data(

            municipio=None,

            days=None,

        )

        return {

            "hoje": self._format(
                hoje
            ),

            "7_dias": self._format(
                sete_dias
            ),

            "30_dias": self._format(
                trinta_dias
            ),

            "historico": self._format(
                historico
            ),

        }

    # ==========================================================
    # FORMATAÇÃO
    # ==========================================================

    @staticmethod
    def _format(
        data,
    ):

        if not data:

            return {
                "dias": [],
                "temperatura": [],
                "precipitacao": [],
                "umidade": [],
                "vento": [],
                "indice_agroclima": [],
            }

        return {

            "dias": data.get(
                "dias",
                [],
            ),

            "temperatura": data.get(
                "temperatura",
                [],
            ),

            "precipitacao": data.get(
                "precipitacao",
                [],
            ),

            "umidade": data.get(
                "umidade",
                [],
            ),

            "vento": data.get(
                "vento",
                [],
            ),

            "indice_agroclima": data.get(
                "indice_agroclima",
                [],
            ),

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

            "indice_agroclima": [],

        }