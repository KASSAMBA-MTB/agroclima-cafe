from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TransactionTestCase

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.single_runs import (
    CanonicalizationError,
    ContractProfileMismatchError,
    ContractSerializationError,
    EXPECTED_UNITS,
    MODEL,
    SOURCE,
    SingleRunContentConflictError,
    canonical_content_payload,
    content_sha256,
    persist_single_run,
    quantize_coordinate,
    validate_profile,
)


RAW = Path("raw/g74_p0/p9_ecmwf_ifs025_20261003T0000_20261007T131010Z.json")
RUN = datetime(2026, 10, 3, tzinfo=dt_timezone.utc)


class G4ClimateSingleRunTests(TransactionTestCase):
    def persist(self, path=RAW, **kwargs):
        return persist_single_run(path, **kwargs)

    def test_raw_profile_persists_complete_672_record_run(self):
        run, result = self.persist()
        self.assertEqual(result, "CREATED")
        self.assertEqual((run.source, run.model), (SOURCE, MODEL))
        self.assertEqual(run.run_datetime, RUN)
        self.assertEqual(run.lat, Decimal("-21.750000"))
        self.assertEqual(run.lon, Decimal("-46.500000"))
        self.assertEqual(run.requested_lat, Decimal("-21.787400"))
        self.assertEqual(run.requested_lon, Decimal("-46.561400"))
        self.assertEqual((run.timezone, run.cell_selection), ("GMT", "land"))
        self.assertEqual(run.elevation, Decimal("1208.000000"))
        self.assertEqual(run.records.count(), 672)
        self.assertEqual(run.records.values("variable").distinct().count(), 14)
        self.assertEqual(run.records.order_by("forecast_datetime").first().forecast_datetime, RUN)
        self.assertEqual(
            run.records.order_by("-forecast_datetime").first().forecast_datetime,
            RUN + timedelta(hours=47),
        )

    def test_raw_traceability_and_exact_bytes_hash(self):
        run, _ = self.persist()
        raw_bytes = (Path(settings.BASE_DIR) / run.raw_path).read_bytes()
        self.assertFalse(Path(run.raw_path).is_absolute())
        self.assertEqual(run.raw_sha256, hashlib.sha256(raw_bytes).hexdigest())

    def test_expected_raw_hash_is_checked_and_missing_raw_fails(self):
        with self.assertRaisesRegex(ValueError, "RAW hash"):
            self.persist(expected_raw_sha256="0" * 64)
        with self.assertRaises(FileNotFoundError):
            self.persist(Path("raw/g74_p0/no_such_raw.json"))

    def test_model_run_and_record_identities_are_unique(self):
        run, _ = self.persist()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClimateModelRun.objects.create(
                source=run.source, model=run.model, run_datetime=run.run_datetime,
                lat=run.lat, lon=run.lon, timezone=run.timezone,
                cell_selection=run.cell_selection, requested_lat=run.requested_lat,
                requested_lon=run.requested_lon, elevation=run.elevation,
                raw_path=run.raw_path, raw_sha256=run.raw_sha256,
                content_sha256=run.content_sha256, ingested_at=run.ingested_at,
            )
        record = run.records.first()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClimateForecastRecord.objects.create(
                model_run=run, forecast_datetime=record.forecast_datetime,
                variable=record.variable, unit=record.unit, value=record.value,
                value_status=record.value_status,
            )

    def test_missing_remains_a_row_and_check_constraint_rejects_bad_pair(self):
        run, _ = self.persist()
        missing = run.records.get(variable="precipitation", forecast_datetime=RUN)
        self.assertEqual(missing.value_status, "MISSING")
        self.assertIsNone(missing.value)
        bad = ClimateForecastRecord(
            model_run=run, forecast_datetime=RUN, variable="bad_missing", unit="mm",
            value=0.0, value_status="MISSING",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            bad.save()
        for status, value in (("NUMERIC", None), ("MISSING", 1.0)):
            bad = ClimateForecastRecord(
                model_run=run, forecast_datetime=RUN, variable=f"bad_{status}_{value}",
                unit="mm", value=value, value_status=status,
            )
            with self.assertRaises(IntegrityError), transaction.atomic():
                bad.save()

    def test_nan_and_positive_negative_infinity_are_rejected_before_save(self):
        run, _ = self.persist()
        for value in (float("nan"), float("inf"), float("-inf")):
            record = ClimateForecastRecord(
                model_run=run, forecast_datetime=RUN, variable=f"bad_{value}",
                unit="mm", value=value, value_status="NUMERIC",
            )
            with self.assertRaises(ValidationError):
                record.full_clean()
            with self.assertRaises(ValidationError):
                record.save()

    def test_frozen_content_hash_payload_and_sha256(self):
        rows = [
            {"forecast_datetime": RUN, "variable": "precipitation", "unit": "mm",
             "value": None, "value_status": "MISSING"},
            {"forecast_datetime": RUN, "variable": "temperature_2m", "unit": "°C",
             "value": 18.7, "value_status": "NUMERIC"},
            {"forecast_datetime": RUN + timedelta(hours=1), "variable": "temperature_2m",
             "unit": "°C", "value": 0.1, "value_status": "NUMERIC"},
        ]
        expected = (
            "2026-10-03T00:00:00Z|precipitation|mm|MISSING|MISSING\n"
            "2026-10-03T00:00:00Z|temperature_2m|°C|18.699999999999999|NUMERIC\n"
            "2026-10-03T01:00:00Z|temperature_2m|°C|0.10000000000000001|NUMERIC\n"
        )
        self.assertEqual(canonical_content_payload(rows), expected)
        digest = "b89601633a0e9eb5df5a66602b0d9511b5c868ac9762f2eb2d1424fd8e4b16f6"
        self.assertEqual(content_sha256(rows), digest)
        self.assertEqual(content_sha256(rows[::-1]), digest)
        self.assertEqual(hashlib.sha256(expected.encode("utf-8")).hexdigest(), digest)

    def test_hash_is_order_independent_normalizes_negative_zero_and_uses_17g(self):
        rows = [{"forecast_datetime": RUN, "variable": "temperature_2m", "unit": "°C",
                 "value": -0.0, "value_status": "NUMERIC"}]
        self.assertTrue(canonical_content_payload(rows).endswith("|0|NUMERIC\n"))
        self.assertEqual(content_sha256(rows), content_sha256(rows[::-1]))
        self.assertEqual(format(18.7, ".17g"), "18.699999999999999")
        self.assertEqual(format(0.1, ".17g"), "0.10000000000000001")
        self.assertEqual(format(0.0, ".17g"), "0")

    def test_datetime_hash_normalizes_to_utc(self):
        local = datetime(2026, 10, 3, 3, tzinfo=ZoneInfo("America/Sao_Paulo"))
        rows = [{"forecast_datetime": local, "variable": "temperature_2m", "unit": "°C",
                 "value": 1.0, "value_status": "NUMERIC"}]
        self.assertTrue(canonical_content_payload(rows).startswith("2026-10-03T06:00:00Z|"))

    def test_hash_rejects_pipe_lf_and_cr_in_variable_or_unit(self):
        base = {"forecast_datetime": RUN, "variable": "temperature_2m", "unit": "°C",
                "value": 1.0, "value_status": "NUMERIC"}
        for key, invalid in (("variable", "temp|2m"), ("variable", "temp\n2m"),
                             ("unit", "m\r")):
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ContractSerializationError):
                canonical_content_payload([{**base, key: invalid}])

    def rows(self):
        return [
            {"forecast_datetime": RUN + timedelta(hours=i), "variable": variable,
             "unit": unit, "value": 1.0, "value_status": "NUMERIC"}
            for variable, unit in EXPECTED_UNITS.items() for i in range(48)
        ]

    def assert_profile_error(self, rows, subcode):
        with self.assertRaises(ContractProfileMismatchError) as caught:
            validate_profile(SOURCE, MODEL, RUN, rows)
        self.assertEqual(caught.exception.subcode, subcode)

    def test_profile_is_exact_14_by_48_grid_and_missing_counts(self):
        rows = self.rows()
        rows[0].update(value=None, value_status="MISSING")
        self.assertEqual(len(rows), 672)
        self.assertTrue(validate_profile(SOURCE, MODEL, RUN, rows))

    def test_profile_rejects_missing_or_extra_variable(self):
        self.assert_profile_error(self.rows()[:-48], "VARIABLE_SET_MISMATCH")
        rows = self.rows()
        rows[-1]["variable"] = "extra"
        self.assert_profile_error(rows, "VARIABLE_SET_MISMATCH")

    def test_profile_rejects_wrong_unit(self):
        rows = self.rows()
        rows[0]["unit"] = "m/s"
        self.assert_profile_error(rows, "UNIT_MISMATCH")

    def test_profile_rejects_short_long_duplicate_missing_shifted_and_irregular_horizon(self):
        for hours in (range(47), range(49)):
            rows = [{"forecast_datetime": RUN + timedelta(hours=i), "variable": var,
                     "unit": unit, "value": 1.0, "value_status": "NUMERIC"}
                    for var, unit in EXPECTED_UNITS.items() for i in hours]
            self.assert_profile_error(rows, "HORIZON_MISMATCH")
        for replacement in (RUN + timedelta(hours=1), RUN + timedelta(minutes=30)):
            rows = self.rows()
            for row in rows:
                if row["forecast_datetime"] == RUN:
                    row["forecast_datetime"] = replacement
            self.assert_profile_error(rows, "HORIZON_MISMATCH")
        rows = self.rows()
        temperature_rows = [row for row in rows if row["variable"] == "temperature_2m"]
        temperature_rows[0]["forecast_datetime"], temperature_rows[1]["forecast_datetime"] = (
            temperature_rows[1]["forecast_datetime"], temperature_rows[0]["forecast_datetime"]
        )
        self.assert_profile_error(rows, "HORIZON_MISMATCH")

    def test_profile_rejects_value_status_and_nonfinite_values(self):
        rows = self.rows()
        rows[0]["value_status"] = "MISSING"
        self.assert_profile_error(rows, "VALUE_STATUS_MISMATCH")
        for value in (float("nan"), float("inf"), float("-inf")):
            rows = self.rows()
            rows[0]["value"] = value
            with self.assertRaises(ValueError):
                validate_profile(SOURCE, MODEL, RUN, rows)

    def test_decimal_conversion_and_round_half_even(self):
        self.assertEqual(quantize_coordinate("1.2345675"), Decimal("1.234568"))
        self.assertEqual(quantize_coordinate("1.2345685"), Decimal("1.234568"))
        self.assertEqual(quantize_coordinate(Decimal("-21.787400")), Decimal("-21.787400"))

    def test_same_content_is_idempotent_and_original_raw_remains_linked(self):
        first, status1 = self.persist()
        second, status2 = self.persist()
        self.assertEqual((status1, status2), ("CREATED", "IDEMPOTENT"))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.raw_path, RAW.as_posix())

    def test_different_content_conflicts_and_same_raw_content_drift_is_reported(self):
        self.persist()
        raw = (Path(settings.BASE_DIR) / RAW).read_bytes()
        changed = raw.replace(b"      15.9,", b"      16.9,", 1)
        with patch.object(Path, "read_bytes", return_value=changed):
            with self.assertRaises(SingleRunContentConflictError):
                self.persist()
        with patch("clima.single_runs.content_sha256", return_value="f" * 64):
            with self.assertRaises(CanonicalizationError):
                self.persist()

    def test_raw_bytes_can_differ_when_canonical_content_matches(self):
        first, _ = self.persist()
        changed_raw = (Path(settings.BASE_DIR) / RAW).read_bytes() + b"\n"
        with patch.object(Path, "read_bytes", return_value=changed_raw):
            second, result = self.persist()
        self.assertEqual(result, "IDEMPOTENT")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.raw_path, RAW.as_posix())

    def test_identity_integrity_error_is_reloaded_after_atomic_rollback(self):
        existing, _ = self.persist()
        with patch.object(ClimateModelRun.objects, "create", side_effect=IntegrityError("raced identity")):
            found, result = self.persist()
        self.assertEqual(result, "IDEMPOTENT")
        self.assertEqual(found.pk, existing.pk)

    def test_concurrent_same_identity_creates_one_run_and_is_idempotent(self):
        barrier = Barrier(2)
        original_create = ClimateModelRun.objects.create

        def synchronized_create(*args, **kwargs):
            barrier.wait(timeout=10)
            return original_create(*args, **kwargs)

        def persist_in_thread():
            close_old_connections()
            try:
                _, status = self.persist()
                return status
            finally:
                close_old_connections()

        with patch.object(ClimateModelRun.objects, "create", side_effect=synchronized_create):
            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = list(executor.map(lambda _: persist_in_thread(), range(2)))
        self.assertEqual(sorted(statuses), ["CREATED", "IDEMPOTENT"])
        self.assertEqual(ClimateModelRun.objects.count(), 1)
        self.assertEqual(ClimateForecastRecord.objects.count(), 672)

    def test_unrelated_integrity_error_propagates_and_atomicity_rolls_back(self):
        with patch.object(ClimateForecastRecord.objects, "bulk_create", side_effect=IntegrityError("other")):
            with self.assertRaises(IntegrityError):
                self.persist()
        self.assertEqual(ClimateModelRun.objects.count(), 0)
        with patch.object(ClimateForecastRecord.objects, "bulk_create", side_effect=RuntimeError("fail")):
            with self.assertRaises(RuntimeError):
                self.persist()
        self.assertEqual(ClimateModelRun.objects.count(), 0)
        self.assertEqual(ClimateForecastRecord.objects.count(), 0)

    def test_use_tz_constraints_and_foreign_key_index_configuration(self):
        self.assertTrue(settings.USE_TZ)
        self.assertIn("climate_model_run_identity_uniq", {c.name for c in ClimateModelRun._meta.constraints})
        self.assertIn("climate_forecast_record_identity_uniq", {c.name for c in ClimateForecastRecord._meta.constraints})
        self.assertIn("climate_forecast_record_value_status_check", {c.name for c in ClimateForecastRecord._meta.constraints})
        self.assertFalse(ClimateForecastRecord._meta.get_field("model_run").db_index)
