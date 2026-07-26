"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: ranking_service.py

Descrição.......:
Serviço responsável pela geração do ranking dos municípios utilizando
o Índice AgroClima.

Versão..........: 2.0
===============================================================================
"""

from core.intelligence.agroclima_index import AgroClimaIndex
from clima.services.weather_service import WeatherService
from municipios.models import Municipio


class RankingService:
    """
    Gera o ranking dos municípios cadastrados.
    """

    def __init__(self):

        self.weather = WeatherService()
        self.iac = AgroClimaIndex()

    # ==========================================================
    # RANKING
    # ==========================================================

    def get_ranking(self):

        ranking = []

        municipios = Municipio.objects.all()

        for municipio in municipios:

            try:

                observation = self.weather.update_current_weather(
                    municipio
                )

                indice = self.iac.calculate(
                    temperature=float(observation.temperature),
                    humidity=float(observation.humidity),
                    precipitation=float(observation.precipitation),
                    frost_level="low",
                    hail_level="low",
                )

                ranking.append({

                    "municipio": municipio.nome,

                    "estado": "SP",

                    "indice": indice["index"],

                    "classificacao": indice["classification"],

                    "icone": indice["icon"],

                    "cor": indice["color"],

                    # Preparado para Dashboard V3
                    "tendencia": "estável"

                })

            except Exception:

                continue

        ranking.sort(

            key=lambda item: item["indice"],

            reverse=True

        )

        for posicao, item in enumerate(ranking, start=1):

            item["posicao"] = posicao

        return ranking