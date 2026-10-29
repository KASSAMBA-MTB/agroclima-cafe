"""MP-01.13 — Montagem reproduzivel do conjunto de validacao de granizo.

Os rotulos sao fornecidos por um manifesto de referencias independentes.
O modulo nao infere ocorrencia de granizo a partir das variaveis meteorologicas.
"""

import csv
import json
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from core.intelligence.hail_potential_experimental_evaluator import (
    HailPotentialExperimentalEvaluator,
)
from core.intelligence.hail_potential_service import HailPotentialService


REQUIRED_COLUMNS = (
    "case_id",
    "reference_label",
    "reference_source",
    "reference_id",
    "valid_time",
    "latitude",
    "longitude",
    "raw_file",
)

REQUIRED_VARIABLES = (
    "cape",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
)

COMPLEMENTARY_VARIABLES = (
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
)

EXPECTED_UNITS = {
    "cape": "J/kg",
    "wind_speed_925hPa": "m/s",
    "wind_direction_925hPa": "°",
    "wind_speed_500hPa": "m/s",
    "wind_direction_500hPa": "°",
    "wet_bulb_temperature_2m": "°C",
    "temperature_850hPa": "°C",
    "relative_humidity_850hPa": "%",
}


class DatasetBuildError(ValueError):
    """Erro identificavel na montagem de um registro."""


