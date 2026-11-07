from unittest import TestCase
from unittest.mock import patch
from dashboard.services.dashboard_service import DashboardService

class HailThresholdClassificationIntegrationTests(TestCase):
    @patch('dashboard.services.dashboard_service.HailThresholdClassificationService')
    def test_classification_is_projected_per_municipality(self, service_class):
        service = service_class.return_value
        service.evaluate.side_effect = [
            {'potential_level': 'TEST_A', 'homologated': False, 'operational': False, 'is_factual_event': False},
            {'potential_level': 'TEST_B', 'homologated': False, 'operational': False, 'is_factual_event': False},
        ]
        hail = {'assessment_status': 'ASSESSED', 'rule_id': 'HAIL_POTENTIAL_001', 'derived': {}, 'complementary_values': {}, 'experimental_evaluation': {}}
        points = [
            {'id': 3500402, 'nome': 'A', 'intelligence_evaluation': {'hail': dict(hail)}},
            {'id': 3500403, 'nome': 'B', 'intelligence_evaluation': {'hail': dict(hail)}},
        ]
        result = DashboardService._compose_hail_assessments(points)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['experimental_threshold_classification']['potential_level'], 'TEST_A')
        self.assertEqual(result[1]['experimental_threshold_classification']['potential_level'], 'TEST_B')
        for item in result:
            self.assertIsNone(item.get('potential_level'))
            c = item['experimental_threshold_classification']
            self.assertFalse(c['homologated'])
            self.assertFalse(c['operational'])
            self.assertFalse(c['is_factual_event'])
        self.assertEqual(service.evaluate.call_count, 2)
