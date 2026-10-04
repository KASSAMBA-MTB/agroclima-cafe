from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from core.intelligence.rules.hydric_pressure_rule import HydricPressureRule
from dashboard.services.dashboard_service import DashboardService
from dashboard.services.hydric_balance_service import HydricBalanceService
from dashboard.services.hydric_pressure_regional_dominance_service import (
    HydricPressureRegionalDominanceService,
)
from dashboard.services.hydric_pressure_regional_service import (
    HydricPressureRegionalService,
)
from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)


def municipal_result(municipality_id, state):
    deficit = state in {
        "DEFICIT_OBSERVED",
        "DEFICIT_AND_EXCESS_OBSERVED",
    }
    excess = state in {
        "EXCESS_OBSERVED",
        "DEFICIT_AND_EXCESS_OBSERVED",
    }
    return HydricPressureRule().evaluate(
        {
            "municipio_id": municipality_id,
            "municipio_nome": f"Município {municipality_id}",
            "analysis_date": date(2026, 10, 4),
            "hydric_balance_method": "REFERENCE_DAILY_RESERVOIR_BALANCE",
            "hydric_balance_scope": "MUNICIPAL",
            "hydric_balance_status": "VALID",
            "cad_mm": 100.0,
            "arm_final_mm": 40.0,
            "arm_final_percentual": 40.0,
            "deficit_hidrico_acumulado": 2.0 if deficit else 0.0,
            "excedente_hidrico_acumulado": 3.0 if excess else 0.0,
        }
    )


def synthesis_for(states):
    municipal_results = [
        municipal_result(index, state)
        for index, state in enumerate(states, start=1)
    ]
    regional = HydricPressureRegionalService().compose(municipal_results)
    return HydricPressureRegionalSynthesisService().synthesize(regional)


