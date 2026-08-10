"""
AgroClima Café

Insight Engine

Transforma resultados das regras em insights
para exibição na Dashboard.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.7
"""

from datetime import datetime


class InsightEngine:
    """
    Responsável por converter resultados produzidos pelas
    Rules em informações compreensíveis ao usuário.
    """

    ICONS = {
        "none": "bi-check-circle-fill",
        "low": "bi-info-circle-fill",
        "medium": "bi-exclamation-circle-fill",
        "high": "bi-exclamation-triangle-fill",
        "critical": "bi-exclamation-octagon-fill",
    }

    COLORS = {
        "none": "success",
        "low": "info",
        "medium": "primary",
        "high": "warning",
        "critical": "danger",
    }

    TITLES = {
        "none": "Sem risco de geada",
        "low": "Baixo risco de geada",
        "medium": "Risco moderado de geada",
        "high": "Alto risco de geada",
        "critical": "Risco crítico de geada",
    }

    # ==========================================================
    # GERAÇÃO DE INSIGHTS
    # ==========================================================

    def generate(self, rule_results):
        """
        Converte os resultados das Rules em Insights.
        """

        insights = []

        for result in rule_results:
            severity = result.get(
                "severity",
                "none"
            )

            score = result.get(
                "score",
                0
            )

            confidence = result.get(
                "confidence",
                0
            )

            factors = result.get(
                "factors",
                []
            )

            created_at = result.get(
                "created_at",
                datetime.now()
            )

            insights.append(
                {
                    "id": result.get("id"),

                    "engine": result.get("engine"),

                    "title": self.TITLES.get(
                        severity,
                        "Situação climática"
                    ),

                    "description": self._description(
                        score,
                        severity
                    ),

                    "severity": severity,

                    "score": score,

                    "confidence": confidence,

                    "icon": self.ICONS.get(
                        severity,
                        "bi-info-circle-fill"
                    ),

                    "color": self.COLORS.get(
                        severity,
                        "secondary"
                    ),

                    "factors": factors,

                    "created_at": created_at,
                }
            )

        return insights

    # ==========================================================
    # DESCRIÇÃO
    # ==========================================================

    def _description(
        self,
        score,
        severity
    ):
        """
        Gera uma descrição padronizada do FRI.
        """

        return (
            f"Frost Risk Index (FRI): {score} pontos. "
            f"Nível de risco: {severity.upper()}."
        )