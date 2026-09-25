from unittest import TestCase
from unittest.mock import MagicMock, patch

from core.intelligence.engine import IntelligenceEngine, RuleEngine
from core.intelligence.interpretation_coordinator import (
    InterpretationCoordinator,
)


class TestMP0145InterpretationCoordinator(TestCase):

    def test_01_rule_engine_to_coordinator(self):
        coordinator = InterpretationCoordinator()

        rule_results = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
                "score": 80,
            }
        ]

        result = coordinator.coordinate({}, rule_results)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rule_id"], "FROST_001")
        self.assertEqual(result[0]["coordination_status"], "coordinated")

    def test_02_original_rule_results_are_preserved(self):
        engine = IntelligenceEngine()

        original = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
                "score": 80,
            }
        ]

        engine.rule_engine.evaluate = MagicMock(
            return_value=original
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=original.copy()
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        result = engine.process({})

        self.assertIs(
            result["rule_results"],
            original,
        )

    def test_03_coordinated_results_are_returned(self):
        engine = IntelligenceEngine()

        rule_results = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
            }
        ]

        coordinated = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
                "coordination_status": "coordinated",
            }
        ]

        engine.rule_engine.evaluate = MagicMock(
            return_value=rule_results
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=coordinated
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        result = engine.process({})

        self.assertEqual(
            result["coordinated_results"],
            coordinated,
        )

    def test_04_coordinator_deduplicates_rule_results(self):
        coordinator = InterpretationCoordinator()

        rule_results = [
            {
                "rule_id": "FROST_001",
                "score": 80,
            },
            {
                "rule_id": "FROST_001",
                "score": 90,
            },
        ]

        result = coordinator.coordinate({}, rule_results)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["score"], 80)

    def test_05_frost_rule_is_preserved(self):
        engine = IntelligenceEngine()

        frost = {
            "rule_id": "FROST_001",
            "channel": "frost",
            "fri": 75,
            "score": 75,
        }

        engine.rule_engine.evaluate = MagicMock(
            return_value=[frost]
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=[frost]
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        result = engine.process({})

        self.assertEqual(
            result["frost"]["rule_id"],
            "FROST_001",
        )

        self.assertEqual(
            result["frost"]["fri"],
            75,
        )

    def test_06_alert_rule_is_preserved(self):
        engine = IntelligenceEngine()

        alert = {
            "rule_id": "METEO_ALERT_001",
            "channel": "alert",
            "severity": "warning",
        }

        engine.rule_engine.evaluate = MagicMock(
            return_value=[alert]
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=[alert]
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        engine.process({})

        engine.alert_engine.generate.assert_called_once()

        alert_inputs = (
            engine.alert_engine.generate.call_args.args[0]
        )

        self.assertIn(alert, alert_inputs)

    def test_07_insight_engine_receives_coordinated_results(self):
        engine = IntelligenceEngine()

        coordinated = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
            }
        ]

        engine.rule_engine.evaluate = MagicMock(
            return_value=coordinated
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=coordinated
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        engine.process({})

        engine.insight_engine.generate.assert_called_once_with(
            coordinated
        )

    def test_08_alert_engine_receives_coordinated_alert_results(self):
        engine = IntelligenceEngine()

        alert = {
            "rule_id": "METEO_ALERT_001",
            "channel": "alert",
        }

        engine.rule_engine.evaluate = MagicMock(
            return_value=[alert]
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=[alert]
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        engine.process({})

        engine.alert_engine.generate.assert_called_once()

        inputs = (
            engine.alert_engine.generate.call_args.args[0]
        )

        self.assertIn(alert, inputs)

    def test_09_explainability_receives_coordinated_results(self):
        engine = IntelligenceEngine()

        coordinated = [
            {
                "rule_id": "FROST_001",
                "channel": "frost",
            }
        ]

        engine.rule_engine.evaluate = MagicMock(
            return_value=coordinated
        )

        engine.interpretation_coordinator.coordinate = MagicMock(
            return_value=coordinated
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        engine.process({})

        engine.explainability_engine.process.assert_called_once_with(
            {},
            coordinated,
        )

    def test_10_rules_are_executed_only_once_per_process(self):
        engine = IntelligenceEngine()

        rule = MagicMock()

        rule.evaluate.return_value = {
            "rule_id": "TEST_RULE",
            "channel": "test",
        }

        engine.rule_engine.rules = [rule]

        engine.interpretation_coordinator.coordinate = MagicMock(
            side_effect=lambda context, results: results
        )

        engine.insight_engine.generate = MagicMock(
            return_value=[]
        )

        engine.recommendation_engine.generate = MagicMock(
            return_value=[]
        )

        engine.alert_engine.generate = MagicMock(
            return_value=[]
        )

        engine.explainability_engine.process = MagicMock(
            return_value={}
        )

        engine.process({})

        rule.evaluate.assert_called_once_with({})