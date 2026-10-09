"""
Testes unitários de MP-01.12 — Avaliação diagnóstica experimental de granizo.

Executar:
python manage.py test core.intelligence.test_hail_potential_experimental_evaluator
"""

from copy import deepcopy

from django.test import SimpleTestCase

from core.intelligence.hail_potential_experimental_evaluator import (
    CLASSIFICATION_STATUS,
    EXPERIMENTAL_STATUS,
    HailPotentialExperimentalEvaluator,
)
from core.intelligence.hail_potential_service import HailPotentialService


class HailPotentialExperimentalEvaluatorTests(SimpleTestCase):
    def setUp(self):
        self.evaluator = HailPotentialExperimentalEvaluator()
        self.canonical = {
            "assessment_status": "ASSESSED",
            "potential_level": None,
            "method_version": "MP-01.11.1",
            "source": "Open-Meteo Historical Forecast API",
            "model": "ecmwf_ifs025",
            "source_run": "run-2025-07-25",
            "valid_from": "2025-07-25T00:00:00Z",
            "valid_to": "2025-07-25T23:00:00Z",
            "required_variables": [
                "cape",
                "wind_speed_925hPa",
                "wind_direction_925hPa",
                "wind_speed_500hPa",
                "wind_direction_500hPa",
            ],
            "missing_variables": [],
            "drivers": [
                {
                    "variable": "cape",
                    "observed_value": 960.0,
                    "unit": "J/kg",
                    "role": "instability",
                    "rule_id": "HAIL_POTENTIAL_001",
                    "rule_version": "MP-01.11.1",
                },
                {
                    "variable": "shear_925_500",
                    "observed_value": 25.327,
                    "unit": "m/s",
                    "role": "vertical_wind_shear",
                    "rule_id": "HAIL_POTENTIAL_001",
                    "rule_version": "MP-01.11.1",
                },
                {
                    "variable": "cape_shear",
                    "observed_value": 24313.545,
                    "unit": "J/kg*m/s",
                    "role": "combined_environment",
                    "rule_id": "HAIL_POTENTIAL_001",
                    "rule_version": "MP-01.11.1",
                },
            ],
            "data_quality": {
                "required_variables_complete": True,
                "missing_variables": [],
                "complementary_variables": {
                    "wet_bulb_temperature_2m": True,
                    "temperature_850hPa": True,
                    "relative_humidity_850hPa": True,
                },
            },
            "derived": {
                "shear_925_500_ms": 25.327,
                "cape_shear": 24313.545,
            },
        }

    def assert_contract_rejected(self, source):
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["reason"], "CANONICAL_CONTRACT_INCONSISTENT")
        self.assertEqual(result["axes"], {})
        self.assertFalse(result["diagnostics_complete"])
        self.assertIsNone(result["potential_level"])

    def test_assessed_input_remains_experimental_and_unclassified(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertEqual(result["evaluation_status"], EXPERIMENTAL_STATUS)
        self.assertEqual(result["classification_status"], CLASSIFICATION_STATUS)
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["homologated"])

    def test_axes_are_separated(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertEqual(
            set(result["axes"]),
            {"instability", "organization_shear", "combined_cape_shear", "thermodynamics"},
        )
        self.assertEqual(result["axes"]["instability"]["evidence"]["value"], 960.0)
        self.assertEqual(result["axes"]["organization_shear"]["evidence"]["value"], 25.327)
        self.assertEqual(result["axes"]["combined_cape_shear"]["evidence"]["value"], 24313.545)

    def test_thermodynamic_values_are_not_invented(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertIsNone(result["axes"]["thermodynamics"]["values"])
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABILITY_ONLY")
        self.assertFalse(result["diagnostics_complete"])

    def test_availability_only_never_means_diagnostics_complete(self):
        source = deepcopy(self.canonical)
        source["data_quality"]["complementary_variables"] = {
            "wet_bulb_temperature_2m": False,
            "temperature_850hPa": False,
            "relative_humidity_850hPa": False,
        }
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABILITY_ONLY")
        self.assertFalse(result["diagnostics_complete"])

    def test_invalid_numeric_values_are_unavailable_not_contract_errors(self):
        source = deepcopy(self.canonical)
        source["drivers"][0]["observed_value"] = None
        source["derived"]["shear_925_500_ms"] = None
        source["derived"]["cape_shear"] = float("nan")
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["instability"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["organization_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "UNAVAILABLE")
        self.assertFalse(result["diagnostics_complete"])

    def test_inconsistent_assessed_contract_is_insufficient(self):
        source = deepcopy(self.canonical)
        source["missing_variables"] = ["cape"]
        source["data_quality"]["missing_variables"] = ["cape"]
        source["data_quality"]["required_variables_complete"] = False
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["reason"], "CANONICAL_CONTRACT_INCONSISTENT")
        self.assertEqual(result["insufficient_variables"], ["cape"])
        self.assertIsNone(result["potential_level"])

    def test_assessed_contract_without_data_quality_is_rejected(self):
        source = deepcopy(self.canonical)
        del source["data_quality"]
        self.assert_contract_rejected(source)

    def test_assessed_contract_with_non_dict_data_quality_is_rejected(self):
        source = deepcopy(self.canonical)
        source["data_quality"] = []
        self.assert_contract_rejected(source)

    def test_assessed_contract_requires_true_boolean_completeness(self):
        for value in (None, "true", 1, False):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["data_quality"]["required_variables_complete"] = value
                self.assert_contract_rejected(source)

    def test_assessed_contract_requires_both_missing_variable_lists(self):
        for location in ("source", "data_quality"):
            with self.subTest(location=location):
                source = deepcopy(self.canonical)
                if location == "source":
                    del source["missing_variables"]
                else:
                    del source["data_quality"]["missing_variables"]
                self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_malformed_missing_variable_lists(self):
        for value in ("cape", [None], [""], ["cape", 1]):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["missing_variables"] = value
                source["data_quality"]["missing_variables"] = value
                self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_non_list_drivers(self):
        for value in (None, {}, "drivers"):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["drivers"] = value
                self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_malformed_driver_entries(self):
        cases = (
            [None],
            [{"variable": "cape"}],
            [{"variable": "", "observed_value": 1, "unit": "J/kg", "role": "x",
              "rule_id": "r", "rule_version": "v"}],
            self.canonical["drivers"] + [deepcopy(self.canonical["drivers"][0])],
        )
        for drivers in cases:
            with self.subTest(drivers=drivers):
                source = deepcopy(self.canonical)
                source["drivers"] = drivers
                self.assert_contract_rejected(source)

    def test_assessed_contract_requires_all_canonical_driver_variables(self):
        source = deepcopy(self.canonical)
        source["drivers"] = [source["drivers"][0]]
        self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_invalid_derived_structure(self):
        for value in (None, [], "derived"):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["derived"] = value
                self.assert_contract_rejected(source)

    def test_assessed_contract_requires_derived_keys(self):
        for key in ("shear_925_500_ms", "cape_shear"):
            with self.subTest(key=key):
                source = deepcopy(self.canonical)
                del source["derived"][key]
                self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_invalid_complementary_structure(self):
        for value in (None, [], "variables"):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["data_quality"]["complementary_variables"] = value
                self.assert_contract_rejected(source)

    def test_assessed_contract_requires_exact_complementary_boolean_map(self):
        cases = (
            {},
            {"wet_bulb_temperature_2m": True},
            {
                "wet_bulb_temperature_2m": True,
                "temperature_850hPa": True,
                "relative_humidity_850hPa": "true",
            },
            {
                "wet_bulb_temperature_2m": True,
                "temperature_850hPa": True,
                "relative_humidity_850hPa": True,
                "unexpected": False,
            },
        )
        for value in cases:
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["data_quality"]["complementary_variables"] = value
                self.assert_contract_rejected(source)

    def test_string_missing_variables_are_not_split_into_characters(self):
        source = deepcopy(self.canonical)
        source["assessment_status"] = "INSUFFICIENT_DATA"
        source["missing_variables"] = "cape"
        source["data_quality"]["missing_variables"] = ["cape"]
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["insufficient_variables"], ["cape"])

    def test_cape_shear_is_not_probability_or_standalone_classification(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertIn("combined_cape_shear", result["axes"])
        self.assertIsNone(result["potential_level"])
        self.assertIn("SEM_PROBABILIDADE_SCORE_ALERTA_OU_DANO", result["limitations"])

    def test_provenance_and_method_version_are_preserved(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertEqual(result["provenance"]["source"], self.canonical["source"])
        self.assertEqual(result["provenance"]["model"], self.canonical["model"])
        self.assertEqual(result["provenance"]["input_method_version"], self.canonical["method_version"])

    def test_input_is_not_mutated(self):
        original = deepcopy(self.canonical)
        self.evaluator.evaluate(self.canonical)
        self.assertEqual(self.canonical, original)

    def test_insufficient_input_does_not_become_zero_or_classification(self):
        source = deepcopy(self.canonical)
        source["assessment_status"] = "INSUFFICIENT_DATA"
        source["missing_variables"] = ["cape"]
        source["derived"] = {}
        source["drivers"] = []
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["potential_level"])
        self.assertEqual(result["insufficient_variables"], ["cape"])

    def test_invalid_input_is_handled_as_insufficient(self):
        result = self.evaluator.evaluate(None)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["diagnostics_complete"])

    def test_actual_mp011_service_contract_is_accepted(self):
        context = {
            "series": {
                "cape": 960.0,
                "wind_speed_925hPa": 10.0,
                "wind_direction_925hPa": 180.0,
                "wind_speed_500hPa": 30.0,
                "wind_direction_500hPa": 270.0,
                "wet_bulb_temperature_2m": 15.0,
                "temperature_850hPa": 8.0,
                "relative_humidity_850hPa": 75.0,
            },
            "provenance": {
                "source": "test-source",
                "model": "ecmwf_ifs025",
                "source_run": "test-run",
            },
            "valid_from": "2026-10-09T00:00:00Z",
            "valid_to": "2026-10-09T23:00:00Z",
        }
        canonical = HailPotentialService().evaluate(context).as_dict()
        result = self.evaluator.evaluate(canonical)
        self.assertEqual(canonical["assessment_status"], "ASSESSED")
        self.assertEqual(result["evaluation_status"], EXPERIMENTAL_STATUS)
        self.assertIsNone(result["potential_level"])
        self.assertEqual(result["provenance"]["source"], "test-source")
        self.assertFalse(result["diagnostics_complete"])
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABILITY_ONLY")
