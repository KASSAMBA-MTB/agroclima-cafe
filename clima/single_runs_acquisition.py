"""
G7.5/G5 — controlled acquisition of an Open-Meteo Single Run.

This module is intentionally separate from the Django persistence contract.
It captures the exact successful API response as RAW and then delegates
canonical validation/persistence to clima.single_runs.persist_single_run().
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from clima.single_runs import MODEL, SOURCE, EXPECTED_UNITS, persist_single_run


SINGLE_RUN_URL = "https://single-runs-api.open-meteo.com/v1/forecast"

REFERENCE_LATITUDE = -21.7874
REFERENCE_LONGITUDE = -46.5614
REFERENCE_TIMEZONE = "GMT"
REFERENCE_CELL_SELECTION = "land"

FORECAST_DAYS = 2
REQUEST_TIMEOUT = 60

RAW_ROOT = Path("raw") / "single_runs"


class SingleRunAcquisitionError(RuntimeError):
    """The authority API did not return a persistable successful response."""

    code = "SINGLE_RUN_ACQUISITION_ERROR"

    def __init__(self, message: str, *, status: int | None = None, payload=None):
        self.status = status
        self.payload = payload
        super().__init__(message)


def build_params(
    *,
    run: str,
    latitude: float = REFERENCE_LATITUDE,
    longitude: float = REFERENCE_LONGITUDE,
    timezone_name: str = REFERENCE_TIMEZONE,
    cell_selection: str = REFERENCE_CELL_SELECTION,
    model: str = MODEL,
) -> dict[str, str]:
    """Build the frozen G5 authority request without date-range parameters."""
    if model != MODEL:
        raise ValueError(f"G5 authority model must be {MODEL!r}.")
    if FORECAST_DAYS != 2:
        raise RuntimeError("The G5 profile requires forecast_days=2.")

    return {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "timezone": timezone_name,
        "cell_selection": cell_selection,
        "models": model,
        "hourly": ",".join(EXPECTED_UNITS),
        "forecast_days": str(FORECAST_DAYS),
        "run": run,
    }


def _request(params: dict[str, str]) -> tuple[int, bytes]:
    query = urllib.parse.urlencode(params)
    url = f"{SINGLE_RUN_URL}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgroClimaCafe-G7.5-G5/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        raise SingleRunAcquisitionError(
            f"Single Runs returned HTTP {exc.code}.",
            status=exc.code,
            payload=payload,
        ) from exc
    except urllib.error.URLError as exc:
        raise SingleRunAcquisitionError(
            f"Single Runs request failed: {exc.reason}"
        ) from exc


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _raw_path(run: str, stamp: str) -> Path:
    normalized_run = run.replace(":", "").replace("-", "")
    return RAW_ROOT / f"single_run_{MODEL}_{normalized_run}_{stamp}.json"


def acquire_single_run(
    *,
    run: str,
    latitude: float = REFERENCE_LATITUDE,
    longitude: float = REFERENCE_LONGITUDE,
    timezone_name: str = REFERENCE_TIMEZONE,
    cell_selection: str = REFERENCE_CELL_SELECTION,
) -> dict:
    """
    Acquire one successful authority response and preserve its exact bytes.

    No database operation occurs in this function.
    """
    params = build_params(
        run=run,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
        cell_selection=cell_selection,
    )

    status, body = _request(params)

    if status != 200:
        raise SingleRunAcquisitionError(
            f"Unexpected HTTP status {status}.",
            status=status,
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SingleRunAcquisitionError(
            "Successful HTTP response is not valid JSON.",
            status=status,
        ) from exc

    if payload.get("error") is True:
        raise SingleRunAcquisitionError(
            "Successful HTTP response contains an API error.",
            status=status,
            payload=payload,
        )

    if payload.get("latitude") is None or payload.get("longitude") is None:
        raise SingleRunAcquisitionError(
            "Successful response does not contain resolved coordinates.",
            status=status,
            payload=payload,
        )

    if payload.get("hourly") is None or payload.get("hourly_units") is None:
        raise SingleRunAcquisitionError(
            "Successful response does not contain the hourly contract.",
            status=status,
            payload=payload,
        )

    acquired_at = datetime.now(timezone.utc).isoformat()
    query = urllib.parse.urlencode(params)
    envelope = {
        "source": SOURCE,
        "model": MODEL,
        "run": run,
        "request": {
            "url": SINGLE_RUN_URL,
            "params": params,
        },
        "acquired_at_utc": acquired_at,
        "http_status": status,
        "payload": payload,
    }

    raw_bytes = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    relative_path = _raw_path(run, _utc_stamp())
    absolute_path = (Path(settings.BASE_DIR) / relative_path).resolve()
    base_dir = Path(settings.BASE_DIR).resolve()

    if not absolute_path.is_relative_to(base_dir):
        raise RuntimeError("Calculated RAW path escapes settings.BASE_DIR.")

    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(raw_bytes)

    return {
        "source": SOURCE,
        "model": MODEL,
        "run": run,
        "http_status": status,
        "raw_path": relative_path.as_posix(),
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_bytes": len(raw_bytes),
        "request_url": f"{SINGLE_RUN_URL}?{query}",
        "acquired_at_utc": acquired_at,
    }


def acquire_and_persist_single_run(
    *,
    run: str,
    latitude: float = REFERENCE_LATITUDE,
    longitude: float = REFERENCE_LONGITUDE,
    timezone_name: str = REFERENCE_TIMEZONE,
    cell_selection: str = REFERENCE_CELL_SELECTION,
) -> dict:
    """
    Execute the complete controlled G5 path:
    API -> RAW -> canonical validation -> physical persistence.
    """
    acquisition = acquire_single_run(
        run=run,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
        cell_selection=cell_selection,
    )

    model_run, status = persist_single_run(
        acquisition["raw_path"],
        expected_raw_sha256=acquisition["raw_sha256"],
    )

    return {
        **acquisition,
        "persistence_status": status,
        "model_run_id": model_run.pk,
        "content_sha256": model_run.content_sha256,
    }
