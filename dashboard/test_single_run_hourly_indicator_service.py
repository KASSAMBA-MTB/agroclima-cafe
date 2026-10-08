from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from dashboard.services.single_run_hourly_indicator_service import (
    SingleRunHourlyIndicatorService,
)


class SingleRunHourlyIndicatorServiceTests(SimpleTestCase):
    def setUp(self):
        start = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.context = {
            "run": {
                "source": "open_meteo_single_runs",
                "model": "ecmwf_ifs025",
                "run_datetime": start,
            },
            "forecast_count": 2,
            "record_count": 4,
            "forecast": {
                "temperature_2m": [
                    {
                        "forecast_datetime": start,
                        "unit": "°C",
                        "value": 18.7,
                        "value_status": "NUMERIC",
                    },
                    {
                        "forecast_datetime": start + timedelta(hours=1),
                        "unit": "°C",
                        "value": None,
                        "value_status": "MISSING",
                    },
                ],
                "precipitation": [
                    {
                        "forecast_datetime": start,
                        "unit": "mm",
                        "value": None,
                        "value_status": "MISSING",
                    },
                    {
                        "forecast_datetime": start + timedelta(hours=1),
                        "unit": "mm",
                        "value": 0.3,
                        "value_status": "NUMERIC",
                    },
                ],
                "relative_humidity_2m": [
                    {
                        "forecast_datetime": start,
                        "unit": "%",
                        "value": 70.0,
                        "value_status": "NUMERIC",
                    },
                ],
                "wind_speed_10m": [
                    {
                        "forecast_datetime": start,
                        "unit": "km/h",
                        "value": 8.0,
                        "value_status": "NUMERIC",
                    },
                ],
            },
        }

    def test_exposes_all_14_canonical_variables(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)
        self.assertEqual(
            result["variables"],
            list(SingleRunHourlyIndicatorService.VARIABLES),
        )
        self.assertEqual(
            set(result["series"]),
            set(SingleRunHourlyIndicatorService.VARIABLES),
        )

    def test_preserves_canonical_value_status_unit_and_timestamp(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)

        temperature = result["series"]["temperature_2m"]
        self.assertEqual(temperature["timestamps"][0], self.context["forecast"]["temperature_2m"][0]["forecast_datetime"])
        self.assertEqual(temperature["values"], [18.7, None])
        self.assertEqual(temperature["statuses"], ["NUMERIC", "MISSING"])
        self.assertEqual(temperature["units"], ["°C", "°C"])

        precipitation = result["series"]["precipitation"]
        self.assertEqual(precipitation["values"], [None, 0.3])
        self.assertEqual(precipitation["statuses"], ["MISSING", "NUMERIC"])

    def test_accepts_g7_6_series_input_with_all_14_variables(self):
        start = datetime(2026, 10, 3, tzinfo=timezone.utc)
        series = {}
        for variable in SingleRunHourlyIndicatorService.VARIABLES:
            series[variable] = {
                "timestamps": [start],
                "values": [1.0],
                "statuses": ["NUMERIC"],
                "units": ["unit"],
            }

        result = SingleRunHourlyIndicatorService().calculate({
            "run": {"model": "ecmwf_ifs025"},
            "forecast_count": 1,
            "record_count": 14,
            "series": series,
        })

        self.assertEqual(result["series"]["cape"]["values"], [1.0])
        self.assertEqual(
            result["series"]["temperature_500hPa"]["values"],
            [1.0],
        )
        self.assertEqual(
            result["series"]["wind_direction_10m"]["statuses"],
            ["NUMERIC"],
        )

    def test_non_aggregated_variables_are_not_given_arbitrary_aggregates(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)

        self.assertNotIn("dew_point_2m", result)
        self.assertNotIn("wind_direction_10m", result)
        self.assertNotIn("pressure_msl", result)
        self.assertNotIn("cape", result)
        self.assertNotIn("temperature_850hPa", result)
        self.assertNotIn("temperature_500hPa", result)

    def test_calculates_hourly_temperature_without_fabricating_missing(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)
        self.assertEqual(result["frequency"], "HOURLY")
        self.assertEqual(result["temperature_2m"]["numeric_count"], 1)
        self.assertEqual(result["temperature_2m"]["missing_count"], 1)
        self.assertEqual(result["temperature_2m"]["min"], 18.7)
        self.assertEqual(result["temperature_2m"]["max"], 18.7)

    def test_precipitation_missing_is_not_zero(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)
        precipitation = result["precipitation"]
        self.assertEqual(precipitation["numeric_count"], 1)
        self.assertEqual(precipitation["missing_count"], 1)
        self.assertEqual(precipitation["min"], 0.3)
        self.assertEqual(precipitation["max"], 0.3)

    def test_run_metadata_and_counts_are_preserved(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)
        self.assertEqual(result["forecast_count"], 2)
        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["run"]["model"], "ecmwf_ifs025")

    def test_no_valid_values_returns_null_aggregates(self):
        context = {
            "forecast": {
                "temperature_2m": [
                    {
                        "value": None,
                        "value_status": "MISSING",
                    },
                ],
            },
        }
        result = SingleRunHourlyIndicatorService().calculate(context)
        self.assertIsNone(result["temperature_2m"]["min"])
        self.assertIsNone(result["temperature_2m"]["max"])
        self.assertIsNone(result["temperature_2m"]["mean"])
        self.assertEqual(
            result["temperature_2m"]["missing_count"],
            1,
        )

    def test_invalid_numeric_values_are_ignored(self):
        context = {
            "forecast": {
                "temperature_2m": [
                    {
                        "value": float("nan"),
                        "value_status": "NUMERIC",
                    },
                    {
                        "value": 20.0,
                        "value_status": "NUMERIC",
                    },
                ],
            },
        }
        result = SingleRunHourlyIndicatorService().calculate(context)
        self.assertEqual(result["temperature_2m"]["numeric_count"], 1)
        self.assertEqual(result["temperature_2m"]["min"], 20.0)

    def test_does_not_create_daily_contract(self):
        result = SingleRunHourlyIndicatorService().calculate(self.context)
        self.assertEqual(result["frequency"], "HOURLY")
        self.assertNotIn("dias", result)
        self.assertNotIn("eto_mm_day", result)
        self.assertNotIn("hydric_balance_version", result)
