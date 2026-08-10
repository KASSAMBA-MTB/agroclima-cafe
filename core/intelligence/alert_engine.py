"""
AgroClima Café

Alert Engine

Responsável pela geração e priorização dos alertas
utilizados na Dashboard.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.7
"""

from datetime import datetime


class AlertEngine:
    """
    Converte recomendações em alertas estruturados.
    """

    PRIORITY = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
        "none": 5,
    }

    ICONS = {
        "critical": "bi-exclamation-octagon-fill",
        "high": "bi-exclamation-triangle-fill",
        "medium": "bi-exclamation-circle-fill",
        "low": "bi-info-circle-fill",
        "none": "bi-check-circle-fill",
    }

    COLORS = {
        "critical": "danger",
        "high": "warning",
        "medium": "primary",
        "low": "info",
        "none": "success",
    }

    # ==========================================================
    # GERAÇÃO DE ALERTAS
    # ==========================================================

    def generate(self, recommendations):
        """
        Gera alertas ordenados por prioridade.
        """

        alerts = []

        for recommendation in recommendations:

            severity = recommendation.get(
                "severity",
                "none"
            )

            alerts.append(
                {
                    "id": recommendation.get(
                        "id"
                    ),

                    "engine": recommendation.get(
                        "engine"
                    ),

                    "title": recommendation.get(
                        "title"
                    ),

                    "message": recommendation.get(
                        "recommendation"
                    ),

                    "severity": severity,

                    "priority": self.PRIORITY.get(
                        severity,
                        99
                    ),

                    "score": recommendation.get(
                        "score",
                        0
                    ),

                    "confidence": recommendation.get(
                        "confidence",
                        0
                    ),

                    "icon": self.ICONS.get(
                        severity,
                        "bi-info-circle-fill"
                    ),

                    "color": self.COLORS.get(
                        severity,
                        "secondary"
                    ),

                    "factors": recommendation.get(
                        "factors",
                        []
                    ),

                    "active": severity != "none",

                    "created_at": datetime.now(),
                }
            )

        # ------------------------------------------------------
        # Ordenação
        # ------------------------------------------------------

        alerts.sort(
            key=lambda alert: (
                alert["priority"],
                -alert["score"],
            )
        )

        return alerts
    