"""
==========================================================
AgroClima Café

Intelligence Engine

==========================================================
"""

from core.intelligence.rules.frost_rule import FrostRule


class RuleEngine:
    """
    Responsável por registrar e executar regras.
    """

    def __init__(self):
        self.rules = []

    def register(self, rule):
        self.rules.append(rule)

    def evaluate(self, context):

        results = []

        for rule in self.rules:

            result = rule.evaluate(context)

            if result is not None:
                results.append(result)

        return results


class IntelligenceEngine:
    """
    Motor central da camada de inteligência.
    """

    def __init__(self):

        self.engine = RuleEngine()

        self._register_rules()

    def _register_rules(self):

        self.engine.register(
            FrostRule()
        )

    def evaluate(self, context):

        return self.engine.evaluate(context)