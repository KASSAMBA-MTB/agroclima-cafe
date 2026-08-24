"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: frost_risk_service.py

Descrição.......:
Serviço de acesso único ao Frost Risk Index (FRI) para a camada Dashboard.

Responsabilidade:
    • Encaminhar o contexto oficial para o IntelligenceEngine.
    • Expor o resultado completo da Inteligência.
    • Expor especificamente o FRI utilizado por mapa, ranking, popups
      e demais componentes da Dashboard.

A regra de cálculo permanece centralizada em core.intelligence.
Nenhuma regra de FRI é implementada neste serviço.

Versão..........: 1.0
===============================================================================
"""

from core.intelligence.engine import IntelligenceEngine


class FrostRiskService:
    """
    Ponto único de acesso ao processamento do Frost Risk Index (FRI)
    na camada Dashboard.

    O serviço não calcula o FRI. Apenas centraliza o acesso ao
    IntelligenceEngine, garantindo que os consumidores utilizem o
    mesmo mecanismo de avaliação.
    """

    def __init__(self):

        self.intelligence = IntelligenceEngine()

    # ==========================================================
    # PROCESSAMENTO OFICIAL
    # ==========================================================

    def process(self, context):
        """
        Processa o contexto pelo motor oficial de Inteligência.
        """

        return self.intelligence.process(
            context
        )

    # ==========================================================
    # FRI
    # ==========================================================

    def evaluate_frost(self, context):
        """
        Retorna exclusivamente o resultado oficial de FRI.
        """

        result = self.process(
            context
        )

        return result.get(
            "frost",
            {}
        )
