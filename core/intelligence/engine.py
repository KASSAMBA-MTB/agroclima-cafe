"""
==========================================================
AgroClima Café

Rule Engine

Motor responsável por registrar e executar
todas as regras da plataforma.

==========================================================
"""

from typing import List


class RuleEngine:

    def __init__(self):

        self.rules: List = []

    def register(self, rule):

        self.rules.append(rule)

    def evaluate(self, context):

        results = []

        for rule in self.rules:

            result = rule.evaluate(context)

            if result is not None:

                results.append(result)

        return results