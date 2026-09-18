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
    • Normalizar o resultado oficial da Inteligência para o contrato
      utilizado pela camada Dashboard.
    • Expor o resultado completo da Inteligência.
    • Expor especificamente o FRI utilizado por mapa, ranking, popups
      e demais componentes da Dashboard.

A regra de cálculo permanece centralizada em core.intelligence.
Nenhuma regra de FRI é implementada neste serviço.

Versão..........: 1.1
===============================================================================
"""

from core.intelligence.engine import IntelligenceEngine


class FrostRiskService:
    """
    Ponto único de acesso ao processamento do Frost Risk Index (FRI)
    na camada Dashboard.

    O serviço não calcula o FRI. Apenas centraliza o acesso ao
    IntelligenceEngine e normaliza a saída da avaliação para que
    os consumidores da Dashboard utilizem uma nomenclatura única.
    """

    def __init__(self):

        self.intelligence = IntelligenceEngine()

        # Resultado completo da última execução.
        #
        # Importante:
        # evaluate_frost() e os demais consumidores devem utilizar
        # exatamente o mesmo resultado produzido por uma única chamada
        # ao IntelligenceEngine.
        self.last_result = {}

    # ==========================================================
    # PROCESSAMENTO OFICIAL
    # ==========================================================

    def process(self, context):
        """
        Processa o contexto pelo motor oficial de Inteligência.

        O IntelligenceEngine permanece responsável pelo cálculo do FRI,
        classificação, confiança e fatores.

        Este método apenas normaliza os nomes do resultado para o contrato
        canônico da Dashboard, preservando os campos legados existentes
        durante a migração.

        O resultado completo é armazenado em ``last_result`` para que
        evaluate_frost() e os consumidores da Dashboard não provoquem
        uma segunda execução do IntelligenceEngine.
        """

        result = self.intelligence.process(
            context
        )

        if not isinstance(result, dict):

            result = {
                "frost": {},
                "rule_results": [],
                "insights": [],
                "recommendations": [],
                "alerts": [],
                "explainability": {},
            }

        frost = result.get(
            "frost",
            {}
        )

        if not isinstance(frost, dict):

            frost = {}

        # ------------------------------------------------------
        # FRI CANÔNICO
        # ------------------------------------------------------
        # A FrostRule atual fornece o valor em ``score``.
        # Aqui ocorre somente a padronização do nome para ``fri``.
        # O valor numérico não é recalculado nem transformado.

        fri = frost.get(
            "fri"
        )

        if fri is None:

            fri = frost.get(
                "score"
            )

        frost["fri"] = fri

        # ------------------------------------------------------
        # FATORES CANÔNICOS
        # ------------------------------------------------------

        frost_factors = frost.get(
            "frost_factors"
        )

        if frost_factors is None:

            frost_factors = frost.get(
                "factors",
                []
            )

        frost["frost_factors"] = frost_factors

        # ------------------------------------------------------
        # CAMPOS CANÔNICOS GARANTIDOS
        # ------------------------------------------------------

        if "severity" not in frost:

            frost["severity"] = None

        if "confidence" not in frost:

            frost["confidence"] = None

        result["frost"] = frost

        # ------------------------------------------------------
        # COLEÇÕES DO RESULTADO CONSOLIDADO
        # ------------------------------------------------------

        if not isinstance(
            result.get("rule_results"),
            list
        ):

            result["rule_results"] = []

        if not isinstance(
            result.get("insights"),
            list
        ):

            result["insights"] = []

        if not isinstance(
            result.get("recommendations"),
            list
        ):

            result["recommendations"] = []

        if not isinstance(
            result.get("alerts"),
            list
        ):

            result["alerts"] = []

        if not isinstance(
            result.get("explainability"),
            dict
        ):

            result["explainability"] = {}

        # ------------------------------------------------------
        # CACHE DA ÚLTIMA AVALIAÇÃO
        # ------------------------------------------------------
        # O objeto armazenado é exatamente o resultado normalizado
        # desta execução. Nenhuma nova avaliação é realizada aqui.

        self.last_result = result

        return result

    # ==========================================================
    # FRI — API CANÔNICA
    # ==========================================================

    def evaluate_frost(self, context):
        """
        Retorna exclusivamente o resultado canônico de FRI.

        A avaliação utiliza a mesma execução do IntelligenceEngine
        realizada por process(). O resultado completo fica disponível
        em ``last_result``.

        Assim, o DashboardService pode consumir:
            evaluate_frost() -> FRI
            last_result     -> inteligência completa

        sem executar o motor duas vezes.
        """

        result = self.process(
            context
        )

        frost = result.get(
            "frost",
            {}
        )

        if not isinstance(
            frost,
            dict
        ):

            return {}

        return frost


# ============================================================================
# REGISTRO DE AUDITORIA — VERSÃO 1.1
# ============================================================================
#
# Objetivo:
#     alinhar o serviço à arquitetura de avaliação única do FRI.
#
# Fluxo canônico:
#
#     DashboardService
#           |
#           v
#     evaluate_frost(context)
#           |
#           v
#     process(context)
#           |
#           v
#     IntelligenceEngine
#           |
#           +--> frost
#           +--> rule_results
#           +--> insights
#           +--> recommendations
#           +--> alerts
#           +--> explainability
#           |
#           v
#     last_result
#
# Garantias:
#     - nenhuma regra de FRI neste serviço;
#     - nenhuma segunda execução para obtenção do resultado completo;
#     - FRI vem exclusivamente de frost;
#     - score não é convertido por cálculo;
#     - alertas permanecem provenientes da Inteligência;
#     - compatibilidade com process() preservada;
#     - evaluate_frost() continua disponível como API específica do FRI.
#
# Rejeição:
#     - cálculo de FRI neste serviço;
#     - segunda chamada ao IntelligenceEngine para o mesmo município;
#     - mistura de resultados de municípios distintos;
#     - descarte de rule_results/alerts/insights/recommendations.
# ============================================================================
