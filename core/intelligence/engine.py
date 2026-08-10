"""
AgroClima Café

Intelligence Engine

Motor central da camada de Inteligência.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.7
"""

from core.intelligence.rules.frost_rule import FrostRule
from core.intelligence.insight_engine import InsightEngine
from core.intelligence.recommendation_engine import RecommendationEngine
from core.intelligence.alert_engine import AlertEngine
from core.intelligence.explainability_engine import ExplainabilityEngine


class RuleEngine:
    """
    Responsável por registrar e executar todas as regras
    da camada de Inteligência.
    """

    def __init__(self):
        self.rules = []

    # ==========================================================
    # REGISTRO
    # ==========================================================

    def register(self, rule):
        """
        Registra uma regra no motor.
        """
        self.rules.append(rule)

    # ==========================================================
    # EXECUÇÃO
    # ==========================================================

    def evaluate(self, context):
        """
        Executa todas as regras registradas para o contexto
        informado.
        """

        results = []

        for rule in self.rules:
            result = rule.evaluate(context)

            if result is not None:
                results.append(result)

        return results


class IntelligenceEngine:
    """
    Motor central da Inteligência do AgroClima Café.

    Responsável por coordenar:

    - avaliação das regras;
    - geração de insights;
    - geração de recomendações;
    - geração de alertas;
    - explicabilidade das decisões.
    """

    def __init__(self):
        self.rule_engine = RuleEngine()

        self.insight_engine = InsightEngine()

        self.recommendation_engine = RecommendationEngine()

        self.alert_engine = AlertEngine()

        self.explainability_engine = ExplainabilityEngine()

        self._register_rules()

    # ==========================================================
    # REGISTRO DAS REGRAS
    # ==========================================================

    def _register_rules(self):
        """
        Registra as regras utilizadas pelo motor.
        """

        self.rule_engine.register(
            FrostRule()
        )

    # ==========================================================
    # PROCESSAMENTO CENTRAL
    # ==========================================================

    def process(self, context):
        """
        Executa o fluxo completo da camada de Inteligência.

        Fluxo:

            Contexto
                ↓
            RuleEngine
                ↓
            Insights
                ↓
            Recomendações
                ↓
            Alertas

        A explicabilidade é processada diretamente a partir
        do contexto original.
        """

        # ------------------------------------------------------
        # 1. Avaliação das regras
        # ------------------------------------------------------

        rule_results = self.rule_engine.evaluate(
            context
        )

        # ------------------------------------------------------
        # 2. Geração de insights
        # ------------------------------------------------------

        insights = self.insight_engine.generate(
            rule_results
        )

        # ------------------------------------------------------
        # 3. Geração de recomendações
        # ------------------------------------------------------

        recommendations = self.recommendation_engine.generate(
            insights
        )

        # ------------------------------------------------------
        # 4. Geração de alertas
        # ------------------------------------------------------

        alerts = self.alert_engine.generate(
            recommendations
        )

        # ------------------------------------------------------
        # 5. Explicabilidade
        # ------------------------------------------------------

        explainability = self.explainability_engine.process(
            context
        )

        # ------------------------------------------------------
        # 6. Resultado específico de geada
        # ------------------------------------------------------

        frost = {}

        if rule_results:
            frost = rule_results[0]

        # ------------------------------------------------------
        # 7. Resultado consolidado
        # ------------------------------------------------------

        return {
            "frost": frost,
            "rule_results": rule_results,
            "insights": insights,
            "recommendations": recommendations,
            "alerts": alerts,
            "explainability": explainability,
        }

    # ==========================================================
    # API PÚBLICA
    # ==========================================================

    def evaluate_frost(self, context):
        """
        Avalia especificamente o risco de geada.
        """

        return self.process(context).get(
            "frost",
            {}
        )

    def evaluate_insights(self, context):
        """
        Retorna os insights gerados para o contexto.
        """

        return self.process(context).get(
            "insights",
            []
        )

    def evaluate_recommendations(self, context):
        """
        Retorna as recomendações geradas para o contexto.
        """

        return self.process(context).get(
            "recommendations",
            []
        )

    def evaluate_alerts(self, context):
        """
        Retorna os alertas gerados para o contexto.
        """

        return self.process(context).get(
            "alerts",
            []
        )

    def evaluate_explainability(self, context):
        """
        Retorna as informações de explicabilidade.
        """

        return self.process(context).get(
            "explainability",
            {}
        )

    # ==========================================================
    # COMPATIBILIDADE
    # ==========================================================

    def evaluate(self, context):
        """
        Mantém compatibilidade com chamadas anteriores
        ao IntelligenceEngine.

        Retorna os resultados das regras.
        """

        return self.process(context).get(
            "rule_results",
            []
        )