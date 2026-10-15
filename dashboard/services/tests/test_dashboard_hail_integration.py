"""Regressão da exposição municipal do resultado experimental de granizo."""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from core.intelligence.hail_potential_contract import (
    ASSESSMENT_INSUFFICIENT,
)
from core.intelligence.rules.hail_potential_rule import HailPotentialRule
from dashboard.services.dashboard_service import DashboardService


class DashboardHailIntegrationTests(SimpleTestCase):
    def test_missing_required_inputs_remain_unclassified(self):
        result = HailPotentialRule().evaluate({
            "municipio_id": 17,
            "municipio_nome": "Município de teste",
        })

        self.assertEqual(
            result["assessment_status"],
            ASSESSMENT_INSUFFICIENT,
        )
        self.assertIsNone(result["potential_level"])
        self.assertTrue(result["missing_variables"])
        self.assertEqual(result["municipio_id"], 17)

    def test_dashboard_exposes_hail_from_the_single_intelligence_result(self):
        hail = {
            "id": "HAIL_POTENTIAL_001",
            "rule_id": "HAIL_POTENTIAL_001",
            "assessment_status": ASSESSMENT_INSUFFICIENT,
            "potential_level": None,
            "missing_variables": [
                "cape",
                "wind_speed_925hPa",
                "wind_direction_925hPa",
                "wind_speed_500hPa",
                "wind_direction_500hPa",
            ],
        }
        frost = {"fri": 18, "score": 18}
        intelligence = {
            "frost": frost,
            "hail": hail,
            "rule_results": [hail],
            "insights": [],
            "recommendations": [],
            "alerts": [],
            "explainability": {},
        }
        risk_service = Mock()
        risk_service.evaluate_frost.return_value = frost
        risk_service.last_result = intelligence

        service = DashboardService.__new__(DashboardService)
        service.frost_risk_service = risk_service

        acquired = {
            "series": {
                "cape": 1200,
                "wind_speed_925hPa": 12,
                "wind_direction_925hPa": 270,
                "wind_speed_500hPa": 25,
                "wind_direction_500hPa": 240,
            },
            "provenance": {"source": "open-meteo-forecast-api", "model": "ecmwf_ifs025"},
            "valid_from": "2026-10-15T12:00",
            "valid_to": "2026-10-15T12:00",
        }
        with patch(
            "dashboard.services.dashboard_service.HailMeteorologicalInputService"
        ) as input_service:
            input_service.return_value.fetch_for_points.return_value = {17: acquired}
            result = service._attach_frost_intelligence([
                {"id": 17, "nome": "Município de teste", "latitude": -21.9, "longitude": -46.9},
            ])

        input_service.return_value.fetch_for_points.assert_called_once()
        evaluation_context = risk_service.evaluate_frost.call_args.args[0]
        self.assertEqual(evaluation_context["series"], acquired["series"])
        self.assertEqual(evaluation_context["provenance"], acquired["provenance"])
        self.assertEqual(evaluation_context["valid_from"], acquired["valid_from"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["hail_potential_evaluation"], hail)
        self.assertEqual(
            result[0]["intelligence_evaluation"]["hail"],
            hail,
        )
        self.assertIsNone(
            result[0]["intelligence_evaluation"]["hail"]["potential_level"]
        )
        risk_service.evaluate_frost.assert_called_once()
