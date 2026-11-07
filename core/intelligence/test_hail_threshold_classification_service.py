from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from core.intelligence.hail_threshold_classification_service import (
    HailThresholdClassificationService,
)


class HailThresholdClassificationServiceTests(TestCase):

    def setUp(self):
        self.model = MagicMock()
        self.service = HailThresholdClassificationService(
            threshold_set_model=self.model
        )

    def test_without_threshold_set_remains_not_configured(self):
        self.model.objects.filter.return_value.order_by.return_value.first.return_value = None

        result = self.service.evaluate({"derived": {"cape": 100}})

        self.assertEqual(result["classification_status"], "NOT_CONFIGURED")
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["homologated"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["is_factual_event"])

    def test_invalid_threshold_bands_remain_not_configured(self):
        threshold = SimpleNamespace(
            pk=1,
            identifier="TEST",
            version="0.1",
            status="PROVISIONAL",
            source="fixture",
            threshold_bands=[],
            created_at=None,
        )
        self.model.objects.filter.return_value.order_by.return_value.first.return_value = threshold

        result = self.service.evaluate({})

        self.assertEqual(result["classification_status"], "NOT_CONFIGURED")
        self.assertIsNone(result["potential_level"])

    def test_missing_meteorological_input_is_insufficient(self):
        threshold = SimpleNamespace(
            pk=1,
            identifier="TEST",
            version="0.1",
            status="PROVISIONAL",
            source="fixture",
            threshold_bands=[
                {"name": "TEST", "cape_min": 10, "shear_min": 5}
            ],
            created_at=None,
        )
        self.model.objects.filter.return_value.order_by.return_value.first.return_value = threshold

        result = self.service.evaluate(
            {"derived": {}},
            threshold_set=threshold,
        )

        self.assertEqual(result["classification_status"], "INSUFFICIENT_DATA")
        self.assertFalse(result["operational"])
        self.assertFalse(result["is_factual_event"])

    def test_extract_inputs_uses_canonical_derived_values(self):
        cape, shear = self.service._extract_inputs({
            "derived": {
                "cape": 1200,
                "shear_925_500": 18,
            }
        })

        self.assertEqual(cape, 1200)
        self.assertEqual(shear, 18)

    def test_invalid_numbers_are_rejected(self):
        cape, shear = self.service._extract_inputs({
            "derived": {
                "cape": float("nan"),
                "shear_925_500": True,
            }
        })

        self.assertIsNone(cape)
        self.assertIsNone(shear)
