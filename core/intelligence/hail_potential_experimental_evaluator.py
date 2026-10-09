"""
MP-01.12 — Avaliação diagnóstica experimental de potencial de granizo.

Componente isolado, não operacional e sem classificação por limiares.

Consome exclusivamente o resultado canônico produzido pelo
HailPotentialService. Não recalcula CAPE, cisalhamento ou CAPE-SHEAR.

Sem limiares regionais homologados, potential_level permanece None.
O componente organiza os eixos disponíveis, explicita lacunas do contrato
e identifica o resultado como experimental e não homologado.

Não gera probabilidade, score, alerta, recomendação, ocorrência observada
ou estimativa de dano. Não altera FRI, DashboardService ou IntelligenceEngine.
"""

from copy import deepcopy
from math import isfinite


EXPERIMENTAL_STATUS = "EXPERIMENTAL_NOT_HOMOLOGATED"
CLASSIFICATION_STATUS = "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS"
INSUFFICIENT_STATUS = "INSUFFICIENT_DATA"
ASSESSED_STATUS = "ASSESSED"


class HailPotentialExperimentalEvaluator:
    """Organiza os eixos meteorológicos sem atribuir nível normativo."""

    METHOD_VERSION = "MP-01.12.2"
    COMPONENT_ID = "HAIL_POTENTIAL_EXPERIMENTAL_EVALUATOR"

    def evaluate(self, canonical_result):
        """
        Recebe HailPotentialContract.as_dict() ou dicionário equivalente.

        A entrada é copiada para evitar mutação do contrato canônico.
        O componente valida a consistência mínima do contrato antes de
        produzir o diagnóstico experimental.
        """
        if not isinstance(canonical_result, dict):
            return self._insufficient(
                reason="CANONICAL_RESULT_INVALID",
                source_result=None,
            )

        source = deepcopy(canonical_result)
        assessment_status = source.get("assessment_status")

        if assessment_status != ASSESSED_STATUS:
            return self._insufficient(
                reason="CANONICAL_ASSESSMENT_NOT_ASSESSED",
                source_result=source,
            )

        data_quality = source.get("data_quality")
        if not isinstance(data_quality, dict):
            data_quality = {}

        missing = self._missing_variables(source, data_quality)

        if missing or data_quality.get("required_variables_complete") is False:
            return self._insufficient(
                reason="CANONICAL_CONTRACT_INCONSISTENT",
                source_result=source,
                missing_variables=missing,
            )

        drivers = source.get("drivers")
        if not isinstance(drivers, (list, tuple)):
            drivers = ()

        driver_values = {}
        for driver in drivers:
            if not isinstance(driver, dict):
                continue
            variable = driver.get("variable")
            if isinstance(variable, str) and variable:
                driver_values[variable] = {
                    "value": driver.get("observed_value"),
                    "unit": driver.get("unit"),
                    "role": driver.get("role"),
                    "rule_id": driver.get("rule_id"),
                    "rule_version": driver.get("rule_version"),
                }

        derived = source.get("derived")
        if not isinstance(derived, dict):
            derived = {}

        complementary = data_quality.get("complementary_variables")
        if not isinstance(complementary, dict):
            complementary = {}

        cape_evidence = driver_values.get("cape")
        cape_available = (
            isinstance(cape_evidence, dict)
            and self._is_numeric(cape_evidence.get("value"))
        )
        shear_value = derived.get("shear_925_500_ms")
        shear_available = self._is_numeric(shear_value)
        cape_shear_value = derived.get("cape_shear")
        cape_shear_available = self._is_numeric(cape_shear_value)

        axes = {
            "instability": {
                "status": "AVAILABLE" if cape_available else "UNAVAILABLE",
                "evidence": cape_evidence if cape_available else None,
                "interpretation": (
                    "Valor CAPE numérico recebido do serviço canônico; "
                    "nenhum limiar de classificação foi aplicado."
                    if cape_available
                    else "O contrato canônico não expôs um valor CAPE numérico válido."
                ),
            },
            "organization_shear": {
                "status": "AVAILABLE" if shear_available else "UNAVAILABLE",
                "evidence": {
                    "value": shear_value,
                    "unit": "m/s",
                    "source": "HailPotentialService",
                } if shear_available else None,
                "interpretation": (
                    "Cisalhamento vetorial 925–500 hPa numérico recebido "
                    "do serviço canônico; nenhum limiar foi aplicado."
                    if shear_available
                    else "O contrato canônico não expôs um cisalhamento numérico válido."
                ),
            },
            "combined_cape_shear": {
                "status": (
                    "AVAILABLE" if cape_shear_available else "UNAVAILABLE"
                ),
                "evidence": {
                    "value": cape_shear_value,
                    "unit": "J/kg*m/s",
                    "source": "HailPotentialService",
                } if cape_shear_available else None,
                "interpretation": (
                    "Indicador combinado informativo; não é probabilidade "
                    "e não classifica granizo isoladamente."
                    if cape_shear_available
                    else "O contrato canônico não expôs um CAPE-SHEAR numérico válido."
                ),
            },
            "thermodynamics": {
                "status": (
                    "AVAILABILITY_ONLY"
                    if complementary
                    else "NOT_EXPOSED_BY_CANONICAL_CONTRACT"
                ),
                "availability": deepcopy(complementary),
                "values": None,
                "interpretation": (
                    "O contrato canônico expõe somente a disponibilidade "
                    "das variáveis termodinâmicas complementares, não seus "
                    "valores. O componente não os reconstrói nem os busca "
                    "fora do contrato."
                    if complementary
                    else "O contrato recebido não expõe disponibilidade nem "
                    "valores termodinâmicos complementares."
                ),
            },
        }

        # Disponibilidade declarada não equivale a evidência termodinâmica
        # numérica. Portanto, AVAILABILITY_ONLY não satisfaz completude.
        diagnostics_complete = all(
            axis["status"] == "AVAILABLE"
            for axis in axes.values()
        )

        return {
            "component_id": self.COMPONENT_ID,
            "method_version": self.METHOD_VERSION,
            "evaluation_status": EXPERIMENTAL_STATUS,
            "classification_status": CLASSIFICATION_STATUS,
            "potential_level": None,
            "operational": False,
            "homologated": False,
            "assessment_status": assessment_status,
            "axes": axes,
            "diagnostics_complete": diagnostics_complete,
            "insufficient_variables": list(missing),
            "provenance": {
                "source": source.get("source"),
                "model": source.get("model"),
                "source_run": source.get("source_run"),
                "valid_from": source.get("valid_from"),
                "valid_to": source.get("valid_to"),
                "input_method_version": source.get("method_version"),
            },
            "data_quality": deepcopy(data_quality),
            "limitations": [
                "LIMIARES_REGIONAIS_NAO_HOMOLOGADOS",
                "CLASSIFICACAO_NORMATIVA_NAO_EXECUTADA",
                "SEM_PROBABILIDADE_SCORE_ALERTA_OU_DANO",
                "THERMODYNAMIC_VALUES_NOT_EXPOSED_BY_CANONICAL_CONTRACT",
            ],
        }

    @staticmethod
    def _is_numeric(value):
        """Aceita números finitos e strings numéricas; rejeita bool, NaN e infinito."""
        if value is None or isinstance(value, bool):
            return False
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return False
        return isfinite(number)

    @staticmethod
    def _missing_variables(source, data_quality):
        missing = source.get("missing_variables")
        if not isinstance(missing, (list, tuple, set)):
            missing = data_quality.get("missing_variables")
        if not isinstance(missing, (list, tuple, set)):
            return []
        return [
            item for item in missing
            if isinstance(item, str) and item
        ]

    def _insufficient(
        self,
        reason,
        source_result,
        missing_variables=None,
    ):
        source = source_result if isinstance(source_result, dict) else {}
        data_quality = source.get("data_quality")
        if not isinstance(data_quality, dict):
            data_quality = {}

        missing = (
            list(missing_variables)
            if missing_variables is not None
            else self._missing_variables(source, data_quality)
        )

        raw_status = source.get("assessment_status")
        assessment_status = (
            raw_status
            if raw_status in {ASSESSED_STATUS, INSUFFICIENT_STATUS}
            else INSUFFICIENT_STATUS
        )

        return {
            "component_id": self.COMPONENT_ID,
            "method_version": self.METHOD_VERSION,
            "evaluation_status": EXPERIMENTAL_STATUS,
            "classification_status": INSUFFICIENT_STATUS,
            "potential_level": None,
            "operational": False,
            "homologated": False,
            "assessment_status": assessment_status,
            "axes": {},
            "diagnostics_complete": False,
            "insufficient_variables": missing,
            "provenance": {
                "source": source.get("source"),
                "model": source.get("model"),
                "source_run": source.get("source_run"),
                "valid_from": source.get("valid_from"),
                "valid_to": source.get("valid_to"),
                "input_method_version": source.get("method_version"),
            },
            "data_quality": deepcopy(data_quality),
            "limitations": [
                "LIMIARES_REGIONAIS_NAO_HOMOLOGADOS",
                "CLASSIFICACAO_NORMATIVA_NAO_EXECUTADA",
                "ENTRADA_CANONICA_INSUFICIENTE_OU_INVALIDA",
            ],
            "reason": reason,
        }
