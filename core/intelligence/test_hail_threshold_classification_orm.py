from django.test import TestCase

from core.intelligence.models import HailThresholdSet
from core.intelligence.hail_threshold_classification_service import (
    HailThresholdClassificationService,
)


class HailThresholdClassificationORMTests(TestCase):

    def create_threshold_set(
        self,
        identifier,
        version,
        status,
        levels=None,
    ):
        return HailThresholdSet.objects.create(
            identifier=identifier,
            version=version,
            status=status,
            source="TEST_FIXTURE",
            threshold_bands={
                "levels": levels or [
                    {
                        "name": "ORM_TEST_LEVEL",
                        "cape_min": 10,
                        "shear_min": 5,
                    }
                ]
            },
        )

    def test_uses_persisted_provisional_set_without_explicit_argument(self):
        provisional = self.create_threshold_set(
            "ORM_INTEGRATION",
            "1.0",
            HailThresholdSet.Status.PROVISIONAL,
        )

        self.create_threshold_set(
            "ORM_DRAFT",
            "1.0",
            HailThresholdSet.Status.DRAFT,
        )

        service = HailThresholdClassificationService()

        result = service.evaluate({
            "derived": {
                "cape": 100,
                "shear_925_500": 10,
            }
        })

        self.assertEqual(result["classification_status"], "CLASSIFIED")
        self.assertEqual(result["potential_level"], "ORM_TEST_LEVEL")
        self.assertEqual(result["threshold_set_id"], str(provisional.pk))
        self.assertEqual(result["threshold_set_status"], "PROVISIONAL")
        self.assertEqual(result["thresholds_source"], "TEST_FIXTURE")
        self.assertFalse(result["homologated"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["is_factual_event"])

    def test_without_provisional_set_returns_not_configured(self):
        self.create_threshold_set(
            "ORM_ONLY_DRAFT",
            "1.0",
            HailThresholdSet.Status.DRAFT,
        )

        service = HailThresholdClassificationService()

        result = service.evaluate({
            "derived": {
                "cape": 100,
                "shear_925_500": 10,
            }
        })

        self.assertEqual(result["classification_status"], "NOT_CONFIGURED")
        self.assertIsNone(result["potential_level"])
        self.assertIsNone(result["threshold_set_id"])
        self.assertFalse(result["homologated"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["is_factual_event"])

    def test_provisional_set_with_missing_meteorology_is_insufficient(self):
        provisional = self.create_threshold_set(
            "ORM_MISSING_DATA",
            "1.0",
            HailThresholdSet.Status.PROVISIONAL,
        )

        service = HailThresholdClassificationService()

        result = service.evaluate({"derived": {}})

        self.assertEqual(
            result["classification_status"],
            "INSUFFICIENT_DATA",
        )
        self.assertEqual(result["threshold_set_id"], str(provisional.pk))
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["homologated"])
        self.assertFalse(result["operational"])
        self.assertFalse(result["is_factual_event"])
