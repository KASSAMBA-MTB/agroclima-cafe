"""
AgroClima CafÃ©

Hail Potential Rule â€” MP-01.11

Regra especialista de integraÃ§Ã£o do potencial meteorolÃ³gico de granizo
Ã  arquitetura BaseRule / RuleEngine.

Responsabilidades
-----------------
- consumir exclusivamente o HailPotentialService;
- adaptar HailPotentialContract para o contrato do RuleEngine;
- preservar CAPE, shear 925â€“500 hPa e CAPE-SHEAR;
- preservar provenance, drivers e data_quality;
- representar ausÃªncia de dados como INSUFFICIENT_DATA;
- nÃ£o criar classificaÃ§Ã£o normativa enquanto os limiares nÃ£o estiverem
  homologados;
- nÃ£o gerar score, probabilidade, alerta ou recomendaÃ§Ã£o;
- nÃ£o alterar FRI ou qualquer regra existente.

Canal
-----
context

A utilizaÃ§Ã£o de "context" impede que o resultado seja enviado
automaticamente ao InsightEngine ou ao AlertEngine.

VersÃ£o: 1.0
"""

from core.intelligence.base_rule import BaseRule
from core.intelligence.hail_potential_service import HailPotentialService
from core.intelligence.hail_potential_experimental_evaluator import (
    HailPotentialExperimentalEvaluator,
)


class HailPotentialRule(BaseRule):
    """
    Integra o HailPotentialService ao contrato BaseRule.

    A regra Ã© deliberadamente fina: nÃ£o reproduz nenhum cÃ¡lculo do
    serviÃ§o e nÃ£o cria novos critÃ©rios meteorolÃ³gicos.
    """

    id = "HAIL_POTENTIAL_001"
    name = "Hail Potential Rule"
    description = (
        "AvaliaÃ§Ã£o do potencial meteorolÃ³gico de ambiente favorÃ¡vel "
        "a granizo, sem probabilidade ou classificaÃ§Ã£o normativa."
    )

    VERSION = "1.0"
    CHANNEL = "context"

    def __init__(self, service=None):
        self.service = service or HailPotentialService()
        self.experimental_evaluator = HailPotentialExperimentalEvaluator()

    def evaluate(self, context):
        """
        Executa o serviÃ§o canÃ´nico e adapta seu contrato para o RuleEngine.

        A ausÃªncia de dados permanece explicitamente como
        INSUFFICIENT_DATA.
        """

        result = self.service.evaluate(context)

        if result is None:
            return None

        if hasattr(result, "as_dict"):
            result = result.as_dict()

        if not isinstance(result, dict):
            return None

        # MP-01.12 adds diagnostics only; the canonical service remains the
        # sole calculator and no operational classification is introduced.
        result["experimental_evaluation"] = self.experimental_evaluator.evaluate(
            result
        )

        # ------------------------------------------------------
        # Identidade da regra
        # ------------------------------------------------------

        result["id"] = self.id
        result["rule_id"] = self.id
        result["rule_version"] = self.VERSION
        result["rule_implementation_version"] = self.VERSION
        result["canonical_method_version"] = (
            result.get("provenance", {}).get("input_canonical_method_version")
            or result.get("provenance", {}).get("input_method_version")
            or result.get("method_version")
        )
        experimental_evaluation = result.get("experimental_evaluation")
        if not isinstance(experimental_evaluation, dict):
            experimental_evaluation = {}

        result["experimental_diagnostic_version"] = (
            experimental_evaluation.get("experimental_diagnostic_version")
            or experimental_evaluation.get("method_version")
        )
        result["engine"] = self.name
        result["channel"] = self.CHANNEL

        # ------------------------------------------------------
        # Estado normativo
        # ------------------------------------------------------
        # Enquanto os limiares de classificaÃ§Ã£o nÃ£o estiverem
        # homologados, potential_level permanece None.
        # A regra nÃ£o inventa uma classificaÃ§Ã£o.
        # ------------------------------------------------------

        result.setdefault("potential_level", None)

        # ------------------------------------------------------
        # ProveniÃªncia da regra
        # ------------------------------------------------------

        provenance = result.get("provenance")

        if isinstance(provenance, dict):
            provenance = dict(provenance)
        else:
            provenance = {}

        provenance.setdefault(
            "rule_id",
            self.id,
        )
        provenance.setdefault(
            "rule_version",
            self.VERSION,
        )
        provenance.setdefault(
            "service",
            "HailPotentialService",
        )

        result["provenance"] = provenance

        # ------------------------------------------------------
        # Contexto municipal
        # ------------------------------------------------------

        if isinstance(context, dict):
            result.setdefault(
                "municipio_id",
                context.get("municipio_id"),
            )
            result.setdefault(
                "municipio_nome",
                context.get("municipio_nome"),
            )

        return result