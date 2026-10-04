from datetime import date

from django.test import SimpleTestCase

from core.intelligence.rules.hydric_pressure_rule import HydricPressureRule
from dashboard.services.hydric_pressure_regional_service import (
    HydricPressureRegionalService,
)
from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)


def municipal_result(municipality_id, state="NO_DEFICIT_OBSERVED"):
    deficit = (
        6.5
        if state in {"DEFICIT_OBSERVED", "DEFICIT_AND_EXCESS_OBSERVED"}
        else 0.0
    )
    excess = (
        3.0
        if state in {"EXCESS_OBSERVED", "DEFICIT_AND_EXCESS_OBSERVED"}
        else 0.0
    )
    return HydricPressureRule().evaluate(
        {
            "municipio_id": municipality_id,
            "municipio_nome": f"Município {municipality_id}",
            "analysis_date": date(2026, 9, 30),
            "hydric_balance_method": "REFERENCE_DAILY_RESERVOIR_BALANCE",
            "hydric_balance_scope": "MUNICIPAL",
            "hydric_balance_status": "VALID",
            "cad_mm": 100.0,
            "arm_final_mm": 42.0,
            "arm_final_percentual": 42.0,
            "deficit_hidrico_acumulado": deficit,
            "deficit_hidrico_mm": deficit,
            "excedente_hidrico_acumulado": excess,
            "excedente_hidrico_mm": excess,
        }
    )


class HydricPressureRegionalServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = HydricPressureRegionalService()

    def test_deduplicates_and_preserves_complete_municipal_result(self):
        first = municipal_result(1, "DEFICIT_OBSERVED")
        first["future_canonical_metric"] = {"value": None}
        duplicate = dict(first, arm_final_mm=1.0)
        results = [
            first,
            municipal_result(2),
            municipal_result(3),
            municipal_result(4),
            duplicate,
            {"rule_id": "OTHER_RULE", "id": "OTHER_RULE"},
            dict(municipal_result(5), analysis_date=None),
        ]

        context = self.service.compose(results)

        self.assertEqual(context["regional_status"], "VALID")
        self.assertEqual(context["min_valid"], 4)
        self.assertEqual(context["valid_count"], 4)
        self.assertEqual(
            [item["municipio_id"] for item in context["municipalities"]],
            [1, 2, 3, 4],
        )
        preserved = context["municipalities"][0]
        self.assertEqual(preserved["analysis_date"], date(2026, 9, 30))
        self.assertEqual(preserved["hydric_state"], "DEFICIT_OBSERVED")
        self.assertEqual(preserved["arm_final_mm"], 42.0)
        self.assertEqual(preserved["deficit_hidrico_mm"], 6.5)
        self.assertIsNone(preserved["future_canonical_metric"]["value"])
        self.assertEqual(
            preserved["provenance"]["source"], "HydricBalanceService"
        )
        self.assertEqual(preserved["factors"], first["factors"])

    def test_less_than_four_valid_municipalities_is_insufficient(self):
        context = self.service.compose(
            [municipal_result(1), municipal_result(2), municipal_result(3)]
        )

        self.assertEqual(context["regional_status"], "INSUFFICIENT_DATA")
        self.assertEqual(context["valid_count"], 3)
        self.assertEqual(context["min_valid"], 4)

    def test_invalid_input_does_not_invent_municipal_results(self):
        context = self.service.compose(None)

        self.assertEqual(context["regional_status"], "INVALID_INPUT")
        self.assertEqual(context["municipalities"], [])
        self.assertEqual(context["hydric_states"], {})


class HydricPressureRegionalSynthesisServiceTests(SimpleTestCase):
    def setUp(self):
        self.regional_service = HydricPressureRegionalService()
        self.synthesis_service = HydricPressureRegionalSynthesisService()

    def test_synthesizes_observed_distribution_without_new_hydric_state(self):
        municipal = [
            municipal_result(1, "DEFICIT_OBSERVED"),
            municipal_result(2, "DEFICIT_OBSERVED"),
            municipal_result(3, "EXCESS_OBSERVED"),
            municipal_result(4, "NO_DEFICIT_OBSERVED"),
        ]
        regional_context = self.regional_service.compose(municipal)

        synthesis = self.synthesis_service.synthesize(regional_context)

        self.assertEqual(synthesis["regional_status"], "VALID")
        self.assertEqual(
            synthesis["state_counts"],
            {
                "DEFICIT_OBSERVED": 2,
                "EXCESS_OBSERVED": 1,
                "NO_DEFICIT_OBSERVED": 1,
            },
        )
        self.assertEqual(
            synthesis["state_fractions"]["DEFICIT_OBSERVED"], 0.5
        )
        self.assertTrue(synthesis["state_heterogeneity"])
        self.assertEqual(
            synthesis["regional_interpretation"],
            "MUNICIPAL_STATE_DISTRIBUTION",
        )
        self.assertNotIn("regional_state", synthesis)
        self.assertNotIn("municipalities", synthesis)
        self.assertEqual(
            synthesis["source_regional_context"]["provenance"],
            regional_context["provenance"],
        )
        self.assertEqual(
            synthesis["source_regional_context"]["analysis_date"],
            date(2026, 9, 30),
        )
        self.assertEqual(synthesis["source_rule_id"], "HYDRIC_PRESSURE_001")
        self.assertEqual(
            [item["municipio_id"] for item in synthesis["participants"]],
            [1, 2, 3, 4],
        )
        self.assertEqual(
            synthesis["participants"][0]["source_rule_id"],
            "HYDRIC_PRESSURE_001",
        )
        self.assertEqual(
            synthesis["participants"][0]["provenance"],
            municipal[0]["provenance"],
        )

    def test_insufficient_collection_keeps_distribution_and_source_status(self):
        regional_context = self.regional_service.compose(
            [municipal_result(1), municipal_result(2), municipal_result(3)]
        )

        synthesis = self.synthesis_service.synthesize(regional_context)

        self.assertEqual(synthesis["regional_status"], "INSUFFICIENT_DATA")
        self.assertEqual(synthesis["valid_count"], 3)
        self.assertEqual(synthesis["state_counts"], {"NO_DEFICIT_OBSERVED": 3})
        self.assertNotIn("regional_state", synthesis)

    def test_rejects_noncanonical_or_duplicate_mp_01_6_collection(self):
        noncanonical = self.synthesis_service.synthesize(
            {"municipalities": [municipal_result(1)]}
        )
        self.assertEqual(
            noncanonical["regional_status"], "INVALID_SOURCE_CONTEXT"
        )

        canonical = self.regional_service.compose(
            [municipal_result(i) for i in range(1, 5)]
        )
        canonical["municipalities"].append(
            dict(canonical["municipalities"][0])
        )
        canonical["valid_count"] += 1
        duplicate = self.synthesis_service.synthesize(canonical)
        self.assertEqual(
            duplicate["regional_status"], "DUPLICATE_MUNICIPALITY"
        )
