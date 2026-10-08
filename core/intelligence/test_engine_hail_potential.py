
from unittest import TestCase

from core.intelligence.engine import IntelligenceEngine
from core.intelligence.rules.hail_potential_rule import HailPotentialRule


class FakeHailService:
    def evaluate(self, context):
        return {
            "status": "ASSESSED",
            "potential_level": None,
            "shear_ms": 25.327,
            "cape_shear": 24313.545,
            "provenance": {
                "source": "historical_forecast_api",
                "source_run": "2025-07-25",
            },
            "drivers": [
                {
                    "variable": "cape",
                    "observed_value": 960,
                },
                {
                    "variable": "wind_shear_925_500",
                    "observed_value": 25.327,
                },
            ],
        }


class IntelligenceEngineHailIntegrationTests(TestCase):

    def setUp(self):
        self.engine = IntelligenceEngine()

        hail_rule = next(
            rule
            for rule in self.engine.rule_engine.rules
            if isinstance(rule, HailPotentialRule)
        )

        hail_rule.service = FakeHailService()

    def test_hail_rule_is_registered(self):
        rules = self.engine.rule_engine.rules

        self.assertTrue(
            any(
                isinstance(rule, HailPotentialRule)
                for rule in rules
            )
        )

    def test_hail_rule_id_is_registered(self):
        result = self.engine.evaluate_hail({})

        self.assertEqual(
            result["rule_id"],
            "HAIL_POTENTIAL_001",
        )

    def test_hail_result_is_exposed_by_process(self):
        result = self.engine.process({})

        self.assertIn("hail", result)

        self.assertEqual(
            result["hail"]["status"],
            "ASSESSED",
        )

    def test_hail_calculations_are_preserved(self):
        result = self.engine.evaluate_hail({})

        self.assertAlmostEqual(
            result["shear_ms"],
            25.327,
            places=3,
        )

        self.assertAlmostEqual(
            result["cape_shear"],
            24313.545,
            places=3,
        )

    def test_hail_does_not_create_insight_or_alert(self):
        result = self.engine.process({})

        hail_id = "HAIL_POTENTIAL_001"

        self.assertFalse(
            any(
                item.get("id") == hail_id
                or item.get("rule_id") == hail_id
                for item in result["insights"]
                if isinstance(item, dict)
            )
        )

        self.assertFalse(
            any(
                item.get("id") == hail_id
                or item.get("rule_id") == hail_id
                for item in result["recommendations"]
                if isinstance(item, dict)
            )
        )

        self.assertFalse(
            any(
                item.get("id") == hail_id
                or item.get("rule_id") == hail_id
                for item in result["alerts"]
                if isinstance(item, dict)
            )
        )

    def test_hail_classification_is_not_invented(self):
        result = self.engine.evaluate_hail({})

        self.assertIsNone(
            result["potential_level"]
        )

    def test_existing_frost_api_remains_available(self):
        self.assertTrue(
            hasattr(self.engine, "evaluate_frost")
        )
