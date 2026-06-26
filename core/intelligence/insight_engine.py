"""
==========================================================
AgroClima Café

Insight Engine

Transforma resultados do Rule Engine em
insights apresentados ao usuário.

==========================================================
"""

from datetime import datetime


class InsightEngine:

    """
    Converte regras avaliadas em Insights.
    """

    def generate(self, rule_results):

        insights = []

        for result in rule_results:

            insights.append({

                "id": result["id"],

                "title": result["title"],

                "description": result["description"],

                "recommendation": result["recommendation"],

                "severity": result["severity"],

                "score": result["score"],

                "icon": self._icon(result["severity"]),

                "color": self._color(result["severity"]),

                "created_at": datetime.now()

            })

        return insights

    def _icon(self, severity):

        icons = {

            "low": "bi-check-circle-fill",

            "medium": "bi-info-circle-fill",

            "high": "bi-exclamation-triangle-fill",

            "critical": "bi-exclamation-octagon-fill"

        }

        return icons.get(severity, "bi-info-circle-fill")

    def _color(self, severity):

        colors = {

            "low": "success",

            "medium": "primary",

            "high": "warning",

            "critical": "danger"

        }

        return colors.get(severity, "secondary")