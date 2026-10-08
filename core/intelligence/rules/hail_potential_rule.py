"""
AgroClima Café

Hail Potential Rule — MP-01.11

Regra especialista de integração do potencial meteorológico de granizo
à arquitetura BaseRule / RuleEngine.

Responsabilidades
-----------------
- consumir exclusivamente o HailPotentialService;
- adaptar HailPotentialContract para o contrato do RuleEngine;
- preservar CAPE, shear 925–500 hPa e CAPE-SHEAR;
- preservar provenance, drivers e data_quality;
- representar ausência de dados como INSUFFICIENT_DATA;
- não criar classificação normativa enquanto os limiares não estiverem
  homologados;
- não gerar score, probabilidade, alerta ou recomendação;
- não alterar FRI ou qualquer regra existente.

Canal
-----
context

A utilização de "context" impede que o resultado seja enviado
automaticamente ao InsightEngine ou ao AlertEngine.

Versão: 1.0
"""

from core.intelligence.base_rule import BaseRule
from core.intelligence.hail_potential_service import HailPotentialService


class HailPotentialRule(BaseRule):
    """
    Integra o HailPotentialService ao contrato BaseRule.

    A regra é deliberadamente fina: não reproduz nenhum cálculo do
    serviço e não cria novos critérios meteorológicos.
    """

    id = "HAIL_POTENTIAL_001"
    name = "Hail Potential Rule"
    description = (
        "Avaliação do potencial meteorológico de ambiente favorável "
        "a granizo, sem probabilidade ou classificação normativa."
    )

    VERSION = "1.0"
    CHANNEL = "context"

    def __init__(self, service=None):
        self.service = service or HailPotentialService()

    def evaluate(self, context):
        """
        Executa o serviço canônico e adapta seu contrato para o RuleEngine.

        A ausência de dados permanece explicitamente como
        INSUFFICIENT_DATA.
        """

        result = self.service.evaluate(context)

        if result is None:
            return None

        if hasattr(result, "as_dict"):
            result = result.as_dict()

        if not isinstance(result, dict):
            return None

        # ------------------------------------------------------
        # Identidade da regra
        # ------------------------------------------------------

        result["id"] = self.id
        result["rule_id"] = self.id
        result["rule_version"] = self.VERSION
        result["engine"] = self.name
        result["channel"] = self.CHANNEL

        # ------------------------------------------------------
        # Estado normativo
        # ------------------------------------------------------
        # Enquanto os limiares de classificação não estiverem
        # homologados, potential_level permanece None.
        # A regra não inventa uma classificação.
        # ------------------------------------------------------

        result.setdefault("potential_level", None)

        # ------------------------------------------------------
        # Proveniência da regra
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
