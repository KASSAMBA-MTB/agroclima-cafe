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

class RankingService:
    """
    Gera o Ranking dos Municípios baseado no
    Frost Risk Index (FRI).
    """

    # ==========================================================
    # RANKING
    # ==========================================================

    def get_ranking(self, map_points):

        ranking = []

        if not map_points:

            return ranking

        for point in map_points:

            try:

                fri = point.get(
                    "fri"
                )

                if fri is None:

                    continue

                severity = point.get(
                    "severity"
                )

                ranking.append({

                    "nome": point.get(
                        "nome"
                    ),

                    "uf": point.get(
                        "estado"
                    ),

                    "score": fri,

                    "severity": severity,

                    "color": self._severity_color(

                        severity

                    ),

                    "confidence": point.get(
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
