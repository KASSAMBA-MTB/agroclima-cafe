"""
AgroClima Café

Recommendation Engine

Responsável por transformar os Insights em
recomendações agronômicas para apoio à decisão.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.7
"""


class RecommendationEngine:
    """
    Gera recomendações a partir dos Insights.
    """

    RECOMMENDATIONS = {
        "none": {
            "title": "Situação Normal",
            "recommendation": (
                "Não há necessidade de ações preventivas. "
                "Manter o monitoramento climático."
            ),
        },

        "low": {
            "title": "Monitoramento Preventivo",
            "recommendation": (
                "Acompanhar a previsão meteorológica e observar "
                "a evolução das condições climáticas."
            ),
        },

        "medium": {
            "title": "Atenção",
            "recommendation": (
                "Reforçar o monitoramento da lavoura e preparar "
                "medidas preventivas caso haja agravamento."
            ),
        },

        "high": {
            "title": "Ação Preventiva",
            "recommendation": (
                "Adotar medidas de proteção contra geadas, "
                "principalmente em áreas de maior altitude."
            ),
        },

        "critical": {
            "title": "Ação Imediata",
            "recommendation": (
                "Executar imediatamente as estratégias de mitigação "
                "previstas para eventos severos de geada."
            ),
        },
    }

    # ==========================================================
    # GERAÇÃO DE RECOMENDAÇÕES
    # ==========================================================

    def generate(self, insights):
        """
        Gera recomendações baseadas na severidade dos Insights.
        """

        recommendations = []

        for insight in insights:

            severity = insight.get(
                "severity",
                "none"
            )

            template = self.RECOMMENDATIONS.get(
                severity,
                self.RECOMMENDATIONS["none"]
            )

            recommendations.append(
                {
                    "id": insight.get("id"),

                    "engine": insight.get("engine"),

                    "severity": severity,

                    "score": insight.get(
                        "score",
                        0
                    ),

                    "confidence": insight.get(
                        "confidence",
                        0
                    ),

                    "title": template["title"],

                    "recommendation": template[
                        "recommendation"
                    ],

                    "icon": insight.get("icon"),

                    "color": insight.get("color"),

                    "factors": insight.get(
                        "factors",
                        []
                    ),
                }
            )

        return recommendations