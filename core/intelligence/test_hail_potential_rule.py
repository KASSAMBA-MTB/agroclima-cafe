"""
Testes da HailPotentialRule — MP-01.11

Valida exclusivamente a integração BaseRule -> Service -> RuleEngine
sem alterar a classificação meteorológica ainda não homologada.
"""

from datetime import datetime
import unittest

from core.intelligence.rules.hail_potential_rule import HailPotentialRule


class HailPotentialRuleTests(unittest.TestCase):

    def setUp(self):
        self.rule = HailPotentialRule()

        self.context = {
            "municipio_id": 1,
            "municipio_nome": "Andradas",
            "source": "historical_forecast_api",
            "model": "ecmwf_ifs025",
            "source_run": "2025-07-25T00:00:00",
            "valid_from": datetime(2025, 7, 25, 15, 0),
            "valid_to": datetime(2025, 7, 25, 15, 0),
            "cape": 960.0,
            "wet_bulb_temperature_2m": 17.2,
            "temperature_850hPa": 14.7,
            "relative_humidity_850hPa": 77.0,
            "wind_speed_925hPa": 3.44,
            "wind_direction_925hPa": 13.0,
            "wind_speed_500hPa": 24.33,
            "wind_direction_500hPa": 270.0,
        }

    def test_rule_inherits_base_rule(self):
        from core.intelligence.base_rule import BaseRule
        self.assertIsInstance(self.rule, BaseRule)

    def test_rule_identity(self):
        result = self.rule.evaluate(self.context)

        self.assertEqual(result["id"], "HAIL_POTENTIAL_001")
        self.assertEqual(result["rule_id"], "HAIL_POTENTIAL_001")
        self.assertEqual(result["rule_version"], "1.0")
        self.assertEqual(result["channel"], "context")

    def test_preserves_assessed_status(self):
        result = self.rule.evaluate(self.context)

        self.assertEqual(result["assessment_status"], "ASSESSED")

    def test_preserves_shear_and_cape_shear(self):
        result = self.rule.evaluate(self.context)

        self.assertIn("shear_925_500_ms", result["derived"])
        self.assertIn("cape_shear", result["derived"])
        self.assertAlmostEqual(
            result["derived"]["shear_925_500_ms"],
            25.327,
            places=2,
        )

    def test_does_not_invent_potential_level(self):
        result = self.rule.evaluate(self.context)

        self.assertIsNone(result["potential_level"])

    def test_missing_required_data(self):
        context = dict(self.context)
        context["cape"] = None

        result = self.rule.evaluate(context)

        self.assertEqual(
            result["assessment_status"],
            "INSUFFICIENT_DATA",
        )
        self.assertIsNone(result["potential_level"])
        self.assertIn("cape", result["missing_variables"])

    def test_preserves_provenance(self):
        result = self.rule.evaluate(self.context)

        self.assertEqual(
            result["provenance"]["rule_id"],
            "HAIL_POTENTIAL_001",
        )
        self.assertEqual(
            result["provenance"]["rule_version"],
            "1.0",
        )
        self.assertEqual(
            result["provenance"]["service"],
            "HailPotentialService",
        )


if __name__ == "__main__":
    unittest.main()
