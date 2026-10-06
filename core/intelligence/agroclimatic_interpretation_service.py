"""
AgroClima Café

MP-01.10 — AgroclimaticInterpretationService

Responsabilidade:
    Materializar a interpretação canônica a partir de um resultado
    de regra já produzido pela camada de Inteligência.

Princípios:
    - não executa regras;
    - não calcula indicadores;
    - não recalcula FRI;
    - não calcula pressão hídrica;
    - não cria severidade/confidence;
    - não mistura municípios;
    - preserva proveniência e temporalidade já disponíveis;
    - ausência permanece ausência;
    - não exige uma versão que a regra de origem não forneceu.
"""


class AgroclimaticInterpretationService:
    """
    Converte um resultado de regra já produzido para o contrato
    AgroclimaticInterpretation.

    A classe é deliberadamente passiva: não executa RuleEngine,
    não consulta fontes externas e não cria semântica que não esteja
    presente no resultado recebido.
    """

    VERSION = "1.1"
    CONTRACT_VERSION = "1.2"

    def build(self, rule_result, context=None):
        """
        Materializa uma única interpretação.

        A identidade mínima exigida é o identificador da regra.
        A rule_version é preservada quando existir, mas sua ausência
        permanece como ausência e não impede a materialização.

        Retorna None quando o resultado não possui rule_id.
        """

        if not isinstance(rule_result, dict):
            return None

        context = context if isinstance(context, dict) else {}

        rule_id = rule_result.get("rule_id") or rule_result.get("id")
        rule_version = rule_result.get("rule_version")

        municipality_id = rule_result.get("municipality_id")
        if municipality_id is None:
            municipality_id = rule_result.get("municipio_id")
        if municipality_id is None:
            municipality_id = context.get("municipality_id")
        if municipality_id is None:
            municipality_id = context.get("municipio_id")

        if not rule_id:
            return None

        analysis_date = (
            rule_result.get("analysis_date")
            if rule_result.get("analysis_date") is not None
            else context.get("analysis_date")
        )

        interpretation_id = (
            rule_result.get("interpretation_id")
            or f"{rule_id}:{municipality_id or 'unknown'}:"
            f"{analysis_date or 'unknown'}"
        )

        return {
            # Preserve the complete result already produced by the rule and
            # coordinator. The canonical fields below remain authoritative
            # where their names overlap; no rule semantics are recalculated.
            **rule_result,
            "interpretation_id": interpretation_id,
            "contract_version": self.CONTRACT_VERSION,
            "service_version": self.VERSION,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "domain": rule_result.get("domain"),
            "status": rule_result.get("status"),
            "condition": rule_result.get("condition"),
            "event": rule_result.get("event"),
            "risk": rule_result.get("risk"),
            "indicator": rule_result.get("indicator"),
            "indicator_value": rule_result.get("indicator_value"),
            "unit": rule_result.get("unit"),
            "context": rule_result.get(
                "context",
                context.get("context"),
            ),
            "potential_impact": rule_result.get("potential_impact"),
            "data_status": rule_result.get(
                "data_status",
                context.get("data_status"),
            ),
            "confidence": rule_result.get("confidence"),
            "explainability": rule_result.get("explainability"),
            "observed_at": rule_result.get(
                "observed_at",
                context.get("observed_at"),
            ),
            "valid_until": rule_result.get(
                "valid_until",
                context.get("valid_until"),
            ),
            "analysis_date": analysis_date,
            "municipality_id": municipality_id,
            "provenance": rule_result.get("provenance"),
        }

    def build_many(self, rule_results, context=None):
        """
        Materializa interpretações individuais.

        Cada resultado é tratado isoladamente.
        Não existe agregação ou deduplicação.
        """

        if not isinstance(rule_results, list):
            return []

        interpretations = []

        for result in rule_results:
            interpretation = self.build(result, context)

            if interpretation is not None:
                interpretations.append(interpretation)

        return interpretations
