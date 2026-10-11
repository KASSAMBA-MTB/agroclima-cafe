"""
MP-01.12 — Avaliação diagnóstica experimental de potencial de granizo.

Componente isolado, não operacional e sem classificação por limiares.
Consome exclusivamente o resultado canônico produzido pelo HailPotentialService.
Não recalcula CAPE, cisalhamento ou CAPE-SHEAR.

Sem limiares regionais homologados, potential_level permanece None.
Não gera probabilidade, score, alerta, recomendação, ocorrência observada
ou estimativa de dano. Não altera FRI, DashboardService ou IntelligenceEngine.
"""

from copy import deepcopy
from math import isfinite


EXPERIMENTAL_STATUS = "EXPERIMENTAL_NOT_HOMOLOGATED"
CLASSIFICATION_STATUS = "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS"
INSUFFICIENT_STATUS = "INSUFFICIENT_DATA"
ASSESSED_STATUS = "ASSESSED"

_REQUIRED_DRIVER_VARIABLES = {"cape", "shear_925_500", "cape_shear"}
_REQUIRED_DERIVED_FIELDS = {"shear_925_500_ms", "cape_shear"}
_REQUIRED_COMPLEMENTARY_FIELDS = {
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
}


class HailPotentialExperimentalEvaluator:
    """Organiza os eixos meteorológicos sem atribuir nível normativo."""

    METHOD_VERSION = "MP-01.12.3"
    COMPONENT_ID = "HAIL_POTENTIAL_EXPERIMENTAL_EVALUATOR"

    def evaluate(self, canonical_result):
        """
        Recebe HailPotentialContract.as_dict() ou dicionário equivalente.

        Contratos ASSESSED precisam ter a estrutura produzida pelo MP-01.11.
        Valores numéricos inválidos permanecem evidências indisponíveis; campos
        estruturais ausentes ou malformados tornam o contrato inconsistente.
        A entrada é copiada para evitar mutação do contrato canônico.
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
            return self._contract_inconsistent(source)

        source_missing = source.get("missing_variables")
        quality_missing = data_quality.get("missing_variables")
        required_complete = data_quality.get("required_variables_complete")

        if (
            not isinstance(source_missing, list)
            or not self._is_string_list(source_missing)
            or not isinstance(quality_missing, list)
            or not self._is_string_list(quality_missing)
            or source_missing != quality_missing
            or source_missing
            or required_complete is not True
        ):
            return self._contract_inconsistent(
                source,
                missing_variables=self._safe_missing(source_missing, quality_missing),
            )

        # Validar a estrutura completa esperada no contrato ASSESSED do MP-01.11.
        drivers = source.get("drivers")
        if not isinstance(drivers, (list, tuple)):
            return self._contract_inconsistent(source)

        driver_values = {}
        for driver in drivers:
            if not isinstance(driver, dict):
                return self._contract_inconsistent(source)

            variable = driver.get("variable")
            if not isinstance(variable, str) or not variable:
                return self._contract_inconsistent(source)

            # Os drivers canônicos têm estes campos, mesmo quando o valor
            # observado é numericamente inválido e deve ficar UNAVAILABLE.
            required_driver_fields = {
                "observed_value", "unit", "rule_id", "rule_version", "role"
            }
            if not required_driver_fields.issubset(driver):
                return self._contract_inconsistent(source)

            # Structural metadata must be non-empty strings.
            # Valor observado inv?lido continua sendo evid?ncia indispon?vel.
            for metadata_field in ("unit", "role", "rule_id", "rule_version"):
                metadata_value = driver.get(metadata_field)
                if (
                    not isinstance(metadata_value, str)
                    or not metadata_value.strip()
                ):
                    return self._contract_inconsistent(source)

            if variable in driver_values:
                return self._contract_inconsistent(source)

            driver_values[variable] = {
                "value": driver.get("observed_value"),
                "unit": driver.get("unit"),
                "role": driver.get("role"),
                "rule_id": driver.get("rule_id"),
                "rule_version": driver.get("rule_version"),
            }

        # The MP-01.11 contract defines exactly these three drivers.
        if set(driver_values) != _REQUIRED_DRIVER_VARIABLES:
            return self._contract_inconsistent(source)

        derived = source.get("derived")
        if not isinstance(derived, dict):
            return self._contract_inconsistent(source)

        # Reject additional derived fields unless the contract is revised.
        if set(derived) != _REQUIRED_DERIVED_FIELDS:
            return self._contract_inconsistent(source)

        complementary = data_quality.get("complementary_variables")
        complementary_values = source.get("complementary_values")
        if not isinstance(complementary, dict):
            return self._contract_inconsistent(source)
        if set(complementary) != _REQUIRED_COMPLEMENTARY_FIELDS:
            return self._contract_inconsistent(source)
        if not all(isinstance(value, bool) for value in complementary.values()):
            return self._contract_inconsistent(source)
        if not isinstance(complementary_values, dict):
            return self._contract_inconsistent(source)
        if set(complementary_values) != _REQUIRED_COMPLEMENTARY_FIELDS:
            return self._contract_inconsistent(source)
        if not all(value is None or self._is_numeric(value) for value in complementary_values.values()):
            return self._contract_inconsistent(source)
        if any(complementary[name] != (complementary_values[name] is not None) for name in _REQUIRED_COMPLEMENTARY_FIELDS):
            return self._contract_inconsistent(source)

        cape_evidence = driver_values["cape"]
        cape_available = self._is_numeric(cape_evidence.get("value"))

        shear_value = derived["shear_925_500_ms"]
        shear_available = self._is_numeric(shear_value)

        cape_shear_value = derived["cape_shear"]
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
                "status": "AVAILABLE" if cape_shear_available else "UNAVAILABLE",
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
                    "AVAILABLE"
                    if all(self._is_numeric(complementary_values[name]) for name in _REQUIRED_COMPLEMENTARY_FIELDS)
                    else "PARTIAL"
                    if any(self._is_numeric(complementary_values[name]) for name in _REQUIRED_COMPLEMENTARY_FIELDS)
                    else "UNAVAILABLE"
                ),
                "availability": deepcopy(complementary),
                "values": {
                    name: {
                        "value": complementary_values[name],
                        "unit": "°C" if name in {"wet_bulb_temperature_2m", "temperature_850hPa"} else "%",
                    }
                    for name in sorted(_REQUIRED_COMPLEMENTARY_FIELDS)
                    if self._is_numeric(complementary_values[name])
                },
                "interpretation": (
                    "Valores termodinâmicos preservados pelo contrato canônico; nenhum limiar foi aplicado."
                    if all(self._is_numeric(complementary_values[name]) for name in _REQUIRED_COMPLEMENTARY_FIELDS)
                    else "Dados termodinâmicos parciais ou ausentes; ausência não é substituída por zero."
                ),
            },
        }

        # Disponibilidade declarada não equivale a evidência termodinâmica
        # numérica. Portanto, AVAILABILITY_ONLY nunca satisfaz completude.
        diagnostics_complete = all(
            axis["status"] == "AVAILABLE" for axis in axes.values()
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
            "insufficient_variables": [],
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
            ],
        }

    @staticmethod
    def _is_string_list(value):
        return all(isinstance(item, str) and bool(item) for item in value)

    @staticmethod
    def _safe_missing(source_missing, quality_missing):
        for candidate in (source_missing, quality_missing):
            if isinstance(candidate, list):
                return [
                    item for item in candidate
                    if isinstance(item, str) and item
                ]
        return []

    def _contract_inconsistent(self, source, missing_variables=None):
        return self._insufficient(
            reason="CANONICAL_CONTRACT_INCONSISTENT",
            source_result=source,
            missing_variables=missing_variables,
        )

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
        return HailPotentialExperimentalEvaluator._safe_missing(
            source.get("missing_variables"),
            data_quality.get("missing_variables"),
        )

    def _insufficient(self, reason, source_result, missing_variables=None):
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
