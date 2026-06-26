"""
==========================================================
AgroClima Café

Frost Rule

Especialista em análise de risco de geadas.

==========================================================
"""

from datetime import datetime

from core.intelligence.base_rule import BaseRule


class FrostRule(BaseRule):

    id = "FROST_001"

    name = "Frost Rule"

    description = "Avalia risco de formação de geadas."

    def evaluate(self, context):

        temperatura = context.get("temperature", 20)

        altitude = context.get("altitude", 0)

        umidade = context.get("humidity", 0)

        vento = context.get("wind_speed", 0)

        if (

            temperatura <= 2

            and altitude >= 900

            and umidade >= 80

            and vento <= 8

        ):

            return {

                "id": self.id,

                "engine": self.name,

                "severity": "high",

                "score": 95,

                "title": "Risco Elevado de Geada",

                "description": (

                    "As condições atmosféricas são favoráveis "

                    "à formação de geadas."

                ),

                "recommendation": (

                    "Monitorar lavouras e adotar medidas "

                    "preventivas."

                ),

                "created_at": datetime.now()

            }

        return None