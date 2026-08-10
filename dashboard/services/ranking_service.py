"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: ranking_service.py

Descrição.......:
Serviço responsável pela geração do Ranking dos Municípios
utilizando o Frost Risk Index (FRI).

Toda a inteligência permanece centralizada em
core.intelligence.

Versão..........: 3.0
===============================================================================
"""

from clima.services.weather_service import WeatherService
from core.intelligence.engine import IntelligenceEngine
from municipios.models import Municipio


class RankingService:
    """
    Gera o Ranking dos Municípios baseado no
    Frost Risk Index (FRI).
    """

    def __init__(self):

        self.weather = WeatherService()

        self.intelligence = IntelligenceEngine()

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

                context = {

                    "temperature": float(
                        observation.temperature
                    ),

                    "humidity": float(
                        observation.humidity
                    ),

                    "wind_speed": float(
                        observation.wind_speed
                    ),

                    "cloud_cover": float(
                        observation.cloud_cover
                    ),

                    "altitude": municipio.altitude,

                    "historical_frost": False,

                    "analysis_date": observation.observation_time,

                }

                frost = self.intelligence.evaluate_frost(
                    context
                )

                ranking.append({

                    "nome": municipio.nome,

                    "uf": municipio.estado,

                    "score": frost.get(
                        "score",
                        0
                    ),

                    "severity": frost.get(
                        "severity",
                        "none"
                    ),

                    "color": self._severity_color(

                        frost.get(
                            "severity",
                            "none"
                        )

                    ),

                    "confidence": frost.get(
                        "confidence",
                        0
                    ),

                })

            except Exception:

                continue

        ranking.sort(

            key=lambda item: item["score"],

            reverse=True

        )

        return ranking

    # ==========================================================
    # CORES
    # ==========================================================

    @staticmethod
    def _severity_color(severity):

        colors = {

            "critical": "danger",

            "high": "warning",

            "medium": "primary",

            "low": "info",

            "none": "success"

        }

        return colors.get(

            severity,

            "secondary"

        )