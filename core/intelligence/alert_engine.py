"""
AgroClima Café

Alert Engine

Responsável pela geração e priorização dos alertas
utilizados na Dashboard.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.8
"""

from datetime import datetime


class AlertEngine:
    """
    Converte recomendações em alertas estruturados.

    Recomendações com severity="none" permanecem como
    recomendações, mas não são tratadas como alertas.

    Somente low, medium, high e critical geram alertas ativos.
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

    LABELS = {
        "critical": "Crítico",
        "high": "Alto",
        "medium": "Moderado",
        "low": "Baixo",
        "none": "Normal",
    }

    ACTIVE_SEVERITIES = {
        "low",
        "medium",
        "high",
        "critical",
    }

    # ==========================================================
    # GERAÇÃO DE ALERTAS
    # ==========================================================

    def generate(self, recommendations):
        """
        Gera somente alertas ativos, ordenados por prioridade.

        A recomendação "none" continua disponível na camada
        RecommendationEngine, mas não entra na coleção alerts.
        """

        alerts = []

        for recommendation in recommendations:

            severity = str(
                recommendation.get(
                    "severity",
                    "none"
                )
            ).lower()

            # --------------------------------------------------
            # SITUAÇÃO NORMAL NÃO É ALERTA
            # --------------------------------------------------

            if severity not in self.ACTIVE_SEVERITIES:
                continue

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

                    "severity_label": self.LABELS.get(
                        severity,
                        "Desconhecido"
                    ),

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

                    "active": True,

                    "created_at": datetime.now(),
                }
            )

        # ------------------------------------------------------
        # ORDENAÇÃO
        # ------------------------------------------------------

        alerts.sort(
            key=lambda alert: (
                alert["priority"],
                -alert["score"],
            )
        )

        return alerts
