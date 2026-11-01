from unittest import TestCase
from unittest.mock import Mock

from dashboard.services.frost_risk_service import FrostRiskService


class FrostRiskServiceResultTests(TestCase):
    def setUp(self):
        self.service = FrostRiskService.__new__(FrostRiskService)
        self.service.intelligence = Mock()

    def test_evaluate_frost_with_result_returns_complete_single_engine_result(self):
        context = {"municipio_id": 17}
        full_result = {
            "frost": {"score": 17},
            "hail": {"municipio_id": 17, "potential_level": None},
            "rule_results": [{"municipio_id": 17}],
            "insights": [{"municipio_id": 17}],
            "recommendations": [{"municipio_id": 17}],
            "alerts": [{"municipio_id": 17}],
            "explainability": {"municipio_id": 17},
            "provenance": {"municipio_id": 17},
            "versions": {"municipio_id": 17},
            "data_quality": {"municipio_id": 17},
            "experimental_evaluation": {"municipio_id": 17},
        }
        self.service.intelligence.process.return_value = full_result

        result = self.service.evaluate_frost_with_result(context)

        self.assertIs(result, full_result)
        self.assertEqual(result["frost"]["fri"], 17)
        self.assertEqual(result["hail"]["potential_level"], None)
        self.assertEqual(result["rule_results"], [{"municipio_id": 17}])
        self.assertEqual(result["provenance"], {"municipio_id": 17})
        self.assertEqual(result["versions"], {"municipio_id": 17})
        self.assertEqual(result["data_quality"], {"municipio_id": 17})
        self.assertEqual(result["experimental_evaluation"], {"municipio_id": 17})
        self.service.intelligence.process.assert_called_once_with(context)
        self.assertFalse(hasattr(self.service, "last_result"))

    def test_evaluate_frost_keeps_fri_only_compatibility_contract(self):
        context = {"municipio_id": 18}
        self.service.intelligence.process.return_value = {
            "frost": {"score": 18, "severity": "low"},
            "rule_results": [{"municipio_id": 18}],
        }

        result = self.service.evaluate_frost(context)

        self.assertEqual(result, {
            "score": 18,
            "severity": "low",
            "fri": 18,
            "frost_factors": [],
            "confidence": None,
        })
        self.service.intelligence.process.assert_called_once_with(context)