class HailScientificDatasetBuilder:
    """Liga referencias independentes a series RAW por tempo e ponto explicitos."""

    METHOD_VERSION = "MP-01.13.1"
    COORDINATE_DECIMALS = 4

    def __init__(self, project_root=None):
        self.project_root = Path(
            project_root or Path(__file__).resolve().parents[2]
        ).resolve()
        self.service = HailPotentialService()
        self.evaluator = HailPotentialExperimentalEvaluator()
        self._raw_cache = {}

    def build_records(self, manifest_path):
        """Retorna (registros, erros, linhas_recebidas), sem alterar os arquivos."""
        manifest = Path(manifest_path)
        if not manifest.is_absolute():
            manifest = self.project_root / manifest
        manifest = manifest.resolve()

        if not manifest.is_file():
            raise FileNotFoundError(f"MANIFEST_NOT_FOUND: {manifest}")

        records = []
        errors = []

        with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or [])
            missing = [name for name in REQUIRED_COLUMNS if name not in columns]
            if missing:
                raise DatasetBuildError(
                    "MANIFEST_COLUMNS_MISSING: " + ",".join(missing)
                )

            rows = list(reader)

        for index, row in enumerate(rows, start=2):
            try:
                records.append(self._build_record(row))
            except (DatasetBuildError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
                message = str(exc)
                errors.append({
                    "manifest_line": index,
                    "case_id": (row.get("case_id") or "").strip() or None,
                    "reason": message,
                })

        return records, errors, len(rows)

    def _build_record(self, row):
        case_id = self._required_text(row, "case_id")
        label = self._required_text(row, "reference_label")
        source = self._required_text(row, "reference_source")
        reference_id = self._required_text(row, "reference_id")
        valid_time_text = self._required_text(row, "valid_time")
        raw_file_text = self._required_text(row, "raw_file")

        if label not in {"HAIL_CONFIRMED", "CONTROL", "UNCERTAIN"}:
            raise DatasetBuildError("INVALID_REFERENCE_LABEL")

        valid_time = self._parse_aware_datetime(valid_time_text, "INVALID_VALID_TIME")
        latitude = self._parse_coordinate(row.get("latitude"), -90, 90, "INVALID_LATITUDE")
        longitude = self._parse_coordinate(row.get("longitude"), -180, 180, "INVALID_LONGITUDE")

        raw_path = Path(raw_file_text)
        if not raw_path.is_absolute():
            raw_path = self.project_root / raw_path
        raw_path = raw_path.resolve()

        try:
            raw_path.relative_to(self.project_root)
        except ValueError:
            raise DatasetBuildError("RAW_PATH_OUTSIDE_PROJECT")

        raw = self._load_raw(raw_path)
        params = raw["request"]["params"]

        if str(params.get("timezone", "")).upper() != "GMT":
            raise DatasetBuildError("RAW_TIMEZONE_NOT_GMT")

        raw_latitude = self._parse_coordinate(
            params.get("latitude"), -90, 90, "RAW_REQUEST_LATITUDE_INVALID"
        )
        raw_longitude = self._parse_coordinate(
            params.get("longitude"), -180, 180, "RAW_REQUEST_LONGITUDE_INVALID"
        )

        if round(latitude, self.COORDINATE_DECIMALS) != round(
            raw_latitude, self.COORDINATE_DECIMALS
        ) or round(longitude, self.COORDINATE_DECIMALS) != round(
            raw_longitude, self.COORDINATE_DECIMALS
        ):
            raise DatasetBuildError("RAW_REQUEST_COORDINATE_MISMATCH")

        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise DatasetBuildError("RAW_PAYLOAD_INVALID")

        hourly = payload.get("hourly")
        units = payload.get("hourly_units")
        if not isinstance(hourly, dict) or not isinstance(units, dict):
            raise DatasetBuildError("RAW_HOURLY_OR_UNITS_INVALID")

        timestamps = hourly.get("time")
        if not isinstance(timestamps, list) or not timestamps:
            raise DatasetBuildError("RAW_TIMESTAMPS_INVALID")

        matches = []
        for position, value in enumerate(timestamps):
            parsed = self._parse_raw_time(value)
            if parsed == valid_time:
                matches.append(position)

        if len(matches) != 1:
            raise DatasetBuildError(
                "RAW_TIMESTAMP_NOT_UNIQUE_EXACT_MATCH"
            )
        position = matches[0]

        series = {}
        for variable, expected_unit in EXPECTED_UNITS.items():
            values = hourly.get(variable)
            if not isinstance(values, list) or len(values) != len(timestamps):
                raise DatasetBuildError(f"RAW_SERIES_LENGTH_INVALID:{variable}")
            if units.get(variable) != expected_unit:
                raise DatasetBuildError(f"RAW_UNIT_MISMATCH:{variable}")

            value = values[position]
            if variable in REQUIRED_VARIABLES and not self._is_number(value):
                raise DatasetBuildError(f"RAW_REQUIRED_VALUE_MISSING:{variable}")

            series[variable] = value

        canonical = self.service.evaluate({
            "source": raw.get("request", {}).get("endpoint"),
            "model": raw.get("model"),
            "source_run": raw.get("run"),
            "valid_from": valid_time.isoformat(),
            "valid_to": valid_time.isoformat(),
            "series": series,
        }).as_dict()

        evaluation = self.evaluator.evaluate(canonical)
        axes = evaluation.get("axes")
        if not isinstance(axes, dict) or not axes:
            raise DatasetBuildError("EXPERIMENTAL_EVALUATION_HAS_NO_AXES")

        return {
            "case_id": case_id,
            "reference_label": label,
            "reference_source": source,
            "reference_id": reference_id,
            "valid_time": valid_time.isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "evaluation": evaluation,
            "provenance": {
                "raw_file": str(raw_path.relative_to(self.project_root)).replace("\\", "/"),
                "raw_model": raw.get("model"),
                "raw_run": raw.get("run"),
                "raw_requested_latitude": raw_latitude,
                "raw_requested_longitude": raw_longitude,
                "raw_grid_latitude": payload.get("latitude"),
                "raw_grid_longitude": payload.get("longitude"),
                "raw_timestamp": timestamps[position],
                "coordinate_match_method": "EXACT_REQUEST_COORDINATES_ROUNDED_TO_4_DECIMALS",
                "time_match_method": "EXACT_UTC_TIMESTAMP",
            },
        }

    def _load_raw(self, path):
        if path in self._raw_cache:
            return self._raw_cache[path]

        if not path.is_file():
            raise DatasetBuildError(f"RAW_FILE_NOT_FOUND:{path.name}")

        with path.open("r", encoding="utf-8-sig") as stream:
            raw = json.load(stream)

        if not isinstance(raw, dict) or raw.get("http_status") != 200:
            raise DatasetBuildError("RAW_HTTP_STATUS_NOT_200")

        request = raw.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("params"), dict):
            raise DatasetBuildError("RAW_REQUEST_METADATA_INVALID")

        self._raw_cache[path] = raw
        return raw

    @staticmethod
    def _required_text(row, field):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DatasetBuildError(f"MANIFEST_FIELD_REQUIRED:{field}")
        return value.strip()

    @staticmethod
    def _parse_aware_datetime(value, error_code):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise DatasetBuildError(error_code)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise DatasetBuildError("VALID_TIME_MUST_INCLUDE_TIMEZONE")
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _parse_raw_time(cls, value):
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _parse_coordinate(value, minimum, maximum, error_code):
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise DatasetBuildError(error_code)
        if not isfinite(number) or not minimum <= number <= maximum:
            raise DatasetBuildError(error_code)
        return number

    @staticmethod
    def _is_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(float(value))
        )
