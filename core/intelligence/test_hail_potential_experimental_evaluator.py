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
            "method_version": "MP-01.11.2",
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
                    "rule_version": "MP-01.11.2",
                },
                {
                    "variable": "shear_925_500",
                    "observed_value": 25.326609464494872,
                    "unit": "m/s",
                    "role": "vertical_wind_shear",
                    "rule_id": "HAIL_POTENTIAL_001",
                    "rule_version": "MP-01.11.2",
                },
                {
                    "variable": "cape_shear",
                    "observed_value": 24313.545085915077,
                    "unit": "J/kg*m/s",
                    "role": "combined_environment",
                    "rule_id": "HAIL_POTENTIAL_001",
                    "rule_version": "MP-01.11.2",
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
                "shear_925_500_ms": 25.326609464494872,
                "cape_shear": 24313.545085915077,
            },
            "complementary_values": {
                "wet_bulb_temperature_2m": 15.0,
                "temperature_850hPa": 8.0,
                "relative_humidity_850hPa": 75.0,
            },
        }

    def assert_contract_rejected(self, source, expected_reason="CANONICAL_CONTRACT_INCONSISTENT"):
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["reason"], expected_reason)
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
        self.assertEqual(
            result["axes"]["organization_shear"]["evidence"]["value"],
            25.326609464494872,
        )
        self.assertEqual(
            result["axes"]["combined_cape_shear"]["evidence"]["value"],
            24313.545085915077,
        )

    def test_thermodynamic_values_are_not_invented(self):
        result = self.evaluator.evaluate(self.canonical)
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABLE")
        thermo = result["axes"]["thermodynamics"]["values"]
        self.assertEqual(thermo["wet_bulb_temperature_2m"], {"value": 15.0, "unit": "°C"})
        self.assertEqual(thermo["temperature_850hPa"], {"value": 8.0, "unit": "°C"})
        self.assertEqual(thermo["relative_humidity_850hPa"], {"value": 75.0, "unit": "%"})
        self.assertEqual(result["axes"]["thermodynamics"]["values"]["wet_bulb_temperature_2m"]["value"], 15.0)
        self.assertEqual(result["axes"]["thermodynamics"]["values"]["temperature_850hPa"]["unit"], "°C")
        self.assertTrue(result["diagnostics_complete"])

    def test_missing_thermodynamic_values_remain_unavailable(self):
        source = deepcopy(self.canonical)
        source["data_quality"]["complementary_variables"] = {
            "wet_bulb_temperature_2m": False,
            "temperature_850hPa": False,
            "relative_humidity_850hPa": False,
        }
        source["complementary_values"] = {
            "wet_bulb_temperature_2m": None,
            "temperature_850hPa": None,
            "relative_humidity_850hPa": None,
        }
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["thermodynamics"]["values"], {})
        self.assertFalse(result["diagnostics_complete"])

    def test_invalid_numeric_values_are_unavailable_not_contract_errors(self):
        source = deepcopy(self.canonical)
        source["drivers"][0]["observed_value"] = None
        source["drivers"][1]["observed_value"] = None
        source["drivers"][2]["observed_value"] = None
        source["derived"]["shear_925_500_ms"] = None
        source["derived"]["cape_shear"] = float("nan")
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["instability"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["organization_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(
            result["insufficient_variables"],
            ["cape", "shear_925_500", "cape_shear"],
        )
        self.assertFalse(result["diagnostics_complete"])

    def test_driver_derived_mismatch_is_rejected_without_axes(self):
        for driver_name, derived_name in (
            ("shear_925_500", "shear_925_500_ms"),
            ("cape_shear", "cape_shear"),
        ):
            with self.subTest(driver=driver_name):
                source = deepcopy(self.canonical)
                driver = next(
                    item for item in source["drivers"]
                    if item["variable"] == driver_name
                )
                driver["observed_value"] += 10
                result = self.evaluator.evaluate(source)
                self.assertEqual(result["reason"], "CANONICAL_DRIVER_DERIVED_MISMATCH")
                self.assertEqual(result["axes"], {})
                self.assertIsNone(result["potential_level"])

    def test_cape_shear_product_mismatch_is_rejected(self):
        source = deepcopy(self.canonical)
        source["derived"]["cape_shear"] += 10
        source["drivers"][2]["observed_value"] += 10
        result = self.evaluator.evaluate(source)
        self.assertEqual(
            result["reason"], "CANONICAL_CAPE_SHEAR_PRODUCT_MISMATCH"
        )
        self.assertEqual(result["axes"], {})
        self.assertIsNone(result["potential_level"])

    def test_missing_numeric_evidence_remains_unavailable_and_is_not_mutated(self):
        source = deepcopy(self.canonical)
        source["drivers"][0]["observed_value"] = None
        source["drivers"][2]["observed_value"] = None
        source["derived"]["cape_shear"] = None
        before = deepcopy(source)
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["instability"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(source, before)

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
        self.assertTrue(result["diagnostics_complete"])
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABLE")
        drivers = {item["variable"]: item for item in canonical["drivers"]}
        self.assertEqual(
            drivers["shear_925_500"]["observed_value"],
            canonical["derived"]["shear_925_500_ms"],
        )
        self.assertEqual(
            drivers["cape_shear"]["observed_value"],
            canonical["derived"]["cape_shear"],
        )
        self.assertEqual(
            canonical["derived"]["cape_shear"],
            drivers["cape"]["observed_value"]
            * drivers["shear_925_500"]["observed_value"],
        )


    def test_driver_metadata_must_be_nonempty_strings(self):
        for field in ("unit", "role", "rule_id", "rule_version"):
            for invalid in ("", "   ", None, 1, [], {}):
                with self.subTest(field=field, invalid=invalid):
                    source = deepcopy(self.canonical)
                    source["drivers"][0][field] = invalid
                    self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_unexpected_driver(self):
        source = deepcopy(self.canonical)
        source["drivers"].append({
            "variable": "unexpected_driver",
            "observed_value": 1.0,
            "unit": "unit",
            "role": "unexpected",
            "rule_id": "TEST",
            "rule_version": "1",
        })
        self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_unexpected_derived_field(self):
        source = deepcopy(self.canonical)
        source["derived"]["unexpected_value"] = 123.0
        self.assert_contract_rejected(source)

    def test_assessed_contract_rejects_incorrect_required_variables(self):
        source = deepcopy(self.canonical)
        source["required_variables"] = ["cape"]
        self.assert_contract_rejected(source)

    def test_boolean_values_are_not_numeric_meteorological_evidence(self):
        source = deepcopy(self.canonical)
        source["drivers"][0]["observed_value"] = True
        source["drivers"][1]["observed_value"] = True
        source["drivers"][2]["observed_value"] = False

        result = self.evaluator.evaluate(source)

        self.assertEqual(result["axes"]["instability"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["organization_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "UNAVAILABLE")
        self.assertFalse(result["diagnostics_complete"])

    def test_mp012_rejects_noncanonical_units_and_roles(self):
        expected = {
            "cape": ("J/kg", "instability"),
            "shear_925_500": ("m/s", "vertical_wind_shear"),
            "cape_shear": ("J/kg*m/s", "combined_environment"),
        }

        for variable, (unit, role) in expected.items():
            for field, invalid in (
                ("unit", "UNIDADE_INCORRETA"),
                ("role", "PAPEL_INCORRETO"),
            ):
                with self.subTest(variable=variable, field=field):
                    source = deepcopy(self.canonical)
                    driver = next(
                        item for item in source["drivers"]
                        if item["variable"] == variable
                    )
                    driver[field] = invalid
                    self.assert_contract_rejected(source)

    def test_mp012_rejects_shear_driver_derived_divergence(self):
        source = deepcopy(self.canonical)
        source["drivers"][1]["observed_value"] = 24.0
        self.assert_contract_rejected(
            source,
            expected_reason="CANONICAL_DRIVER_DERIVED_MISMATCH",
        )

    def test_mp012_rejects_cape_shear_driver_derived_divergence(self):
        source = deepcopy(self.canonical)
        source["derived"]["cape_shear"] = 25000.0
        self.assert_contract_rejected(
            source,
            expected_reason="CANONICAL_DRIVER_DERIVED_MISMATCH",
        )

    def test_mp012_rejects_inconsistent_cape_shear_product(self):
        source = deepcopy(self.canonical)

        # Driver e campo derivado concordam entre si, mas divergem
        # do produto CAPE x cisalhamento além da tolerância.
        for driver in source["drivers"]:
            if driver["variable"] == "cape_shear":
                driver["observed_value"] = 25000.0

        source["derived"]["cape_shear"] = 25000.0
        self.assert_contract_rejected(
            source,
            expected_reason="CANONICAL_CAPE_SHEAR_PRODUCT_MISMATCH",
        )

    def test_mp012_accepts_full_precision_fixture(self):
        # O fixture espelha os floats completos produzidos pelo serviço.
        result = self.evaluator.evaluate(deepcopy(self.canonical))
        self.assertEqual(result["evaluation_status"], EXPERIMENTAL_STATUS)
        self.assertEqual(result["classification_status"], CLASSIFICATION_STATUS)
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["homologated"])

    def test_mp012_invalid_numeric_evidence_remains_unavailable(self):
        source = deepcopy(self.canonical)
        source["drivers"][0]["observed_value"] = float("nan")

        result = self.evaluator.evaluate(source)

        self.assertEqual(result["evaluation_status"], EXPERIMENTAL_STATUS)
        self.assertEqual(
            result["axes"]["instability"]["status"],
            "UNAVAILABLE",
        )
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["homologated"])

    def test_r1_rejects_boolean_numeric_strings_and_invalid_domains(self):
        cases = (
            ("cape", True),
            ("cape", "960.0"),
            ("cape", -1.0),
            ("shear_925_500", -0.1),
            ("cape_shear", True),
            ("cape_shear", "24313.5"),
            ("cape_shear", float("inf")),
        )
        for variable, value in cases:
            with self.subTest(variable=variable, value=value):
                source = deepcopy(self.canonical)
                driver = next(d for d in source["drivers"] if d["variable"] == variable)
                driver["observed_value"] = value
                result = self.evaluator.evaluate(source)
                self.assertNotIn("reason", result)
                axis = {
                    "cape": "instability",
                    "shear_925_500": "organization_shear",
                    "cape_shear": "combined_cape_shear",
                }[variable]
                self.assertEqual(result["axes"][axis]["status"], "UNAVAILABLE")
                self.assertIn(variable, result["insufficient_variables"])

    def test_axis_uses_canonical_driver_when_derived_value_is_invalid(self):
        source = deepcopy(self.canonical)
        source["derived"]["shear_925_500_ms"] = -1.0
        source["derived"]["cape_shear"] = "not-a-number"
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["organization_shear"]["status"], "AVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "AVAILABLE")
        self.assertNotIn("shear_925_500", result["insufficient_variables"])
        self.assertNotIn("cape_shear", result["insufficient_variables"])

    def test_product_check_uses_driver_shear_and_each_valid_product_representation(self):
        source = deepcopy(self.canonical)
        source["drivers"][1]["observed_value"] = -1.0
        result = self.evaluator.evaluate(source)
        self.assertEqual(result["axes"]["organization_shear"]["status"], "UNAVAILABLE")
        self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "AVAILABLE")

        for location in ("driver", "derived"):
            with self.subTest(location=location):
                source = deepcopy(self.canonical)
                if location == "driver":
                    next(d for d in source["drivers"] if d["variable"] == "cape_shear")["observed_value"] = -1.0
                    source["derived"]["cape_shear"] = -1.0
                else:
                    source["derived"]["cape_shear"] = -1.0
                    next(d for d in source["drivers"] if d["variable"] == "cape_shear")["observed_value"] = -1.0
                result = self.evaluator.evaluate(source)
                self.assertEqual(result["reason"], "CANONICAL_CAPE_SHEAR_PRODUCT_MISMATCH")
                self.assertEqual(result["axes"], {})

    def test_zero_product_is_valid_and_not_reported_missing(self):
        for variable in ("cape", "shear_925_500"):
            with self.subTest(variable=variable):
                source = deepcopy(self.canonical)
                next(d for d in source["drivers"] if d["variable"] == variable)["observed_value"] = 0.0
                next(d for d in source["drivers"] if d["variable"] == "cape_shear")["observed_value"] = 0.0
                source["derived"]["cape_shear"] = 0.0
                if variable == "shear_925_500":
                    source["derived"]["shear_925_500_ms"] = 0.0
                result = self.evaluator.evaluate(source)
                self.assertNotIn(variable, result["insufficient_variables"])
                self.assertEqual(result["axes"]["combined_cape_shear"]["status"], "AVAILABLE")

    def test_declared_complementary_value_must_be_effectively_valid(self):
        for invalid in (None, True, "8.0", float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                source = deepcopy(self.canonical)
                source["complementary_values"]["temperature_850hPa"] = invalid
                result = self.evaluator.evaluate(source)
                self.assertEqual(result["axes"]["thermodynamics"]["status"], "PARTIAL")
                self.assertIn("temperature_850hPa", result["insufficient_variables"])
                self.assertFalse(result["diagnostics_complete"])

    def test_thermodynamics_is_partial_for_one_or_two_valid_complementaries(self):
        for valid_count in (1, 2):
            with self.subTest(valid_count=valid_count):
                source = deepcopy(self.canonical)
                names = (
                    "wet_bulb_temperature_2m",
                    "temperature_850hPa",
                    "relative_humidity_850hPa",
                )
                for name in names[valid_count:]:
                    source["complementary_values"][name] = None
                    source["data_quality"]["complementary_variables"][name] = False
                result = self.evaluator.evaluate(source)
                self.assertEqual(result["axes"]["thermodynamics"]["status"], "PARTIAL")
                self.assertEqual(result["insufficient_variables"], list(names[valid_count:]))
                self.assertFalse(result["diagnostics_complete"])

    def test_relative_humidity_domain_is_inclusive_and_enforced(self):
        for value, expected in ((0.0, "AVAILABLE"), (100.0, "AVAILABLE"), (-0.1, "PARTIAL"), (100.1, "PARTIAL")):
            with self.subTest(value=value):
                source = deepcopy(self.canonical)
                source["complementary_values"]["relative_humidity_850hPa"] = value
                result = self.evaluator.evaluate(source)
                self.assertEqual(result["axes"]["thermodynamics"]["status"], expected)
                self.assertEqual("relative_humidity_850hPa" in result["insufficient_variables"], expected == "PARTIAL")
