"""
AgroClima Café

Explainability Engine

Motor responsável por explicar os resultados efetivamente produzidos
pelas regras de Inteligência.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 2.0
"""


class ExplainabilityEngine:
    """
    Produz uma representação explicável dos resultados de Inteligência.

    Responsabilidades:

    - receber os resultados já produzidos pelas regras/coordenador;
    - preservar a identidade da regra;
    - preservar score, severity, confidence e fatores quando existentes;
    - preservar município e data quando existentes;
    - não recalcular FRI;
    - não recalcular severidade;
    - não criar evidência ausente;
    - não executar regras novamente.
    """

    VERSION = "2.0"

    def process(self, context, rule_results=None):
        """
        Explica os resultados já produzidos pela camada de Inteligência.

        O método não executa nenhuma regra. Quando rule_results não é
        fornecido, retorna uma estrutura vazia e mantém compatibilidade
        com chamadas antigas que forneçam somente context.
        """

        if not isinstance(context, dict):
            context = {}

        if not isinstance(rule_results, list):
            rule_results = []

        explanations = []

        for result in rule_results:
            if not isinstance(result, dict):
                continue

            explanation = {
                "rule_id": result.get("rule_id") or result.get("id"),
                "rule_version": result.get("rule_version"),
                "engine": result.get("engine"),
                "channel": result.get("channel"),
                "severity": result.get("severity"),
                "severity_label": result.get("severity_label"),
                "confidence": result.get("confidence"),
                "score": result.get("score"),
                "metric": result.get("metric"),
                "metric_value": result.get("metric_value"),
                "factors": list(result.get("factors") or []),
                "municipio_id": (
                    result.get("municipio_id")
                    if result.get("municipio_id") is not None
                    else context.get("municipio_id")
                ),
                "municipio_nome": (
                    result.get("municipio_nome")
                    if result.get("municipio_nome") is not None
                    else context.get("municipio_nome")
                ),
                "analysis_date": (
                    result.get("analysis_date")
                    if result.get("analysis_date") is not None
                    else context.get("analysis_date")
                ),
                "provenance": result.get("provenance"),
                "coordinator_version": result.get("coordinator_version"),
                "policy_version": result.get("policy_version"),
                "coordination_status": result.get("coordination_status"),
            }

            explanations.append(explanation)

        return {
            "version": self.VERSION,
            "municipio_id": context.get("municipio_id"),
            "municipio_nome": context.get("municipio_nome"),
            "analysis_date": context.get("analysis_date"),
            "rule_count": len(explanations),
            "rules": explanations,
        }
