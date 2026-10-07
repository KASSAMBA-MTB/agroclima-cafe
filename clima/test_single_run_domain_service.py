"""
G7.5 / G6 — Testes do SingleRunDomainService.

Destino:
    clima/test_single_run_domain_service.py
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.services.single_run_domain_service import SingleRunDomainService


class SingleRunDomainServiceTests(TestCase):
    def setUp(self):
        self.run_datetime = datetime(2026, 10, 3, tzinfo=timezone.utc)

        self.model_run = ClimateModelRun.objects.create(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=self.run_datetime,
            lat=Decimal("-21.750000"),
            lon=Decimal("-46.500000"),
            timezone="GMT",
            cell_selection="land",
            requested_lat=Decimal("-21.787400"),
            requested_lon=Decimal("-46.561400"),
            elevation=Decimal("1208.000000"),
            raw_path="raw/single_runs/test.json",
            raw_sha256="a" * 64,
            content_sha256="b" * 64,
            ingested_at=datetime(2026, 10, 7, 12, tzinfo=timezone.utc),
        )

        ClimateForecastRecord.objects.create(
            model_run=self.model_run,
            forecast_datetime=self.run_datetime,
            variable="precipitation",
            unit="mm",
            value=None,
            value_status=ClimateForecastRecord.ValueStatus.MISSING,
        )
        ClimateForecastRecord.objects.create(
            model_run=self.model_run,
            forecast_datetime=self.run_datetime,
            variable="temperature_2m",
            unit="°C",
            value=18.7,
            value_status=ClimateForecastRecord.ValueStatus.NUMERIC,
        )
        ClimateForecastRecord.objects.create(
            model_run=self.model_run,
            forecast_datetime=self.run_datetime + timedelta(hours=1),
            variable="temperature_2m",
            unit="°C",
            value=18.8,
            value_status=ClimateForecastRecord.ValueStatus.NUMERIC,
        )
        ClimateForecastRecord.objects.create(
            model_run=self.model_run,
            forecast_datetime=self.run_datetime + timedelta(hours=1),
            variable="cape",
            unit="J/kg",
            value=100.0,
            value_status=ClimateForecastRecord.ValueStatus.NUMERIC,
        )

        self.service = SingleRunDomainService()

    def test_context_preserves_run_identity_and_provenance(self):
        context = self.service.get_context(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=self.run_datetime,
            lat=Decimal("-21.750000"),
            lon=Decimal("-46.500000"),
            cell_selection="land",
        )

        run = context["run"]
        self.assertEqual(run["source"], "open_meteo_single_runs")
        self.assertEqual(run["model"], "ecmwf_ifs025")
        self.assertEqual(run["raw_sha256"], "a" * 64)
        self.assertEqual(run["content_sha256"], "b" * 64)
        self.assertEqual(run["elevation"], Decimal("1208.000000"))

    def test_context_groups_records_by_forecast_datetime(self):
        context = self.service.get_context_for_run(model_run=self.model_run)

        self.assertEqual(context["forecast_count"], 2)
        self.assertEqual(context["record_count"], 4)
        self.assertEqual(
            [item["forecast_datetime"] for item in context["forecasts"]],
            [
                self.run_datetime,
                self.run_datetime + timedelta(hours=1),
            ],
        )

    def test_variables_keep_canonical_unit_value_and_status(self):
        context = self.service.get_context_for_run(model_run=self.model_run)

        first = context["forecasts"][0]["variables"]
        self.assertEqual(first["temperature_2m"]["unit"], "°C")
        self.assertEqual(first["temperature_2m"]["value"], 18.7)
        self.assertEqual(
            first["temperature_2m"]["value_status"],
            ClimateForecastRecord.ValueStatus.NUMERIC,
        )

    def test_missing_precipitation_is_not_converted_to_zero(self):
        context = self.service.get_context_for_run(model_run=self.model_run)

        precipitation = context["forecasts"][0]["variables"]["precipitation"]

        self.assertIsNone(precipitation["value"])
        self.assertEqual(
            precipitation["value_status"],
            ClimateForecastRecord.ValueStatus.MISSING,
        )

    def test_no_persistence_is_created_by_domain_read(self):
        before_runs = ClimateModelRun.objects.count()
        before_records = ClimateForecastRecord.objects.count()

        self.service.get_context_for_run(model_run=self.model_run)

        self.assertEqual(ClimateModelRun.objects.count(), before_runs)
        self.assertEqual(
            ClimateForecastRecord.objects.count(),
            before_records,
        )

    def test_context_has_no_derived_temperature_or_precipitation_fields(self):
        context = self.service.get_context_for_run(model_run=self.model_run)

        first = context["forecasts"][0]["variables"]
        self.assertNotIn("temperature_average", first)
        self.assertNotIn("precipitation_accumulated", first)
        self.assertNotIn("derived_value", first)
