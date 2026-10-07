"""
G7.5 / G6 — testes do contrato de leitura Single Runs.

Arquivo entregue em TXT.
Destino no projeto:
    clima/test_single_run_read_service.py

Os testes assumem que os testes G4 já disponibilizam os modelos e que a
persistência pode ser criada diretamente para validar somente a leitura.
Nenhuma API externa é chamada.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.services.single_run_read_service import SingleRunReadService


class SingleRunReadServiceTests(TestCase):
    def setUp(self):
        self.service = SingleRunReadService()

        self.run = ClimateModelRun.objects.create(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 3, tzinfo=timezone.utc),
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

        base = self.run.run_datetime

        ClimateForecastRecord.objects.create(
            model_run=self.run,
            forecast_datetime=base,
            variable="precipitation",
            unit="mm",
            value=None,
            value_status=ClimateForecastRecord.ValueStatus.MISSING,
        )

        ClimateForecastRecord.objects.create(
            model_run=self.run,
            forecast_datetime=base,
            variable="temperature_2m",
            unit="°C",
            value=18.7,
            value_status=ClimateForecastRecord.ValueStatus.NUMERIC,
        )

        ClimateForecastRecord.objects.create(
            model_run=self.run,
            forecast_datetime=base + timedelta(hours=1),
            variable="temperature_2m",
            unit="°C",
            value=18.8,
            value_status=ClimateForecastRecord.ValueStatus.NUMERIC,
        )

    def test_get_run_uses_full_canonical_identity(self):
        result = self.service.get_run(
            source=self.run.source,
            model=self.run.model,
            run_datetime=self.run.run_datetime,
            lat=self.run.lat,
            lon=self.run.lon,
            cell_selection=self.run.cell_selection,
        )

        self.assertEqual(result.pk, self.run.pk)

    def test_list_runs_is_deterministically_ordered(self):
        older = ClimateModelRun.objects.create(
            source="open_meteo_single_runs",
            model="ecmwf_ifs025",
            run_datetime=datetime(2026, 10, 2, tzinfo=timezone.utc),
            lat=Decimal("-21.750000"),
            lon=Decimal("-46.500000"),
            timezone="GMT",
            cell_selection="land",
            requested_lat=Decimal("-21.787400"),
            requested_lon=Decimal("-46.561400"),
            elevation=Decimal("1208.000000"),
            raw_path="raw/single_runs/test2.json",
            raw_sha256="c" * 64,
            content_sha256="d" * 64,
            ingested_at=datetime(2026, 10, 7, 12, tzinfo=timezone.utc),
        )

        runs = list(
            self.service.list_runs(
                source="open_meteo_single_runs",
                model="ecmwf_ifs025",
            )
        )

        self.assertEqual([r.pk for r in runs], [self.run.pk, older.pk])

    def test_get_records_preserves_missing(self):
        records = list(self.service.get_records(model_run=self.run))

        self.assertEqual(len(records), 3)

        precipitation = next(
            record for record in records
            if record.variable == "precipitation"
        )

        self.assertEqual(
            precipitation.value_status,
            ClimateForecastRecord.ValueStatus.MISSING,
        )
        self.assertIsNone(precipitation.value)

    def test_get_records_can_filter_variable(self):
        records = list(
            self.service.get_records(
                model_run=self.run,
                variable="temperature_2m",
            )
        )

        self.assertEqual(len(records), 2)
        self.assertTrue(
            all(record.variable == "temperature_2m" for record in records)
        )

    def test_get_record_uses_record_identity(self):
        record = self.service.get_record(
            model_run=self.run,
            forecast_datetime=self.run.run_datetime,
            variable="temperature_2m",
        )

        self.assertEqual(record.value, 18.7)
        self.assertEqual(record.unit, "°C")
        self.assertEqual(
            record.value_status,
            ClimateForecastRecord.ValueStatus.NUMERIC,
        )

    def test_get_run_contract_contains_persisted_values_without_recalculation(self):
        contract = self.service.get_run_contract(model_run=self.run)

        self.assertEqual(contract["source"], "open_meteo_single_runs")
        self.assertEqual(contract["model"], "ecmwf_ifs025")
        self.assertEqual(contract["content_sha256"], "b" * 64)
        self.assertEqual(len(contract["records"]), 3)

        precipitation = next(
            item
            for item in contract["records"]
            if item["variable"] == "precipitation"
        )

        self.assertEqual(precipitation["value_status"], "MISSING")
        self.assertIsNone(precipitation["value"])

    def test_read_service_does_not_create_additional_records(self):
        before_runs = ClimateModelRun.objects.count()
        before_records = ClimateForecastRecord.objects.count()

        list(self.service.list_runs())
        list(self.service.get_records(model_run=self.run))
        self.service.get_run_contract(model_run=self.run)

        self.assertEqual(ClimateModelRun.objects.count(), before_runs)
        self.assertEqual(ClimateForecastRecord.objects.count(), before_records)
