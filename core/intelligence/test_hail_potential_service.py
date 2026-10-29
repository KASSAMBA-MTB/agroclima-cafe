"""
Testes do MP-01.11 — HailPotentialService.

Testa somente o contrato implementado.
Não testa threshold porque threshold ainda não é parte do contrato.
"""

from django.test import SimpleTestCase

from core.intelligence.hail_potential_contract import (
    ASSESSMENT_ASSESSED,
    ASSESSMENT_INSUFFICIENT,
)
from core.intelligence.hail_potential_service import HailPotentialService
from core.intelligence.hail_potential_experimental_evaluator import (
    HailPotentialExperimentalEvaluator,
)


class HailPotentialServiceTests(SimpleTestCase):

    def setUp(self):
        self.service = HailPotentialService()

    def context(self):
        return {
            "source": "historical_forecast",
            "model": "ecmwf_ifs025",
            "source_run": "2025-07-25",
            "valid_from": "2025-07-25T00:00",
            "valid_to": "2025-07-25T23:00",
            "series": {
                "cape": 960.0,
                "wet_bulb_temperature_2m": 17.2,
                "temperature_850hPa": 14.7,
                "relative_humidity_850hPa": 77.0,
                "wind_speed_925hPa": 3.44,
                "wind_direction_925hPa": 13.0,
                "wind_speed_500hPa": 24.33,
                "wind_direction_500hPa": 270.0,
            },
        }

    def test_assessed_when_required_variables_are_present(self):
        result = self.service.evaluate(self.context())

        self.assertEqual(result.assessment_status, ASSESSMENT_ASSESSED)
        self.assertIsNone(result.potential_level)
        self.assertEqual(result.missing_variables, ())
        self.assertEqual(result.complementary_values["temperature_850hPa"], 14.7)
        self.assertEqual(result.complementary_values["relative_humidity_850hPa"], 77.0)

    def test_service_contract_flows_through_experimental_evaluator(self):
        canonical = self.service.evaluate(self.context()).as_dict()

        result = HailPotentialExperimentalEvaluator().evaluate(canonical)

        self.assertEqual(canonical["assessment_status"], ASSESSMENT_ASSESSED)
        cape_driver = next(
            driver for driver in canonical["drivers"]
            if driver["variable"] == "cape"
        )
        self.assertEqual(cape_driver["observed_value"], self.context()["series"]["cape"])
        self.assertEqual(
            result["classification_status"],
            "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS",
        )
        self.assertTrue(result["diagnostics_complete"])
        self.assertIsNone(result["potential_level"])

    def test_incomplete_service_contract_flows_as_insufficient(self):
        context = self.context()
        del context["series"]["wind_speed_500hPa"]
        canonical = self.service.evaluate(context).as_dict()

        result = HailPotentialExperimentalEvaluator().evaluate(canonical)

        self.assertEqual(canonical["assessment_status"], ASSESSMENT_INSUFFICIENT)
        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertIn("wind_speed_500hPa", result["insufficient_variables"])
        self.assertEqual(
            set(result["axes"]),
            {
                "instability",
                "organization_shear",
                "combined_cape_shear",
                "thermodynamics",
            },
        )
        self.assertEqual(result["axes"]["thermodynamics"]["status"], "AVAILABLE")
        self.assertFalse(result["diagnostics_complete"])
        self.assertIsNone(result["potential_level"])

    def test_calculates_925_500_shear(self):
        result = self.service.evaluate(self.context())

        shear = result.derived["shear_925_500_ms"]

        self.assertGreater(shear, 0)
        self.assertAlmostEqual(shear, 25.326609464494872, places=10)

    def test_calculates_cape_shear(self):
        result = self.service.evaluate(self.context())

        self.assertAlmostEqual(
            result.derived["cape_shear"],
            960.0 * result.derived["shear_925_500_ms"],
            places=6,
        )

    def test_missing_required_variable_returns_insufficient_data(self):
        context = self.context()
        del context["series"]["wind_speed_500hPa"]

        result = self.service.evaluate(context)

        self.assertEqual(
            result.assessment_status,
            ASSESSMENT_INSUFFICIENT,
        )
        self.assertIsNone(result.potential_level)
        self.assertIn("wind_speed_500hPa", result.missing_variables)
        self.assertEqual(result.derived, {})

    def test_missing_never_becomes_zero(self):
        context = self.context()
        context["series"]["cape"] = None

        result = self.service.evaluate(context)

        self.assertEqual(
            result.assessment_status,
            ASSESSMENT_INSUFFICIENT,
        )
        self.assertIsNone(result.derived.get("cape_shear"))

    def test_provenance_is_preserved(self):
        result = self.service.evaluate(self.context())

        self.assertEqual(result.source, "historical_forecast")
        self.assertEqual(result.model, "ecmwf_ifs025")
        self.assertEqual(result.source_run, "2025-07-25")

    def test_drivers_contain_cape_shear_and_combined_environment(self):
        result = self.service.evaluate(self.context())

        variables = [driver["variable"] for driver in result.drivers]

        self.assertIn("cape", variables)
        self.assertIn("shear_925_500", variables)
        self.assertIn("cape_shear", variables)

    def test_contract_serializes(self):
        result = self.service.evaluate(self.context())
        payload = result.as_dict()

        self.assertEqual(payload["assessment_status"], "ASSESSED")
        self.assertIn("data_quality", payload)
        self.assertIn("derived", payload)
        self.assertEqual(payload["complementary_values"]["wet_bulb_temperature_2m"], 17.2)

    def test_missing_complementary_value_stays_none_and_is_not_zero(self):
        context = self.context()
        context["series"]["temperature_850hPa"] = None

        payload = self.service.evaluate(context).as_dict()

        self.assertEqual(payload["assessment_status"], "ASSESSED")
        self.assertIsNone(payload["complementary_values"]["temperature_850hPa"])
        self.assertFalse(payload["data_quality"]["complementary_variables"]["temperature_850hPa"])

    def test_directional_wind_uses_meteorological_vector_conversion(self):
        context = self.context()
        context["series"]["wind_speed_925hPa"] = 0.0
        context["series"]["wind_direction_925hPa"] = 0.0
        context["series"]["wind_speed_500hPa"] = 10.0
        context["series"]["wind_direction_500hPa"] = 0.0

        result = self.service.evaluate(context)

        self.assertAlmostEqual(
            result.derived["shear_925_500_ms"],
            10.0,
            places=6,
        )
    def test_boolean_required_variable_returns_insufficient_data(self):
        context = self.context()
        context["series"]["cape"] = True

        result = self.service.evaluate(context)

        self.assertEqual(
            result.assessment_status,
            ASSESSMENT_INSUFFICIENT,
        )
        self.assertIn("cape", result.missing_variables)
        self.assertEqual(result.derived, {})

    def test_boolean_complementary_value_is_preserved_as_missing(self):
        context = self.context()
        context["series"]["temperature_850hPa"] = True

        payload = self.service.evaluate(context).as_dict()

        self.assertEqual(payload["assessment_status"], "ASSESSED")
        self.assertIsNone(
            payload["complementary_values"]["temperature_850hPa"]
        )
        self.assertFalse(
            payload["data_quality"]["complementary_variables"][
                "temperature_850hPa"
            ]
        )

    def test_rejects_required_values_outside_established_domains(self):
        invalid_cases = (
            ("cape", -0.1),
            ("wind_speed_925hPa", -0.1),
            ("wind_speed_500hPa", -0.1),
            ("wind_direction_925hPa", -0.1),
            ("wind_direction_500hPa", 360.1),
            ("cape", True),
            ("cape", float("nan")),
            ("cape", float("inf")),
        )
        for variable, value in invalid_cases:
            with self.subTest(variable=variable, value=value):
                context = self.context()
                context["series"][variable] = value
                result = self.service.evaluate(context).as_dict()
                self.assertEqual(result["assessment_status"], ASSESSMENT_INSUFFICIENT)
                self.assertIsNone(result["potential_level"])
                self.assertIn(variable, result["missing_variables"])
                self.assertIn(variable, result["data_quality"]["invalid_variables"])
                self.assertEqual(result["derived"], {})

    def test_direction_360_is_valid_and_equivalent_to_zero(self):
        zero_context = self.context()
        zero_context["series"].update({
            "wind_speed_925hPa": 0,
            "wind_direction_925hPa": 0,
            "wind_speed_500hPa": 10,
            "wind_direction_500hPa": 0,
        })
        wrap_context = self.context()
        wrap_context["series"].update({
            "wind_speed_925hPa": 0,
            "wind_direction_925hPa": 360,
            "wind_speed_500hPa": 10,
            "wind_direction_500hPa": 360,
        })
        zero_result = self.service.evaluate(zero_context)
        wrap_result = self.service.evaluate(wrap_context)
        self.assertEqual(zero_result.assessment_status, ASSESSMENT_ASSESSED)
        self.assertEqual(wrap_result.assessment_status, ASSESSMENT_ASSESSED)
        self.assertAlmostEqual(
            wrap_result.derived["shear_925_500_ms"],
            zero_result.derived["shear_925_500_ms"],
            places=12,
        )

    def test_invalid_relative_humidity_is_unavailable_not_zero(self):
        context = self.context()
        context["series"]["relative_humidity_850hPa"] = 100.1
        result = self.service.evaluate(context).as_dict()
        self.assertEqual(result["assessment_status"], ASSESSMENT_ASSESSED)
        self.assertIsNone(result["complementary_values"]["relative_humidity_850hPa"])
        self.assertIn(
            "relative_humidity_850hPa",
            result["data_quality"]["invalid_complementary_variables"],
        )
