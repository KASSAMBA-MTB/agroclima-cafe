"""
G7.6 — Testes do SingleRunIndicatorAdapter.
"""

from datetime import datetime, timezone

from django.test import SimpleTestCase

from dashboard.services.single_run_indicator_adapter import (
    SingleRunIndicatorAdapter,
)


class SingleRunIndicatorAdapterTests(SimpleTestCase):
    VARIABLES = SingleRunIndicatorAdapter.VARIABLES

    def setUp(self):
        self.timestamp = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.values = {
            "temperature_2m": ("°C", 18.7),
            "relative_humidity_2m": ("%", 82.0),
            "dew_point_2m": ("°C", 15.2),
            "precipitation": ("mm", None),
            "wind_speed_10m": ("km/h", 12.4),
            "wind_direction_10m": ("°", 140.0),
            "pressure_msl": ("hPa", 1012.3),
            "surface_pressure": ("hPa", 948.1),
            "cape": ("J/kg", 35.0),
            "temperature_850hPa": ("°C", 10.4),
            "relative_humidity_850hPa": ("%", 91.0),
            "geopotential_height_850hPa": ("m", 1487.0),
            "temperature_500hPa": ("°C", -8.6),
            "geopotential_height_500hPa": ("m", 5652.0),
        }

        variables = {}
        for variable, (unit, value) in self.values.items():
            variables[variable] = {
                "unit": unit,
                "value": value,
                "value_status": "MISSING" if value is None else "NUMERIC",
            }

        self.context = {
            "run": {
                "model": "ecmwf_ifs025",
                "source": "open_meteo_single_runs",
            },
            "forecast_count": 1,
            "record_count": 14,
            "forecasts": [
                {
                    "forecast_datetime": self.timestamp,
                    "variables": variables,
                },
            ],
        }
        self.adapter = SingleRunIndicatorAdapter()

    def test_build_series_exposes_all_14_canonical_variables(self):
        result = self.adapter.build_series(self.context)

        self.assertEqual(set(result["series"]), set(self.VARIABLES))
        for variable in self.VARIABLES:
            self.assertEqual(len(result["series"][variable]["values"]), 1)

    def test_build_series_preserves_values_statuses_and_units(self):
        result = self.adapter.build_series(self.context)

        for variable, (unit, value) in self.values.items():
            series = result["series"][variable]
            self.assertEqual(series["values"], [value])
            self.assertEqual(
                series["statuses"],
                ["MISSING" if value is None else "NUMERIC"],
            )
            self.assertEqual(series["units"], [unit])

    def test_missing_precipitation_is_preserved(self):
        result = self.adapter.build_indicator_input(self.context)

        precipitation = result["series"]["precipitation"]
        self.assertIsNone(precipitation["values"][0])
        self.assertEqual(precipitation["statuses"][0], "MISSING")

    def test_indicator_input_exposes_all_14_variables(self):
        result = self.adapter.build_indicator_input(self.context)

        self.assertEqual(set(result["series"]), set(self.VARIABLES))
        self.assertEqual(result["series"]["cape"]["values"], [35.0])
        self.assertEqual(
            result["series"]["wind_direction_10m"]["values"],
            [140.0],
        )
        self.assertEqual(
            result["series"]["temperature_500hPa"]["values"],
            [-8.6],
        )

    def test_indicator_input_preserves_compatibility_aliases(self):
        result = self.adapter.build_indicator_input(self.context)

        self.assertEqual(result["dias"], [self.timestamp])
        self.assertEqual(result["temperatura"], [18.7])
        self.assertEqual(result["precipitacao"], [None])
        self.assertEqual(result["units"]["temperature_2m"], "°C")
        self.assertEqual(result["units"]["precipitation"], "mm")

    def test_indicator_input_does_not_create_eto(self):
        result = self.adapter.build_indicator_input(self.context)

        self.assertEqual(result["eto_mm_day"], [])
        self.assertEqual(result["eto_status"], [])

    def test_adapter_does_not_mutate_context(self):
        original = repr(self.context)
        self.adapter.build_indicator_input(self.context)
        self.assertEqual(repr(self.context), original)
