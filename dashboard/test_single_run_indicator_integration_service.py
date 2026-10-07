"""
G7.5 / G6 — Testes da fronteira de integração de indicadores Single Run.

Destino:
    dashboard/test_single_run_indicator_integration_service.py
"""

from datetime import datetime, timezone

from django.test import SimpleTestCase

from dashboard.services.single_run_indicator_integration_service import (
    SingleRunIndicatorIntegrationService,
)


class FakeDomainService:
    def __init__(self, context):
        self.context = context
        self.calls = []

    def get_context(self, **kwargs):
        self.calls.append(kwargs)
        return self.context

    def get_context_for_run(self, **kwargs):
        self.calls.append(kwargs)
        return self.context


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def build_indicator_input(self, context):
        self.calls.append(context)
        return {
            "run": context["run"],
            "dias": [context["forecasts"][0]["forecast_datetime"]],
            "temperatura": [18.7],
            "temperatura_status": ["NUMERIC"],
            "precipitacao": [None],
            "precipitacao_status": ["MISSING"],
            "eto_mm_day": [],
            "eto_status": [],
            "units": {
                "temperature_2m": "°C",
                "precipitation": "mm",
            },
            "forecast_count": 1,
            "record_count": 2,
        }


class SingleRunIndicatorIntegrationServiceTests(SimpleTestCase):
    def setUp(self):
        self.timestamp = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.context = {
            "run": {
                "source": "open_meteo_single_runs",
                "model": "ecmwf_ifs025",
            },
            "forecast_count": 1,
            "record_count": 2,
            "forecasts": [
                {
                    "forecast_datetime": self.timestamp,
                    "variables": {
                        "temperature_2m": {
                            "unit": "°C",
                            "value": 18.7,
                            "value_status": "NUMERIC",
                        },
                        "precipitation": {
                            "unit": "mm",
                            "value": None,
                            "value_status": "MISSING",
                        },
                    },
                }
            ],
        }
        self.domain = FakeDomainService(self.context)
        self.adapter = FakeAdapter()
        self.service = SingleRunIndicatorIntegrationService(
            domain_service=self.domain,
            adapter=self.adapter,
        )

    def test_orchestrates_domain_then_adapter(self):
        result = self.service.get_indicator_context(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=self.timestamp,
            lat=-21.75,
            lon=-46.50,
            cell_selection="land",
        )

        self.assertEqual(result["temperatura"], [18.7])
        self.assertEqual(result["precipitacao"], [None])
        self.assertEqual(result["precipitacao_status"], ["MISSING"])
        self.assertEqual(len(self.domain.calls), 1)
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertIs(self.adapter.calls[0], self.context)

    def test_identity_is_passed_without_recalculation(self):
        self.service.get_indicator_context(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=self.timestamp,
            lat=-21.75,
            lon=-46.50,
            cell_selection="land",
        )

        call = self.domain.calls[0]
        self.assertEqual(call["source"], "open_meteo_single_runs")
        self.assertEqual(call["model"], "ecmwf_ifs025")
        self.assertEqual(call["run_datetime"], self.timestamp)
        self.assertEqual(call["lat"], -21.75)
        self.assertEqual(call["lon"], -46.50)
        self.assertEqual(call["cell_selection"], "land")

    def test_existing_model_run_path_uses_domain_service(self):
        marker = object()

        result = self.service.get_indicator_context_for_run(
            model_run=marker
        )

        self.assertEqual(result["temperatura"], [18.7])
        self.assertEqual(len(self.domain.calls), 1)
        self.assertIs(self.domain.calls[0]["model_run"], marker)

    def test_no_daily_aggregation_or_eto_is_created(self):
        result = self.service.get_indicator_context(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=self.timestamp,
            lat=-21.75,
            lon=-46.50,
            cell_selection="land",
        )

        self.assertEqual(result["eto_mm_day"], [])
        self.assertEqual(result["forecast_count"], 1)
        self.assertEqual(result["record_count"], 2)
