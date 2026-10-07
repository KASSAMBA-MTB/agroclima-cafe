# ARQUIVO: clima/test_single_run_forecast_query_integration_G7_5_V1.py
# TIPO: código Python — substituir o teste de integração atualmente instalado.
# CORREÇÃO G7.5: o serviço preserva os tipos canônicos do domínio: datetime
# timezone-aware para datas e Decimal para coordenadas. Os testes devem comparar
# valores com os mesmos tipos, sem converter o contrato de produção para strings.
#
# NÃO altera o serviço de produção.
# NÃO altera o contrato canônico.
# NÃO altera persistência.
# Corrige somente as expectativas de tipo que permaneceram incompatíveis.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.services.single_run_forecast_query_service import (
    SingleRunForecastQueryService,
)


class SingleRunForecastQueryIntegrationTests(TestCase):
    SOURCE = "open_meteo_single_runs"
    MODEL = "ecmwf_ifs025"
    RUN_DATETIME = datetime(2026, 10, 3, tzinfo=timezone.utc)
    LAT = Decimal("-21.787400")
    LON = Decimal("-46.561400")
    CELL_SELECTION = "land"

    VARIABLES = {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "dew_point_2m": "°C",
        "precipitation": "mm",
        "wind_speed_10m": "km/h",
        "wind_direction_10m": "°",
        "pressure_msl": "hPa",
        "surface_pressure": "hPa",
        "cape": "J/kg",
        "temperature_850hPa": "°C",
        "relative_humidity_850hPa": "%",
        "geopotential_height_850hPa": "m",
        "temperature_500hPa": "°C",
        "geopotential_height_500hPa": "m",
    }

    @classmethod
    def setUpTestData(cls) -> None:
        cls.model_run = ClimateModelRun.objects.create(
            source=cls.SOURCE,
            model=cls.MODEL,
            run_datetime=cls.RUN_DATETIME,
            lat=cls.LAT,
            lon=cls.LON,
            timezone="GMT",
            cell_selection=cls.CELL_SELECTION,
            requested_lat=cls.LAT,
            requested_lon=cls.LON,
            elevation=Decimal("1196.000000"),
            raw_path="raw/single_runs/test_g7_5.json",
            raw_sha256="a" * 64,
            content_sha256="b" * 64,
            ingested_at=datetime(2026, 10, 3, 1, tzinfo=timezone.utc),
        )

        records = []
        for hour in range(48):
            forecast_datetime = cls.RUN_DATETIME + timedelta(hours=hour)

            for variable, unit in cls.VARIABLES.items():
                missing = hour == 0 and variable == "precipitation"
                records.append(
                    ClimateForecastRecord(
                        model_run=cls.model_run,
                        forecast_datetime=forecast_datetime,
                        variable=variable,
                        unit=unit,
                        value=None if missing else 1.0,
                        value_status="MISSING" if missing else "NUMERIC",
                    )
                )

        ClimateForecastRecord.objects.bulk_create(records)

    def _result(self) -> dict:
        return SingleRunForecastQueryService().get_forecast_for_run(
            model_run=self.model_run
        )

    def test_persisted_run_has_672_records(self) -> None:
        self.assertEqual(self.model_run.records.count(), 672)

    def test_operational_output_has_48_timestamps(self) -> None:
        result = self._result()
        self.assertEqual(result["forecast_count"], 48)
        self.assertEqual(result["record_count"], 672)

    def test_operational_output_has_14_canonical_variables(self) -> None:
        result = self._result()
        self.assertEqual(set(result["variables"]), set(self.VARIABLES))

    def test_every_timestamp_has_all_14_variables(self) -> None:
        result = self._result()
        self.assertEqual(len(result["forecast"]), 48)

        for row in result["forecast"]:
            self.assertEqual(
                set(row["variables"]),
                set(self.VARIABLES),
                msg=f"Timestamp incompleto: {row['forecast_datetime']}",
            )

    def test_first_precipitation_is_missing_and_not_zero(self) -> None:
        result = self._result()
        first = result["forecast"][0]
        precipitation = first["variables"]["precipitation"]

        self.assertEqual(
            first["forecast_datetime"],
            self.RUN_DATETIME,
        )
        self.assertIsNone(precipitation["value"])
        self.assertEqual(precipitation["value_status"], "MISSING")

    def test_remaining_671_records_are_numeric(self) -> None:
        result = self._result()
        numeric_records = 0

        for row in result["forecast"]:
            for item in row["variables"].values():
                if item["value_status"] == "NUMERIC":
                    numeric_records += 1
                    self.assertIsNotNone(item["value"])

        self.assertEqual(numeric_records, 671)

    def test_run_provenance_is_preserved(self) -> None:
        result = self._result()

        self.assertEqual(result["run"]["source"], self.SOURCE)
        self.assertEqual(result["run"]["model"], self.MODEL)
        self.assertEqual(
            result["run"]["run_datetime"],
            self.RUN_DATETIME,
        )
        self.assertEqual(result["run"]["lat"], self.LAT)
        self.assertEqual(result["run"]["lon"], self.LON)
        self.assertEqual(result["run"]["cell_selection"], "land")
