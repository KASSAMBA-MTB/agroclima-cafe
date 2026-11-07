from unittest import TestCase

from core.intelligence.hail_project_context_contract import (
    HailProjectContextContract,
)


class HailProjectContextContractSanitizationTests(TestCase):
    @staticmethod
    def as_context(hail):
        return HailProjectContextContract.from_municipal_result(
            hail=hail,
            municipio_id=17,
            municipio_nome="Município de teste",
        ).as_dict()

    def test_main_potential_level_is_always_none(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "potential_level": "HIGH",
        })

        self.assertIsNone(context["potential_level"])
        self.assertEqual(context["classification_status"], "NOT_CLASSIFIED")

    def test_municipal_result_potential_level_is_sanitized(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "potential_level": "HIGH",
            "classification_status": "HIGH",
        })

        self.assertIsNone(context["municipal_result"]["potential_level"])
        self.assertEqual(
            context["municipal_result"]["classification_status"],
            "NOT_CLASSIFIED",
        )

    def test_experimental_potential_is_sanitized_without_losing_diagnostics(self):
        experimental = {
            "potential_level": "HIGH",
            "classification_status": "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
            "operational": True,
            "homologated": True,
            "diagnostics_complete": True,
            "axes": {"instability": {"value": 1200.0}},
            "provenance": {"source_run": "run-exp-1"},
            "data_quality": {"complete": True},
        }
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "experimental_evaluation": experimental,
        })
        sanitized = context["municipal_result"]["experimental_evaluation"]

        self.assertIsNone(sanitized["potential_level"])
        self.assertEqual(
            sanitized["classification_status"],
            "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
        )
        self.assertFalse(sanitized["operational"])
        self.assertFalse(sanitized["homologated"])
        self.assertTrue(sanitized["diagnostics_complete"])
        self.assertEqual(sanitized["axes"], {"instability": {"value": 1200.0}})
        self.assertEqual(sanitized["provenance"], {"source_run": "run-exp-1"})
        self.assertEqual(sanitized["data_quality"], {"complete": True})
        self.assertEqual(experimental["potential_level"], "HIGH")

    def test_nested_canonical_payload_classification_is_sanitized(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "municipal_result": {
                "potential_level": "HIGH",
                "classification_status": "HIGH",
                "is_factual_event": True,
                "drivers": [{"variable": "cape", "observed_value": 900.0}],
            },
        })
        nested = context["municipal_result"]["municipal_result"]

        self.assertIsNone(nested["potential_level"])
        self.assertEqual(nested["classification_status"], "NOT_CLASSIFIED")
        self.assertFalse(nested["is_factual_event"])
        self.assertEqual(
            nested["drivers"],
            [{"variable": "cape", "observed_value": 900.0}],
        )

    def test_conflicting_experimental_classification_status_is_not_exposed(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "experimental_evaluation": {
                "assessment_status": "ASSESSED",
                "classification_status": "HIGH",
                "potential_level": "HIGH",
            },
        })
        experimental = context["municipal_result"]["experimental_evaluation"]

        self.assertEqual(
            experimental["classification_status"],
            "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
        )
        self.assertIsNone(experimental["potential_level"])

    def test_conflicting_factual_flags_never_cross_the_contract(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "is_factual_event": True,
            "experimental_evaluation": {"is_factual_event": True},
            "municipal_result": {"is_factual_event": True},
        })

        self.assertFalse(context["is_factual_event"])
        self.assertFalse(context["municipal_result"]["is_factual_event"])
        self.assertFalse(
            context["municipal_result"]["experimental_evaluation"][
                "is_factual_event"
            ]
        )
        self.assertFalse(
            context["municipal_result"]["municipal_result"][
                "is_factual_event"
            ]
        )

    def test_meteorology_provenance_versions_and_quality_are_preserved(self):
        hail = {
            "assessment_status": "ASSESSED",
            "potential_level": "HIGH",
            "method_version": "MP-01.11.2",
            "canonical_method_version": "MP-01.11.2-canonical",
            "experimental_diagnostic_version": "MP-01.12.3",
            "rule_implementation_version": "1.0",
            "source": "open-meteo-forecast-api",
            "model": "ecmwf_ifs025",
            "source_run": "run-123",
            "valid_from": "2026-10-15T12:00",
            "valid_to": "2026-10-15T15:00",
            "data_quality": {"required_variables_complete": True},
            "derived": {"shear_925_500_ms": 13.25, "cape_shear": 26500.0},
            "experimental_evaluation": {
                "potential_level": "HIGH",
                "axes": {"organization_shear": {"value": 13.25}},
            },
        }

        context = self.as_context(hail)

        self.assertEqual(context["derived"], hail["derived"])
        self.assertEqual(context["data_quality"], hail["data_quality"])
        self.assertEqual(context["source"], hail["source"])
        self.assertEqual(context["model"], hail["model"])
        self.assertEqual(context["source_run"], hail["source_run"])
        self.assertEqual(context["valid_from"], hail["valid_from"])
        self.assertEqual(context["valid_to"], hail["valid_to"])
        self.assertEqual(context["method_version"], hail["method_version"])
        self.assertEqual(
            context["canonical_method_version"],
            hail["canonical_method_version"],
        )
        self.assertEqual(
            context["experimental_diagnostic_version"],
            hail["experimental_diagnostic_version"],
        )
        self.assertEqual(
            context["rule_implementation_version"],
            hail["rule_implementation_version"],
        )
        self.assertEqual(
            context["municipal_result"]["experimental_evaluation"]["axes"],
            hail["experimental_evaluation"]["axes"],
        )

    def test_package_c1_projects_municipal_experimental_potential_contract(self):
        context = self.as_context({
            "assessment_status": "ASSESSED",
            "method_version": "MP-01.11.2",
            "experimental_evaluation": {
                "evaluation_status": "EXPERIMENTAL_NOT_HOMOLOGATED",
                "experimental_diagnostic_version": "MP-01.12.3",
                "axes": {
                    "instability": {
                        "status": "AVAILABLE",
                        "evidence": {"value": 900.0, "unit": "J/kg"},
                    },
                    "organization_shear": {
                        "status": "AVAILABLE",
                        "evidence": {"value": 12.0, "unit": "m/s"},
                    },
                    "thermodynamics": {"status": "UNAVAILABLE"},
                },
            },
        })
        municipal = context["municipal_result"]

        self.assertIsNone(municipal["potential_level"])
        self.assertEqual(
            municipal["classification_status"],
            "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
        )
        self.assertEqual(municipal["rule_version"], "MP-01.12.3")
        self.assertEqual(
            municipal["rule_applied"],
            "HAIL_POTENTIAL_EXPERIMENTAL_EVALUATOR",
        )
        self.assertEqual(
            municipal["determining_indicators"],
            ["instability", "organization_shear"],
        )
        self.assertIsNone(municipal["threshold_set_version"])
        self.assertEqual(municipal["threshold_set_status"], "NOT_CONFIGURED")
        self.assertIsNone(municipal["validation_reference"])
        self.assertFalse(municipal["operational"])
        self.assertFalse(municipal["is_factual_event"])
        self.assertTrue(municipal["limitations"])

    def test_missing_experimental_evaluation_is_not_invented(self):
        context = self.as_context({
            "assessment_status": "INSUFFICIENT_DATA",
            "potential_level": "HIGH",
            "missing_variables": ["cape"],
        })

        self.assertNotIn(
            "experimental_evaluation",
            context["municipal_result"],
        )
        self.assertIsNone(context["potential_level"])
        self.assertFalse(context["is_factual_event"])
