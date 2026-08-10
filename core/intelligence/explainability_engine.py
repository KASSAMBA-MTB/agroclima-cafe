"""
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Projeto.........: AgroClima Café
Módulo..........: Inteligência
Arquivo.........: explainability_engine.py

Descrição.......:
Motor responsável por explicar a composição do Índice AgroClima.

Versão..........: 1.0
"""


class ExplainabilityEngine:
    """
    Explica a composição do Índice AgroClima.
    """

    WEIGHTS = {
        "temperature": 25,
        "humidity": 20,
        "precipitation": 18,
        "wind_speed": 12,
        "altitude": 10,
        "historical": 15,
    }

    # ==========================================================
    # PROCESSAMENTO
    # ==========================================================

    def process(self, context):
        """
        Retorna a composição dos pesos utilizados
        pelo Índice AgroClima.
        """

        return {
            "temperature": self.WEIGHTS["temperature"],
            "humidity": self.WEIGHTS["humidity"],
            "precipitation": self.WEIGHTS["precipitation"],
            "wind_speed": self.WEIGHTS["wind_speed"],
            "altitude": self.WEIGHTS["altitude"],
            "historical": self.WEIGHTS["historical"],
            "total": sum(
                self.WEIGHTS.values()
            ),
        }