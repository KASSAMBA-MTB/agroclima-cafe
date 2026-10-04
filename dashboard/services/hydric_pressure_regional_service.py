"""
AgroClima Café

Composição municipal de Pressão Hídrica Agroclimática — MP-01.6.

Recebe exclusivamente resultados de HYDRIC_PRESSURE_001 já produzidos pelo
IntelligenceEngine. Preserva os resultados municipais e não recalcula dados,
não executa regras e não cria uma classificação hídrica regional.
"""

from collections import Counter


class HydricPressureRegionalService:
    """Valida, deduplica e organiza resultados hídricos municipais."""

    RULE_ID = "HYDRIC_PRESSURE_001"
    CONTEXT_TYPE = "REGIONAL_HYDRIC_PRESSURE_CONTEXT"
    MIN_VALID = 4
    VERSION = "1.0"

    REQUIRED_FIELDS = (
        "municipio_id",
        "municipio_nome",
        "analysis_date",
        "hydric_state",
        "pressure_status",
        "condition",
    )

    ALLOWED_STATES = frozenset(
        {
            "NO_DEFICIT_OBSERVED",
            "DEFICIT_OBSERVED",
            "EXCESS_OBSERVED",
            "DEFICIT_AND_EXCESS_OBSERVED",
        }
    )
    ALLOWED_PRESSURE_STATUS = frozenset({"OBSERVED", "NOT_OBSERVED"})
    ALLOWED_CONDITIONS = frozenset(
        {
            "DEFICIT_HIDRICO_OBSERVADO",
            "EXCEDENTE_HIDRICO_OBSERVADO",
            "SEM_DEFICIT_HIDRICO_OBSERVADO",
        }
    )

    def compose(self, results):
        """Compoe a coleção MP-01.6 sem alterar os resultados municipais."""
        if not isinstance(results, (list, tuple)):
            return self._empty_result("INVALID_INPUT")

        municipalities = []
        seen = set()

        for result in results:
            if not self._is_valid_result(result):
                continue

            municipality_id = result["municipio_id"]
            try:
                if municipality_id in seen:
                    continue
                seen.add(municipality_id)
            except TypeError:
                continue

            # Preserve the complete rule result, including future canonical
            # metrics and provenance fields not interpreted by this service.
            municipality = dict(result)
            if isinstance(result.get("provenance"), dict):
                municipality["provenance"] = dict(result["provenance"])
            if isinstance(result.get("factors"), list):
                municipality["factors"] = list(result["factors"])
            municipalities.append(municipality)

        state_counts = Counter(
            item["hydric_state"] for item in municipalities
        )
        valid_count = len(municipalities)

        return {
            "id": self.RULE_ID,
            "version": self.VERSION,
            "interpretation_type": self.CONTEXT_TYPE,
            "regional_status": (
                "VALID" if valid_count >= self.MIN_VALID
                else "INSUFFICIENT_DATA"
            ),
            "valid_count": valid_count,
            "min_valid": self.MIN_VALID,
            "hydric_states": dict(state_counts),
            "municipalities": municipalities,
            "provenance": {
                "source": "HydricPressureRule",
                "rule_id": self.RULE_ID,
                "composition": "MUNICIPAL_RESULTS_PRESERVED",
            },
        }

    def _is_valid_result(self, result):
        if not isinstance(result, dict):
            return False

        if (
            result.get("rule_id") != self.RULE_ID
            or result.get("id") != self.RULE_ID
        ):
            return False

        if any(result.get(field) is None for field in self.REQUIRED_FIELDS):
            return False

        if result.get("hydric_state") not in self.ALLOWED_STATES:
            return False

        if result.get("pressure_status") not in self.ALLOWED_PRESSURE_STATUS:
            return False

        if result.get("condition") not in self.ALLOWED_CONDITIONS:
            return False

        if result.get("municipio_id") == "":
            return False

        provenance = result.get("provenance")
        if (
            not isinstance(provenance, dict)
            or provenance.get("source") != "HydricBalanceService"
        ):
            return False

        return True

    def _empty_result(self, status):
        return {
            "id": self.RULE_ID,
            "version": self.VERSION,
            "interpretation_type": self.CONTEXT_TYPE,
            "regional_status": status,
            "valid_count": 0,
            "min_valid": self.MIN_VALID,
            "hydric_states": {},
            "municipalities": [],
            "provenance": {
                "source": "HydricPressureRule",
                "rule_id": self.RULE_ID,
                "composition": "MUNICIPAL_RESULTS_PRESERVED",
            },
        }
