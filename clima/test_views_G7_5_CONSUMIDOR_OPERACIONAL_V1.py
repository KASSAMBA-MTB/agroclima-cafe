# ARQUIVO: clima/test_views_G7_5_CONSUMIDOR_OPERACIONAL_V2_CORRIGIDO.py
# TIPO: código Python — substituir o teste V1 instalado.
# G7.5 — correção exclusiva do fixture de teste.
#
# Motivo da correção:
# ClimateModelRun.ingested_at é NOT NULL no contrato persistido.
# O V1 criou o RUN de teste sem esse campo, causando 7 erros no setUp.
#
# NÃO altera:
# - produção;
# - ClimateModelRun;
# - SingleRunForecastQueryService;
# - contrato canônico;
# - rota;
# - view.
#
# Correção:
# incluir ingested_at=timezone.now() na criação do ClimateModelRun.

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.views import single_run_forecast


class SingleRunForecastViewTests(TestCase):
    SOURCE = "open_meteo_single_runs"
    MODEL = "ecmwf_ifs025"
    RUN_DATETIME = datetime(
        2026,
        10,
        3,
        tzinfo=timezone.utc,
    )
    LAT = Decimal("-21.787400")
    LON = Decimal("-46.561400")
    TIMEZONE = "GMT"
    CELL_SELECTION = "land"

    def setUp(self):
        self.model_run = ClimateModelRun.objects.create(
            source=self.SOURCE,
            model=self.MODEL,
            run_datetime=self.RUN_DATETIME,
            lat=self.LAT,
            lon=self.LON,
            timezone=self.TIMEZONE,
            cell_selection=self.CELL_SELECTION,
            requested_lat=self.LAT,
            requested_lon=self.LON,
            elevation=Decimal("1196.000000"),
            raw_path="raw/test/g7_5_view.json",
            raw_sha256="a" * 64,
            content_sha256="b" * 64,
            ingested_at=datetime.now(timezone.utc),
        )

        variables = (
            ("temperature_2m", "°C", 18.7),
            ("relative_humidity_2m", "%", 80.0),
            ("dew_point_2m", "°C", 15.0),
            ("precipitation", "mm", None),
            ("wind_speed_10m", "km/h", 4.2),
            ("wind_direction_10m", "°", 120.0),
            ("pressure_msl", "hPa", 900.0),
            ("surface_pressure", "hPa", 890.0),
            ("cape", "J/kg", 10.0),
            ("temperature_850hPa", "°C", 10.0),
            ("relative_humidity_850hPa", "%", 70.0),
            ("geopotential_height_850hPa", "m", 1450.0),
            ("temperature_500hPa", "°C", -5.0),
            ("geopotential_height_500hPa", "m", 5700.0),
        )

        records = []

        for hour in range(48):
            forecast_datetime = (
                self.RUN_DATETIME
                + timedelta(hours=hour)
            )

            for variable, unit, value in variables:
                if value is None and hour == 0:
                    records.append(
                        ClimateForecastRecord(
                            model_run=self.model_run,
                            forecast_datetime=forecast_datetime,
                            variable=variable,
                            unit=unit,
                            value=None,
                            value_status="MISSING",
                        )
                    )
                else:
                    numeric_value = (
                        0.0
                        if value is None
                        else value
                    )

                    records.append(
                        ClimateForecastRecord(
                            model_run=self.model_run,
                            forecast_datetime=forecast_datetime,
                            variable=variable,
                            unit=unit,
                            value=numeric_value,
                            value_status="NUMERIC",
                        )
                    )

        ClimateForecastRecord.objects.bulk_create(records)

    def _url(self):
        return (
            "/clima/single-run/forecast/"
            "?source=open_meteo_single_runs"
            "&model=ecmwf_ifs025"
            "&run_datetime=2026-10-03T00:00:00Z"
            "&lat=-21.787400"
            "&lon=-46.561400"
            "&cell_selection=land"
        )

    def test_get_returns_operational_contract(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data["contract_version"],
            "1.0",
        )
        self.assertEqual(
            data["frequency"],
            "HOURLY",
        )
        self.assertEqual(
            data["run"]["model"],
            self.MODEL,
        )
        self.assertEqual(
            data["forecast_count"],
            48,
        )
        self.assertEqual(
            data["record_count"],
            672,
        )

    def test_first_precipitation_remains_missing(self):
        response = self.client.get(self._url())
        data = response.json()

        first = data["forecast"][0]

        precipitation = first["variables"]["precipitation"]

        self.assertIsNone(
            precipitation["value"]
        )
        self.assertEqual(
            precipitation["value_status"],
            "MISSING",
        )

    def test_missing_is_not_converted_to_zero(self):
        response = self.client.get(self._url())
        data = response.json()

        first = data["forecast"][0]

        precipitation = first["variables"]["precipitation"]

        self.assertIsNot(
            precipitation["value"],
            0,
        )

    def test_run_provenance_is_preserved(self):
        response = self.client.get(self._url())
        data = response.json()

        self.assertEqual(
            data["run"]["source"],
            self.SOURCE,
        )
        self.assertEqual(
            data["run"]["model"],
            self.MODEL,
        )
        self.assertEqual(
            data["run"]["cell_selection"],
            self.CELL_SELECTION,
        )
        self.assertEqual(
            data["run"]["lat"],
            str(self.LAT),
        )
        self.assertEqual(
            data["run"]["lon"],
            str(self.LON),
        )

    def test_unknown_run_returns_404(self):
        url = self._url().replace(
            "2026-10-03T00:00:00Z",
            "2026-10-04T00:00:00Z",
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_missing_parameter_returns_400(self):
        response = self.client.get(
            "/clima/single-run/forecast/"
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_post_is_not_allowed(self):
        response = self.client.post(
            self._url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )
