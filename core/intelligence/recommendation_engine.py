"""
==========================================================
AgroClima Café

Recommendation Engine

Responsável por transformar Insights em
ações recomendadas ao usuário.

==========================================================
"""


class RecommendationEngine:

    """
    Gera recomendações baseadas no Insight.
    """

    def generate(self, insights):

        recommendations = []

        for insight in insights:

            recommendations.append({

                "id": insight["id"],

                "title": insight["title"],

                "severity": insight["severity"],

                "recommendation": self._recommend(insight)

            })

        return recommendations

    def _recommend(self, insight):

        severity = insight["severity"]

        title = insight["title"]

        rules = {

            "Risco Elevado de Geada": {

                "low": [
                    "Realizar monitoramento preventivo."
                ],

                "medium": [
                    "Monitorar áreas de maior altitude.",
                    "Acompanhar previsões meteorológicas."
                ],

                "high": [
                    "Proteger mudas jovens.",
                    "Inspecionar áreas suscetíveis.",
                    "Preparar medidas emergenciais."
                ],

                "critical": [
                    "Acionar protocolo de contingência.",
                    "Executar plano de mitigação imediatamente."
                ]

            }

        }

        return rules.get(title, {}).get(

            severity,

            ["Nenhuma recomendação disponível."]

        )