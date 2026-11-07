import unittest

from core.intelligence.hail_potential_classifier import (
    HailPotentialClassifier,
    CLASSIFIED,
    INSUFFICIENT_DATA,
    NOT_CONFIGURED,
    NOT_CLASSIFIED_OUT_OF_RANGE,
)


class HailPotentialClassifierTests(unittest.TestCase):

    def setUp(self):
        self.config = {
            "version": "TEST-1",
            "source": "TEST",
            "homologated": True,
            "operational": True,
            "levels": [
                {"name": "LOW", "cape_min": 500, "shear_min": 5},
                {"name": "MODERATE", "cape_min": 1000, "shear_min": 10},
            ],
        }
        self.classifier = HailPotentialClassifier(self.config)

    def test_out_of_range_never_returns_unclassified_level(self):
        result = self.classifier.classify(100, 1)
        self.assertEqual(result.status, NOT_CLASSIFIED_OUT_OF_RANGE)
        self.assertIsNone(result.potential_level)
        self.assertFalse(result.homologated)

    def test_configuration_boolean_cannot_homologate(self):
        result = self.classifier.classify(1500, 12)
        self.assertEqual(result.status, CLASSIFIED)
        self.assertEqual(result.potential_level, "MODERATE")
        self.assertFalse(result.homologated)

    def test_missing_data_returns_insufficient_data(self):
        result = self.classifier.classify(None, 12)
        self.assertEqual(result.status, INSUFFICIENT_DATA)
        self.assertIsNone(result.potential_level)

    def test_invalid_numeric_data_returns_insufficient_data(self):
        result = self.classifier.classify("invalid", 12)
        self.assertEqual(result.status, INSUFFICIENT_DATA)
        self.assertIsNone(result.potential_level)

    def test_missing_configuration_returns_not_configured(self):
        result = HailPotentialClassifier().classify(1500, 12)
        self.assertEqual(result.status, NOT_CONFIGURED)
        self.assertFalse(result.homologated)


if __name__ == "__main__":
    unittest.main()
