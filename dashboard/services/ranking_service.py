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
utilizando o Frost Risk Index (FRI) oficial da Dashboard.

O Ranking consome os mesmos pontos municipais estruturados utilizados
pelo mapa, e a avaliação do FRI é centralizada em FrostRiskService.
Toda a inteligência permanece centralizada em
core.intelligence.

Versão..........: 3.1
===============================================================================
"""

from dashboard.services.frost_risk_service import FrostRiskService


class RankingService:
    """
    Gera o Ranking dos Municípios baseado no
    Frost Risk Index (FRI).
    """

    def __init__(self):

        self.frost_risk = FrostRiskService()

    # ==========================================================
    # RANKING
    # ==========================================================

    def get_ranking(self, map_points):

        ranking = []

        if not map_points:

            return ranking

        for point in map_points:

            try:

                context = {

                    "temperature": point.get(
                        "temperature"
                    ),

                    "humidity": point.get(
                        "humidity"
                    ),

                    "wind_speed": point.get(
                        "wind_speed"
                    ),

                    "cloud_cover": point.get(
                        "cloud_cover"
                    ),

                    "altitude": point.get(
                        "altitude"
                    ),

                    "historical_frost": point.get(
                        "historical_frost"
                    ),

                    "historical_total_days": point.get(
                        "historical_total_days"
                    ),

                    "historical_frost_days": point.get(
                        "historical_frost_days"
                    ),

                    "historical_frost_frequency": point.get(
                        "historical_frost_frequency"
                    ),

                    "historical_frost_episodes": point.get(
                        "historical_frost_episodes"
                    ),

                    "historical_min_temperature": point.get(
                        "historical_min_temperature"
                    ),

                    "analysis_date": point.get(
                        "analysis_date"
                    ),

                }

                frost = self.frost_risk.evaluate_frost(
                    context
                )

                score = frost.get(
                    "score"
                )

                if score is None:

                    continue

                severity = frost.get(
                    "severity"
                )

                ranking.append({

                    "nome": point.get(
                        "nome"
                    ),

                    "uf": point.get(
                        "estado"
                    ),

                    "score": score,

                    "severity": severity,

                    "color": self._severity_color(

                        severity

                    ),

                    "confidence": frost.get(
                        "confidence"
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