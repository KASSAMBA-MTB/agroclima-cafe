"""
==========================================================
AgroClima Café

Alert Engine

Responsável por transformar recomendações em
alertas priorizados para o Dashboard.

Autor:
Walter Junio Pontes Teixeira

==========================================================
"""

from datetime import datetime


class AlertEngine:

    """
    Motor responsável pela geração dos alertas.
    """

    PRIORITY = {

        "critical": 1,

        "high": 2,

        "medium": 3,

        "low": 4

    }

    def generate(self, recommendations):

        alerts = []

        for recommendation in recommendations:

            severity = recommendation["severity"]

            alerts.append({

                "id": recommendation["id"],

                "title": recommendation["title"],

                "severity": severity,

                "priority": self.PRIORITY.get(severity, 99),

                "recommendations": recommendation["recommendation"],

                "icon": self._icon(severity),

                "color": self._color(severity),

                "created_at": datetime.now(),

                "expires": False

            })

        alerts.sort(

            key=lambda alert: alert["priority"]

        )

        return alerts

    def _icon(self, severity):

        icons = {

            "low": "bi-check-circle-fill",

            "medium": "bi-info-circle-fill",

            "high": "bi-exclamation-triangle-fill",

            "critical": "bi-exclamation-octagon-fill"

        }

        return icons.get(

            severity,

            "bi-info-circle-fill"

        )

    def _color(self, severity):

        colors = {

            "low": "success",

            "medium": "primary",

            "high": "warning",

            "critical": "danger"

        }

        return colors.get(

            severity,

            "secondary"

        )