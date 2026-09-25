from unittest import TestCase

from core.intelligence.explainability_engine import ExplainabilityEngine


class TestMP0146ExplainabilityEngine(TestCase):

    def setUp(self):
        self.engine = ExplainabilityEngine()

    def test_01_processes_real_rule_result(self):
        context = {
            "municipio_id": 1,
            "municipio_nome": "Poços de Caldas",
            "analysis_date": "2026-09-25",
        }

        results = [{
            "rule_id": "FROST_001",
            "rule_version": "2.0",
            "channel": "frost",
            "severity": "high",
            "confidence": 0.90,
            "score": 80,
            "factors": ["temperature_min", "humidity"],
            "provenance": "FrostRule",
            "coordinator_version": "1.2",
            "policy_version": "1.0",
            "coordination_status": "coordinated",
        }]

        output = self.engine.process(context, results)

        self.assertEqual(output["version"], "2.0")
        self.assertEqual(output["rule_count"], 1)
        self.assertEqual(len(output["rules"]), 1)

    def test_02_preserves_rule_identity_and_version(self):
        result = {
            "rule_id": "FROST_001",
            "rule_version": "2.0",
        }

        output = self.engine.process({}, [result])
        explanation = output["rules"][0]

        self.assertEqual(explanation["rule_id"], "FROST_001")
        self.assertEqual(explanation["rule_version"], "2.0")

    def test_03_preserves_decision_fields(self):
        result = {
            "rule_id": "FROST_001",
            "severity": "high",
            "severity_label": "Alto",
            "confidence": 0.90,
            "score": 80,
        }

        output = self.engine.process({}, [result])
        explanation = output["rules"][0]

        self.assertEqual(explanation["severity"], "high")
        self.assertEqual(explanation["severity_label"], "Alto")
        self.assertEqual(explanation["confidence"], 0.90)
        self.assertEqual(explanation["score"], 80)

    def test_04_preserves_factors(self):
        result = {
            "rule_id": "FROST_001",
            "factors": ["temperature_min", "humidity"],
        }

        output = self.engine.process({}, [result])
        explanation = output["rules"][0]

        self.assertEqual(
            explanation["factors"],
            ["temperature_min", "humidity"],
        )

    def test_05_preserves_municipality_and_date(self):
        context = {
            "municipio_id": 10,
            "municipio_nome": "Poços de Caldas",
            "analysis_date": "2026-09-25",
        }

        result = {"rule_id": "FROST_001"}

        output = self.engine.process(context, [result])
        explanation = output["rules"][0]

        self.assertEqual(explanation["municipio_id"], 10)
        self.assertEqual(
            explanation["municipio_nome"],
            "Poços de Caldas",
        )
        self.assertEqual(
            explanation["analysis_date"],
            "2026-09-25",
        )

    def test_06_preserves_provenance_and_coordination(self):
        result = {
            "rule_id": "FROST_001",
            "provenance": "FrostRule",
            "coordinator_version": "1.2",
            "policy_version": "1.0",
            "coordination_status": "coordinated",
        }

        output = self.engine.process({}, [result])
        explanation = output["rules"][0]

        self.assertEqual(explanation["provenance"], "FrostRule")
        self.assertEqual(
            explanation["coordinator_version"],
            "1.2",
        )
        self.assertEqual(
            explanation["policy_version"],
            "1.0",
        )
        self.assertEqual(
            explanation["coordination_status"],
            "coordinated",
        )

    def test_07_does_not_create_missing_evidence(self):
        result = {
            "rule_id": "FROST_001",
            "score": 80,
        }

        output = self.engine.process({}, [result])
        explanation = output["rules"][0]

        self.assertIsNone(explanation["confidence"])
        self.assertIsNone(explanation["metric"])
        self.assertIsNone(explanation["metric_value"])
        self.assertEqual(explanation["factors"], [])

    def test_08_empty_results_produce_empty_explanation(self):
        output = self.engine.process({}, [])

        self.assertEqual(output["rule_count"], 0)
        self.assertEqual(output["rules"], [])

    def test_09_invalid_results_are_ignored(self):
        results = [
            None,
            "invalid",
            123,
            {"rule_id": "FROST_001"},
        ]

        output = self.engine.process({}, results)

        self.assertEqual(output["rule_count"], 1)
        self.assertEqual(
            output["rules"][0]["rule_id"],
            "FROST_001",
        )

    def test_10_multiple_rules_are_explained_independently(self):
        results = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
                "score": 80,
            },
            {
                "rule_id": "METEO_ALERT_001",
                "channel": "alert",
                "severity": "warning",
            },
        ]

        output = self.engine.process({}, results)

        self.assertEqual(output["rule_count"], 2)
        self.assertEqual(
            output["rules"][0]["rule_id"],
            "FROST_001",
        )
        self.assertEqual(
            output["rules"][1]["rule_id"],
            "METEO_ALERT_001",
        )