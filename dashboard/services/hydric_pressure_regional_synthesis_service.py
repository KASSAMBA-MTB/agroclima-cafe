"""
AgroClima Café

Síntese da distribuição regional de Pressão Hídrica — MP-01.7.

Consome exclusivamente o contexto canônico produzido pela MP-01.6. Resume
os estados municipais observados, sem reconstruir resultados, atribuir novo
estado hídrico regional ou calcular índice de severidade.
"""

from collections import Counter


class HydricPressureRegionalSynthesisService:
    """Resume, de forma rastreável, a distribuição municipal da MP-01.6."""

    SOURCE_CONTEXT_ID = "HYDRIC_PRESSURE_001"
    SOURCE_CONTEXT_TYPE = "REGIONAL_HYDRIC_PRESSURE_CONTEXT"
    SYNTHESIS_ID = "HYDRIC_PRESSURE_REGIONAL_001"
    VERSION = "1.0"

    ALLOWED_STATES = frozenset(
        {
            "NO_DEFICIT_OBSERVED",
            "DEFICIT_OBSERVED",
            "EXCESS_OBSERVED",
            "DEFICIT_AND_EXCESS_OBSERVED",
        }
    )

    def synthesize(self, regional_context):
        """Gera distribuição somente a partir do resultado MP-01.6."""
        if not isinstance(regional_context, dict):
            return self._unavailable("INVALID_INPUT")

        if (
            regional_context.get("id") != self.SOURCE_CONTEXT_ID
            or regional_context.get("interpretation_type")
            != self.SOURCE_CONTEXT_TYPE
        ):
            return self._unavailable("INVALID_SOURCE_CONTEXT")

        municipalities = regional_context.get("municipalities")
        if not isinstance(municipalities, list):
            return self._unavailable("MISSING_MUNICIPAL_COLLECTION")

        valid_count = regional_context.get("valid_count")
        min_valid = regional_context.get("min_valid")
        source_status = regional_context.get("regional_status")

        if (
            not isinstance(valid_count, int)
            or isinstance(valid_count, bool)
            or valid_count != len(municipalities)
            or not isinstance(min_valid, int)
            or isinstance(min_valid, bool)
            or min_valid < 1
        ):
            return self._unavailable("INVALID_SOURCE_CONTEXT")

        if source_status not in {"VALID", "INSUFFICIENT_DATA"}:
            return self._unavailable("INVALID_SOURCE_CONTEXT")

        expected_status = "VALID" if valid_count >= min_valid else "INSUFFICIENT_DATA"
        if source_status != expected_status:
            return self._unavailable("INVALID_SOURCE_CONTEXT")

        seen = set()
        states = []
        for municipality in municipalities:
            if not isinstance(municipality, dict):
                return self._unavailable("INVALID_MUNICIPAL_COLLECTION")

            municipality_id = municipality.get("municipio_id")
            state = municipality.get("hydric_state")
            if (
                municipality_id in (None, "")
                or municipality.get("municipio_nome") is None
                or municipality.get("analysis_date") is None
                or state not in self.ALLOWED_STATES
                or not isinstance(municipality.get("provenance"), dict)
            ):
                return self._unavailable("INVALID_MUNICIPAL_COLLECTION")

            try:
                if municipality_id in seen:
                    return self._unavailable("DUPLICATE_MUNICIPALITY")
                seen.add(municipality_id)
            except TypeError:
                return self._unavailable("INVALID_MUNICIPAL_COLLECTION")

            states.append(state)

        state_counts = Counter(states)
        state_fractions = (
            {
                state: count / valid_count
                for state, count in state_counts.items()
            }
            if valid_count
            else None
        )

        source_provenance = regional_context.get("provenance")
        if isinstance(source_provenance, dict):
            source_provenance = dict(source_provenance)

        return {
            "id": self.SYNTHESIS_ID,
            "version": self.VERSION,
            "interpretation_type": "REGIONAL_HYDRIC_PRESSURE_DISTRIBUTION",
            "source_context_id": self.SOURCE_CONTEXT_ID,
            "source_rule_id": self.SOURCE_CONTEXT_ID,
            "regional_status": source_status,
            "valid_count": valid_count,
            "min_valid": min_valid,
            "state_counts": dict(state_counts),
            "state_fractions": state_fractions,
            "observed_states": list(state_counts),
            "participants": [
                {
                    "municipio_id": municipality["municipio_id"],
                    "municipio_nome": municipality["municipio_nome"],
                    "analysis_date": municipality["analysis_date"],
                    "source_rule_id": municipality.get("rule_id"),
                    "provenance": dict(municipality["provenance"]),
                }
                for municipality in municipalities
            ],
            "state_heterogeneity": (
                len(state_counts) > 1 if valid_count else None
            ),
            "regional_interpretation": "MUNICIPAL_STATE_DISTRIBUTION",
            "source_regional_context": {
                "id": regional_context.get("id"),
                "version": regional_context.get("version"),
                "analysis_date": self._common_date(municipalities),
                "provenance": source_provenance,
            },
            "provenance": {
                "source": "HydricPressureRegionalService",
                "source_context_id": self.SOURCE_CONTEXT_ID,
                "composition": "MP_01_6_CANONICAL_COLLECTION",
                "synthesis": "MP_01_7",
            },
        }

    def _unavailable(self, status):
        return {
            "id": self.SYNTHESIS_ID,
            "version": self.VERSION,
            "interpretation_type": "REGIONAL_HYDRIC_PRESSURE_DISTRIBUTION",
            "source_context_id": self.SOURCE_CONTEXT_ID,
            "source_rule_id": self.SOURCE_CONTEXT_ID,
            "regional_status": status,
            "valid_count": None,
            "min_valid": None,
            "state_counts": None,
            "state_fractions": None,
            "observed_states": None,
            "state_heterogeneity": None,
            "regional_interpretation": None,
            "source_regional_context": {},
            "provenance": {
                "source": "HydricPressureRegionalService",
                "source_context_id": self.SOURCE_CONTEXT_ID,
                "composition": "MP_01_6_CANONICAL_COLLECTION",
                "synthesis": "MP_01_7",
            },
        }

    @staticmethod
    def _common_date(municipalities):
        dates = []
        for municipality in municipalities:
            value = municipality.get("analysis_date")
            if value is not None and value not in dates:
                dates.append(value)

        return dates[0] if len(dates) == 1 else None
