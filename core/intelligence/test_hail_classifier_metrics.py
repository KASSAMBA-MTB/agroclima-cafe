from django.test import SimpleTestCase

from core.intelligence.hail_classifier_metrics import HailClassifierMetrics


class HailClassifierMetricsTests(SimpleTestCase):
    def setUp(self):
        self.service = HailClassifierMetrics()

    def test_calcula_matriz_de_confusao_e_metricas(self):
        report = self.service.evaluate([
            {"reference_label": "HAIL_CONFIRMED", "predicted_label": "HAIL"},
            {"reference_label": "HAIL_CONFIRMED", "predicted_label": "NO_HAIL"},
            {"reference_label": "CONTROL", "predicted_label": "HAIL"},
            {"reference_label": "CONTROL", "predicted_label": "NO_HAIL"},
        ])
        self.assertEqual(report["status"], "METRICS_COMPUTED")
        self.assertEqual(report["confusion_matrix"], {
            "true_positive": 1,
            "true_negative": 1,
            "false_positive": 1,
            "false_negative": 1,
        })
        self.assertEqual(report["metrics"]["pod"], 0.5)
        self.assertEqual(report["metrics"]["far"], 0.5)
        self.assertEqual(report["metrics"]["csi"], 1 / 3)
        self.assertEqual(report["metrics"]["hss"], 0.0)
        self.assertFalse(report["classification_performed_by_this_component"])

    def test_exclui_referencias_incertas(self):
        report = self.service.evaluate([
            {"reference_label": "UNCERTAIN", "predicted_label": "HAIL"},
            {"reference_label": "HAIL_CONFIRMED", "predicted_label": "HAIL"},
            {"reference_label": "CONTROL", "predicted_label": "NO_HAIL"},
        ])
        self.assertEqual(report["sample_counts"]["uncertain_excluded"], 1)
        self.assertEqual(report["sample_counts"]["evaluated"], 2)
        self.assertEqual(report["metrics"]["pod"], 1.0)
        self.assertEqual(report["metrics"]["far"], 0.0)

    def test_denominadores_zero_retornam_none(self):
        report = self.service.evaluate([
            {"reference_label": "CONTROL", "predicted_label": "NO_HAIL"},
        ])
        self.assertIsNone(report["metrics"]["pod"])
        self.assertIsNone(report["metrics"]["far"])
        self.assertIsNone(report["metrics"]["csi"])
        self.assertIsNone(report["metrics"]["hss"])

    def test_registros_invalidos_sao_rejeitados(self):
        report = self.service.evaluate([
            {"reference_label": "HAIL_CONFIRMED", "predicted_label": "MAYBE"},
        ])
        self.assertEqual(report["status"], "DATA_QUALITY_REVIEW_REQUIRED")
        self.assertEqual(report["sample_counts"]["rejected"], 1)
        self.assertEqual(report["sample_counts"]["evaluated"], 0)
