"""Controlled physical persistence for the fixed G4 Single Runs profile."""

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from clima.models import ClimateForecastRecord, ClimateModelRun


SOURCE = "open_meteo_single_runs"
MODEL = "ecmwf_ifs025"
EXPECTED_UNITS = {
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


class ContractProfileMismatchError(ValueError):
    code = "CONTRACT_PROFILE_MISMATCH"

    def __init__(self, subcode, message):
        self.subcode = subcode
        super().__init__(f"{self.code}: {subcode}: {message}")


class ContractSerializationError(ValueError):
    code = "CONTRACT_SERIALIZATION_ERROR"


class SingleRunContentConflictError(ValueError):
    code = "SINGLE_RUN_CONTENT_CONFLICT"


class CanonicalizationError(ValueError):
    code = "CANONICALIZATION_ERROR"


def quantize_coordinate(value):
    """Quantize a textual/Decimal coordinate without a float round trip."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    return decimal_value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)


def _utc_datetime(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must be timezone-aware.")
    return value.astimezone(datetime_timezone.utc)


def _format_datetime(value):
    return _utc_datetime(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_value(value):
    if not math.isfinite(value):
        raise ValueError("Numeric values must be finite.")
    if value == 0:
        value = 0.0
    return format(value, ".17g")


def canonical_content_payload(records):
    rows = []
    for record in records:
        variable, unit = record["variable"], record["unit"]
        if any(char in variable or char in unit for char in ("|", "\n", "\r")):
            raise ContractSerializationError(
                "variable and unit cannot contain pipe, LF, or CR."
            )
        status = record["value_status"]
        if status == "MISSING":
            if record.get("value") is not None:
                raise ValueError("MISSING records require value=None.")
            value_text = "MISSING"
        elif status == "NUMERIC":
            value = record.get("value")
            if value is None:
                raise ValueError("NUMERIC records require a value.")
            value_text = _format_value(value)
        else:
            raise ValueError(f"Unsupported value_status: {status}")
        rows.append((
            _utc_datetime(record["forecast_datetime"]), variable,
            f"{_format_datetime(record['forecast_datetime'])}|{variable}|{unit}|{value_text}|{status}",
        ))
    rows.sort(key=lambda row: (row[0], row[1]))
    return "".join(row[2] + "\n" for row in rows)


def content_sha256(records):
    return hashlib.sha256(canonical_content_payload(records).encode("utf-8")).hexdigest()


def validate_profile(source, model, run_datetime, records):
    if source != SOURCE or model != MODEL:
        raise ContractProfileMismatchError("SOURCE_MODEL_MISMATCH", "Unexpected source/model.")

    variables = {record["variable"] for record in records}
    expected_variables = set(EXPECTED_UNITS)
    if variables != expected_variables:
        raise ContractProfileMismatchError(
            "VARIABLE_SET_MISMATCH",
            f"missing={sorted(expected_variables - variables)}, extra={sorted(variables - expected_variables)}",
        )

    for record in records:
        expected_unit = EXPECTED_UNITS[record["variable"]]
        if record["unit"] != expected_unit:
            raise ContractProfileMismatchError(
                "UNIT_MISMATCH",
                f"{record['variable']}: expected {expected_unit!r}, got {record['unit']!r}",
            )

    expected_times = [
        _utc_datetime(run_datetime) + timedelta(hours=hour) for hour in range(48)
    ]
    timestamps = {_utc_datetime(record["forecast_datetime"]) for record in records}
    if len(timestamps) != 48 or sorted(timestamps) != expected_times:
        raise ContractProfileMismatchError(
            "HORIZON_MISMATCH", "Expected 48 unique hourly timestamps from run_datetime through +47h."
        )

    if len(records) != 14 * 48:
        raise ContractProfileMismatchError("HORIZON_MISMATCH", "Expected exactly 672 records.")

    seen = set()
    by_variable = {variable: [] for variable in expected_variables}
    for record in records:
        stamp = _utc_datetime(record["forecast_datetime"])
        key = (stamp, record["variable"])
        if key in seen:
            raise ContractProfileMismatchError("HORIZON_MISMATCH", "Duplicate timestamp/variable row.")
        seen.add(key)
        by_variable[record["variable"]].append(stamp)
        status, value = record.get("value_status"), record.get("value")
        if (status == "MISSING" and value is not None) or (status == "NUMERIC" and value is None):
            raise ContractProfileMismatchError("VALUE_STATUS_MISMATCH", "value and value_status disagree.")
        if status not in ("MISSING", "NUMERIC"):
            raise ContractProfileMismatchError("VALUE_STATUS_MISMATCH", "Unknown value_status.")
        if status == "NUMERIC" and not math.isfinite(value):
            raise ValueError("NaN and infinite values cannot be persisted.")
    if any(sequence != expected_times for sequence in by_variable.values()):
        raise ContractProfileMismatchError(
            "HORIZON_MISMATCH", "Each variable must follow the ordered hourly sequence."
        )
    return True


def _parse_raw(raw_bytes):
    envelope = json.loads(raw_bytes, parse_float=Decimal, parse_int=Decimal)
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or not isinstance(envelope.get("request"), dict):
        raise ValueError("RAW must be a successful G7.4/P9 response envelope.")
    params = envelope["request"].get("params", {})
    model = envelope.get("model")
    timezone_name = payload["timezone"]
    source_timezone = ZoneInfo(timezone_name)
    run_text = params.get("run") or envelope.get("run")
    run_datetime = datetime.fromisoformat(run_text.replace("Z", "+00:00"))
    if run_datetime.tzinfo is None:
        run_datetime = run_datetime.replace(tzinfo=source_timezone)
    run_datetime = _utc_datetime(run_datetime)
    source = SOURCE
    requested_lat = quantize_coordinate(params["latitude"])
    requested_lon = quantize_coordinate(params["longitude"])
    lat = quantize_coordinate(payload["latitude"])
    lon = quantize_coordinate(payload["longitude"])
    raw_records = []
    hourly = payload["hourly"]
    units = payload["hourly_units"]
    times = hourly["time"]
    for variable, unit in EXPECTED_UNITS.items():
        values = hourly[variable]
        if len(values) != len(times):
            raise ContractProfileMismatchError("HORIZON_MISMATCH", f"{variable} has a different length.")
        for stamp, value in zip(times, values):
            forecast_datetime = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if forecast_datetime.tzinfo is None:
                forecast_datetime = forecast_datetime.replace(tzinfo=source_timezone)
            raw_records.append({
                "forecast_datetime": _utc_datetime(forecast_datetime),
                "variable": variable,
                "unit": units[variable],
                "value": None if value is None else float(value),
                "value_status": "MISSING" if value is None else "NUMERIC",
            })
    validate_profile(source, model, run_datetime, raw_records)
    return {
        "source": source,
        "model": model,
        "run_datetime": run_datetime,
        "lat": lat,
        "lon": lon,
        "timezone": timezone_name,
        "cell_selection": params["cell_selection"],
        "requested_lat": requested_lat,
        "requested_lon": requested_lon,
        "elevation": payload["elevation"],
        "records": raw_records,
    }


def persist_single_run(raw_path, *, expected_raw_sha256=None):
    """Validate and atomically persist one already captured authority RAW."""
    base_dir = Path(settings.BASE_DIR).resolve()
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError("raw_path must be relative to settings.BASE_DIR.")
    resolved = (base_dir / path).resolve()
    if not resolved.is_relative_to(base_dir):
        raise ValueError("raw_path must resolve within settings.BASE_DIR.")
    raw_bytes = resolved.read_bytes()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    if expected_raw_sha256 is not None and raw_hash != expected_raw_sha256:
        raise ValueError("RAW hash does not match expected_raw_sha256.")
    parsed = _parse_raw(raw_bytes)
    parsed["records"].sort(key=lambda row: (row["forecast_datetime"], row["variable"]))
    canonical_hash = content_sha256(parsed["records"])
    identity = {key: parsed[key] for key in (
        "source", "model", "run_datetime", "lat", "lon", "cell_selection"
    )}
    try:
        with transaction.atomic():
            model_run = ClimateModelRun.objects.create(
                **identity,
                timezone=parsed["timezone"],
                requested_lat=parsed["requested_lat"],
                requested_lon=parsed["requested_lon"],
                elevation=parsed["elevation"],
                raw_path=path.as_posix(),
                raw_sha256=raw_hash,
                content_sha256=canonical_hash,
                ingested_at=timezone.now(),
            )
            ClimateForecastRecord.objects.bulk_create([
                ClimateForecastRecord(model_run=model_run, **record)
                for record in parsed["records"]
            ])
        return model_run, "CREATED"
    except IntegrityError:
        # Query only after the failed atomic block has rolled back.
        with transaction.atomic():
            existing = ClimateModelRun.objects.filter(**identity).first()
            if existing is None:
                raise
            if existing.content_sha256 == canonical_hash:
                return existing, "IDEMPOTENT"
            if existing.raw_sha256 == raw_hash:
                raise CanonicalizationError("Same RAW produced different canonical content.")
            raise SingleRunContentConflictError("Identity already exists with different content.")
