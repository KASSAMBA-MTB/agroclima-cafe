# ARQUIVO: clima/test_single_run_forecast_query_service.py
# TIPO: código Python — substituir a versão V1.
# FINALIDADE: testes unitários do consumidor operacional horário.

from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock

from clima.services.single_run_forecast_query_service import (
    SingleRunForecastQueryService,
)


class SingleRunForecastQueryServiceTests(TestCase):

    def setUp(self) -> None:
        self.domain_service = Mock()
        self.service = SingleRunForecastQueryService(
            domain_service=self.domain_service
        )

    def _context(self) -> dict:
        return {
            "run": {
                "id": 1,
                "source": "open_meteo_single_runs",
                "model": "ecmwf_ifs025",
                "run_datetime": "2026-10-03T00:00:00Z",
                "lat": "-21.787400",
                "lon": "-46.561400",
                "timezone": "GMT",
                "cell_selection": "land",
            },
            "record_count": 4,
            "forecasts": [
                {
                    "forecast_datetime": "2026-10-03T00:00:00Z",
                    "variables": {
                        "precipitation": {
                            "unit": "mm",
                            "value": None,
                            "value_status": "MISSING",
                        },
                        "temperature_2m": {
                            "unit": "°C",
                            "value": 18.2,
                            "value_status": "NUMERIC",
                        },
                    },
                },
                {
                    "forecast_datetime": "2026-10-03T01:00:00Z",
                    "variables": {
                        "precipitation": {
                            "unit": "mm",
                            "value": 0.1,
                            "value_status": "NUMERIC",
                        },
                        "temperature_2m": {
                            "unit": "°C",
                            "value": 17.9,
                            "value_status": "NUMERIC",
                        },
                    },
                },
            ],
        }

    def test_contract_metadata_is_preserved(self) -> None:
        self.domain_service.get_context.return_value = self._context()

        result = self.service.get_forecast(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3),
            lat=-21.7874,
            lon=-46.5614,
            cell_selection="land",
        )

        self.assertEqual(result["contract_version"], "1.0")
        self.assertEqual(result["frequency"], "HOURLY")
        self.assertEqual(result["run"]["model"], "ecmwf_ifs025")
        self.assertEqual(result["run"]["source"], "open_meteo_single_runs")

    def test_forecast_is_preserved_in_domain_order(self) -> None:
        self.domain_service.get_context.return_value = self._context()

        result = self.service.get_forecast(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3),
            lat=-21.7874,
            lon=-46.5614,
            cell_selection="land",
        )

        self.assertEqual(
            [row["forecast_datetime"] for row in result["forecast"]],
            [
                "2026-10-03T00:00:00Z",
                "2026-10-03T01:00:00Z",
            ],
        )
        self.assertEqual(result["forecast_count"], 2)
        self.assertEqual(result["record_count"], 4)

    def test_missing_is_not_converted_to_zero(self) -> None:
        self.domain_service.get_context.return_value = self._context()

        result = self.service.get_forecast(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3),
            lat=-21.7874,
            lon=-46.5614,
            cell_selection="land",
        )

        precipitation = result["forecast"][0]["variables"]["precipitation"]

        self.assertIsNone(precipitation["value"])
        self.assertEqual(precipitation["value_status"], "MISSING")

    def test_numeric_value_and_unit_are_preserved(self) -> None:
        self.domain_service.get_context.return_value = self._context()

        result = self.service.get_forecast(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3),
            lat=-21.7874,
            lon=-46.5614,
            cell_selection="land",
        )

        temperature = result["forecast"][0]["variables"]["temperature_2m"]

        self.assertEqual(temperature["value"], 18.2)
        self.assertEqual(temperature["unit"], "°C")
        self.assertEqual(temperature["value_status"], "NUMERIC")

    def test_variable_list_is_deterministic(self) -> None:
        self.domain_service.get_context.return_value = self._context()

        result = self.service.get_forecast(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3),
            lat=-21.7874,
            lon=-46.5614,
            cell_selection="land",
        )

        self.assertEqual(
            result["variables"],
            ["precipitation", "temperature_2m"],
        )

    def test_get_forecast_for_run_uses_keyword_only_contract(self) -> None:
        self.domain_service.get_context_for_run.return_value = self._context()
        model_run = Mock()

        result = self.service.get_forecast_for_run(model_run=model_run)

        self.domain_service.get_context_for_run.assert_called_once_with(
            model_run=model_run
        )
        self.assertEqual(result["forecast_count"], 2)
        self.assertEqual(result["record_count"], 4)
