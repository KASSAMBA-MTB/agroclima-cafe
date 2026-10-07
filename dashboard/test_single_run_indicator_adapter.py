"""
G7.5 / G6 — Testes do SingleRunIndicatorAdapter.

Destino:
    dashboard/test_single_run_indicator_adapter.py
"""

from datetime import datetime, timezone

from django.test import SimpleTestCase

from dashboard.services.single_run_indicator_adapter import (
    SingleRunIndicatorAdapter,
)


class SingleRunIndicatorAdapterTests(SimpleTestCase):
    def setUp(self):
        self.timestamp = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.context = {
            "run": {
                "model": "ecmwf_ifs025",
                "source": "open_meteo_single_runs",
            },
            "forecast_count": 2,
            "record_count": 4,
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
                },
                {
                    "forecast_datetime": self.timestamp.replace(hour=1),
                    "variables": {
                        "temperature_2m": {
                            "unit": "°C",
                            "value": 18.8,
                            "value_status": "NUMERIC",
                        },
                        "precipitation": {
                            "unit": "mm",
                            "value": 0.2,
                            "value_status": "NUMERIC",
                        },
                    },
                },
            ],
        }
        self.adapter = SingleRunIndicatorAdapter()

    def test_build_series_preserves_values_and_statuses(self):
        result = self.adapter.build_series(self.context)
        temperature = result["series"]["temperature_2m"]

        self.assertEqual(temperature["values"], [18.7, 18.8])
        self.assertEqual(
            temperature["statuses"],
            ["NUMERIC", "NUMERIC"],
        )
        self.assertEqual(temperature["units"], ["°C", "°C"])

    def test_missing_precipitation_is_preserved(self):
        result = self.adapter.build_series(self.context)
        precipitation = result["series"]["precipitation"]

        self.assertIsNone(precipitation["values"][0])
        self.assertEqual(
            precipitation["statuses"][0],
            "MISSING",
        )
        self.assertEqual(precipitation["values"][1], 0.2)

    def test_indicator_input_does_not_create_eto(self):
        result = self.adapter.build_indicator_input(self.context)

        self.assertEqual(result["eto_mm_day"], [])
        self.assertEqual(result["eto_status"], [])

    def test_indicator_input_has_canonical_series(self):
        result = self.adapter.build_indicator_input(self.context)

        self.assertEqual(result["dias"], [self.timestamp, self.timestamp.replace(hour=1)])
        self.assertEqual(result["temperatura"], [18.7, 18.8])
        self.assertEqual(result["precipitacao"], [None, 0.2])
        self.assertEqual(result["units"]["temperature_2m"], "°C")
        self.assertEqual(result["units"]["precipitation"], "mm")

    def test_adapter_does_not_mutate_context(self):
        original = repr(self.context)
        self.adapter.build_indicator_input(self.context)
        self.assertEqual(repr(self.context), original)
