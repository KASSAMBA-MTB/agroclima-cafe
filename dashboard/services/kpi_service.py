"""
==========================================================
AgroClima Café

KPI Service

Responsável pelos indicadores exibidos
no Dashboard Executivo.

Todos os KPIs devem ser obtidos através
dos motores do Core Platform.

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from core.intelligence.agroclima_index import AgroClimaIndex


class KPIService:

    """
    Serviço responsável pelos KPIs do Dashboard.
    """

    def __init__(self):

        self.iac = AgroClimaIndex()

    def get_kpis(self):

        """
        Calcula os KPIs do Dashboard.

        Nesta primeira versão os valores ainda
        são simulados.

        Posteriormente serão provenientes do
        Open-Meteo + PostgreSQL.
        """

        agroclima = self.iac.calculate(

            temperature=18.4,

            humidity=72,

            precipitation=28,

            frost_level="low",

            hail_level="low"

        )

        return {

            "temperatura_media": "18,4°C",

            "geadas": 1,

            "precipitacao": "28 mm",

            "granizo": 0,

            "municipios": 24,

            "indice_agroclima": agroclima["index"],

            "classificacao_agroclima": agroclima["classification"],

            "cor_agroclima": agroclima["color"],

            "icone_agroclima": agroclima["icon"],

            "scores": agroclima["scores"]

        }