class HydricPressureRegionalDominanceTests(SimpleTestCase):
    def setUp(self):
        self.service = HydricPressureRegionalDominanceService()

    def test_simple_predominance_uses_original_valid_count(self):
        evidence = synthesis_for(
            [
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "NO_DEFICIT_OBSERVED",
                "NO_DEFICIT_OBSERVED",
                "EXCESS_OBSERVED",
            ]
        )

        output = self.service.analyze(evidence)

        self.assertEqual(output["regional_status"], "VALID")
        self.assertEqual(output["predominant_states"], ["DEFICIT_OBSERVED"])
        self.assertEqual(
            output["predominant_state_counts"], {"DEFICIT_OBSERVED": 3}
        )
        self.assertEqual(
            output["predominant_state_fractions"],
            {"DEFICIT_OBSERVED": 0.5},
        )
        self.assertEqual(output["valid_count_original"], 6)
        self.assertEqual(output["denominator_used"], 6)
        self.assertFalse(output["denominator_divergence"])
        self.assertEqual(output["excluded_null_or_unknown_count"], 0)
        self.assertEqual(output["participants"], evidence["participants"])
        self.assertEqual(output["source_rule_id"], "HYDRIC_PRESSURE_001")
        self.assertEqual(output["provenance"], evidence["provenance"])

    def test_ties_keep_first_observed_order_and_individual_fractions(self):
        evidence = synthesis_for(
            [
                "EXCESS_OBSERVED",
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "EXCESS_OBSERVED",
                "NO_DEFICIT_OBSERVED",
            ]
        )

        output = self.service.analyze(evidence)

        self.assertEqual(
            output["predominant_states"],
            ["EXCESS_OBSERVED", "DEFICIT_OBSERVED"],
        )
        self.assertEqual(
            output["predominant_state_counts"],
            {"EXCESS_OBSERVED": 2, "DEFICIT_OBSERVED": 2},
        )
        self.assertEqual(
            output["predominant_state_fractions"],
            {"EXCESS_OBSERVED": 0.4, "DEFICIT_OBSERVED": 0.4},
        )

    def test_null_and_unknown_distribution_entries_are_excluded(self):
        evidence = synthesis_for(
            [
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "NO_DEFICIT_OBSERVED",
                "EXCESS_OBSERVED",
            ]
        )
        evidence["state_counts"] = {
            "DEFICIT_OBSERVED": 2,
            None: 1,
            "UNKNOWN": 1,
        }
        evidence["observed_states"] = ["DEFICIT_OBSERVED"]
        evidence["participants"] = evidence["participants"][:2]

        output = self.service.analyze(evidence)

        self.assertEqual(output["excluded_null_or_unknown_count"], 2)
        self.assertEqual(output["predominant_states"], ["DEFICIT_OBSERVED"])
        self.assertEqual(output["valid_count_original"], 4)
        self.assertEqual(output["denominator_used"], 2)
        self.assertTrue(output["denominator_divergence"])
        self.assertEqual(output["participants"], evidence["participants"])

    def test_valid_without_classifiable_states_is_explicitly_undetermined(self):
        evidence = synthesis_for(
            ["DEFICIT_OBSERVED", "NO_DEFICIT_OBSERVED", "EXCESS_OBSERVED", "EXCESS_OBSERVED"]
        )
        evidence["state_counts"] = {}
        evidence["observed_states"] = []
        evidence["participants"] = []

        output = self.service.analyze(evidence)

        self.assertEqual(output["regional_status"], "VALID")
        self.assertEqual(output["dominance_status"], "UNDETERMINED")
        self.assertEqual(output["predominant_states"], [])
        self.assertEqual(output["predominant_state_counts"], {})
        self.assertEqual(output["predominant_state_fractions"], {})
        self.assertEqual(output["excluded_null_or_unknown_count"], 4)
        self.assertEqual(output["valid_count_original"], 4)
        self.assertEqual(output["denominator_used"], 0)
        self.assertTrue(output["denominator_divergence"])

    def test_insufficient_data_with_states_does_not_create_predominance(self):
        evidence = synthesis_for(
            [
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "NO_DEFICIT_OBSERVED",
            ]
        )

        output = self.service.analyze(evidence)

        self.assertEqual(evidence["regional_status"], "INSUFFICIENT_DATA")
        self.assertEqual(output["regional_status"], "INSUFFICIENT_DATA")
        self.assertEqual(output["dominance_status"], "INSUFFICIENT_DATA")
        self.assertEqual(output["predominant_states"], [])
        self.assertEqual(output["predominant_state_counts"], {})
        self.assertEqual(output["valid_count_original"], 3)
        self.assertEqual(output["denominator_used"], 3)
        self.assertEqual(output["participants"], evidence["participants"])

    def test_denominator_divergence_uses_observed_valid_state_total(self):
        evidence = synthesis_for(
            [
                "DEFICIT_OBSERVED",
                "DEFICIT_OBSERVED",
                "NO_DEFICIT_OBSERVED",
                "EXCESS_OBSERVED",
            ]
        )
        evidence["valid_count"] = 5

        output = self.service.analyze(evidence)

        self.assertEqual(output["valid_count_original"], 5)
        self.assertEqual(output["denominator_used"], 4)
        self.assertTrue(output["denominator_divergence"])
        self.assertEqual(
            output["predominant_state_fractions"],
            {"DEFICIT_OBSERVED": 0.5},
        )

    def test_missing_evidence_remains_absent(self):
        dashboard = DashboardService.__new__(DashboardService)
        dashboard.hydric_pressure_regional_dominance_service = self.service
        context = {"unrelated": "preserved"}

        result = dashboard._attach_hydric_pressure_regional_dominance(context)

        self.assertIs(result, context)
        self.assertNotIn("hydric_pressure_regional_dominance", context)

    def test_dashboard_consumes_real_synthesis_without_mutation_or_recalculation(self):
        results = [
            municipal_result(index, state)
            for index, state in enumerate(
                [
                    "DEFICIT_OBSERVED",
                    "DEFICIT_OBSERVED",
                    "NO_DEFICIT_OBSERVED",
                    "EXCESS_OBSERVED",
                ],
                start=1,
            )
        ]
        regional = HydricPressureRegionalService().compose(results)
        evidence = HydricPressureRegionalSynthesisService().synthesize(regional)
        snapshot = deepcopy(evidence)

        dashboard = DashboardService.__new__(DashboardService)
        dashboard.hydric_pressure_regional_dominance_service = (
            HydricPressureRegionalDominanceService()
        )
        context = {"hydric_pressure_regional_synthesis": evidence}

        balance = HydricBalanceService()
        rule = HydricPressureRule()
        original_balance_calculate = HydricBalanceService.calculate
        original_rule_evaluate = HydricPressureRule.evaluate
        original_analyze = dashboard.hydric_pressure_regional_dominance_service.analyze
        consumed = []

        def capture_evidence(argument):
            consumed.append((argument, deepcopy(argument)))
            return original_analyze(argument)

        with patch.object(
            HydricBalanceService,
            "calculate",
            autospec=True,
            side_effect=original_balance_calculate,
        ) as balance_spy:
            with patch.object(
                HydricPressureRule,
                "evaluate",
                autospec=True,
                side_effect=original_rule_evaluate,
            ) as rule_spy:
                # Positive controls prove each spy observes the public method.
                balance.calculate(
                    precipitation_series=[0.0],
                    eto_series=[0.0],
                    cad_mm=100.0,
                    initial_arm_mm=40.0,
                    scope="MUNICIPAL",
                )
                rule.evaluate(
                    {
                        "hydric_balance_method": (
                            "REFERENCE_DAILY_RESERVOIR_BALANCE"
                        ),
                        "hydric_balance_scope": "MUNICIPAL",
                        "hydric_balance_status": "VALID",
                        "cad_mm": 100.0,
                        "arm_final_mm": 40.0,
                    }
                )
                self.assertEqual(balance_spy.call_count, 1)
                self.assertEqual(rule_spy.call_count, 1)
                balance_spy.reset_mock()
                rule_spy.reset_mock()

                original_evidence = context[
                    "hydric_pressure_regional_synthesis"
                ]
                original_snapshot = deepcopy(original_evidence)
                dashboard.hydric_pressure_regional_dominance_service.analyze = (
                    capture_evidence
                )
                dashboard._attach_hydric_pressure_regional_dominance(context)

                self.assertEqual(balance_spy.call_count, 0)
                self.assertEqual(rule_spy.call_count, 0)

        consumed_evidence, consumed_snapshot = consumed[0]
        self.assertEqual(consumed_snapshot, snapshot)
        self.assertEqual(consumed_evidence, snapshot)
        self.assertEqual(original_evidence, original_snapshot)
        self.assertEqual(
            context["hydric_pressure_regional_synthesis"], snapshot
        )
        self.assertIn("hydric_pressure_regional_dominance", context)
        self.assertEqual(
            context["hydric_pressure_regional_dominance"]["regional_status"],
            "VALID",
        )
        self.assertEqual(
            context["hydric_pressure_regional_dominance"]["source_rule_id"],
            "HYDRIC_PRESSURE_001",
        )
