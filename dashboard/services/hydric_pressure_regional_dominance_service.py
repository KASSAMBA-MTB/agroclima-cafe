"""Interpreta a dominância dos estados na evidência regional MP-01.7."""

from copy import deepcopy

from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)


class HydricPressureRegionalDominanceService:
    """Resume a maior frequência sem alterar ou recalcular a evidência."""

    def analyze(self, synthesis_evidence):
        """Produz a dominância exclusivamente a partir da saída MP-01.7."""
        if not isinstance(synthesis_evidence, dict):
            return None

        regional_status = synthesis_evidence.get("regional_status")
        valid_count_original = synthesis_evidence.get("valid_count")
        state_counts = synthesis_evidence.get("state_counts")
        observed_states = synthesis_evidence.get("observed_states")
        source_participants = synthesis_evidence.get("participants", [])

        if (
            not isinstance(regional_status, str)
            or not isinstance(source_participants, list)
            or (state_counts is not None and not isinstance(state_counts, dict))
            or (observed_states is not None and not isinstance(observed_states, list))
        ):
            return None

        if not isinstance(valid_count_original, int) or isinstance(
            valid_count_original, bool
        ):
            valid_count_original = None

        if state_counts is None:
            state_counts = {}
        if observed_states is None:
            observed_states = []

        allowed_states = HydricPressureRegionalSynthesisService.ALLOWED_STATES
        ordered_states = []
        for state in observed_states:
            if state in allowed_states and state not in ordered_states:
                ordered_states.append(state)
        for state in state_counts:
            if state in allowed_states and state not in ordered_states:
                ordered_states.append(state)

        counts = {}
        excluded_count = 0
        for state, count in state_counts.items():
            if (
                not isinstance(count, int)
                or isinstance(count, bool)
                or count < 0
            ):
                return None

            if state in allowed_states:
                if count:
                    counts[state] = count
            else:
                # Null, empty, unknown and any label outside the MP-01.7
                # state vocabulary are excluded instead of becoming a new
                # hydric state.
                excluded_count += count

        counted_total = sum(counts.values())
        if (
            regional_status == "VALID"
            and not counts
            and valid_count_original is not None
        ):
            # The explicit VALID/no-classifiable-states case means every
            # source participant is excluded from state predominance.
            excluded_count = max(excluded_count, valid_count_original)

        denominator_divergence = (
            counted_total != valid_count_original
            if valid_count_original is not None
            else True
        )
        denominator_used = (
            valid_count_original
            if not denominator_divergence
            else counted_total
        )

        predominant_states = []
        predominant_counts = {}
        predominant_fractions = {}
        dominance_status = "UNDETERMINED"

        if regional_status == "INSUFFICIENT_DATA":
            dominance_status = "INSUFFICIENT_DATA"
        elif regional_status == "VALID" and counts and denominator_used:
            maximum = max(counts.values())
            predominant_states = [
                state for state in ordered_states if counts.get(state) == maximum
            ]
            predominant_counts = {
                state: counts[state] for state in predominant_states
            }
            predominant_fractions = {
                state: counts[state] / denominator_used
                for state in predominant_states
            }
            dominance_status = "DETERMINED"

        participants = deepcopy(source_participants) if counts else []

        source_provenance = synthesis_evidence.get("provenance")
        source_regional_context = synthesis_evidence.get(
            "source_regional_context"
        )

        return {
            "id": "HYDRIC_PRESSURE_REGIONAL_DOMINANCE_001",
            "version": "1.0",
            "interpretation_type": "REGIONAL_HYDRIC_PRESSURE_DOMINANCE",
            "regional_status": regional_status,
            "dominance_status": dominance_status,
            "predominant_states": predominant_states,
            "predominant_state_counts": predominant_counts,
            "predominant_state_fractions": predominant_fractions,
            "participants": participants,
            "excluded_null_or_unknown_count": excluded_count,
            "valid_count_original": valid_count_original,
            "denominator_used": denominator_used,
            "denominator_divergence": denominator_divergence,
            "source_evidence_id": synthesis_evidence.get("id"),
            "source_context_id": synthesis_evidence.get("source_context_id"),
            "source_rule_id": synthesis_evidence.get("source_rule_id"),
            "source_regional_context": deepcopy(source_regional_context),
            "provenance": deepcopy(source_provenance),
        }
