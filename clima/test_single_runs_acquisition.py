from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from clima.single_runs_acquisition import (
    MODEL,
    RAW_ROOT,
    SINGLE_RUN_URL,
    SingleRunAcquisitionError,
    acquire_and_persist_single_run,
    acquire_single_run,
    build_params,
)


class FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def minimal_success_payload():
    hourly = {
        "time": ["2026-10-03T00:00", "2026-10-03T01:00"],
        "temperature_2m": [18.7, 18.6],
    }
    return {
        "latitude": -21.75,
        "longitude": -46.5,
        "elevation": 1208.0,
        "timezone": "GMT",
        "hourly": hourly,
        "hourly_units": {
            "temperature_2m": "°C",
        },
    }


class SingleRunAcquisitionTests(SimpleTestCase):
    @override_settings(BASE_DIR=Path(".").resolve())
    def test_build_params_uses_frozen_authority_profile(self):
        params = build_params(run="2026-10-03T00:00")

        self.assertEqual(params["models"], MODEL)
        self.assertEqual(params["forecast_days"], "2")
        self.assertEqual(params["timezone"], "GMT")
        self.assertEqual(params["cell_selection"], "land")
        self.assertEqual(params["run"], "2026-10-03T00:00")
        self.assertNotIn("start_date", params)
        self.assertNotIn("end_date", params)

    @override_settings(BASE_DIR=Path(".").resolve())
    @patch("clima.single_runs_acquisition.urllib.request.urlopen")
    def test_successful_response_is_preserved_as_raw_envelope(self, mock_urlopen):
        payload = minimal_success_payload()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        mock_urlopen.return_value = FakeResponse(body)

        result = acquire_single_run(run="2026-10-03T00:00")

        self.assertEqual(result["http_status"], 200)
        self.assertTrue(result["raw_path"].startswith(RAW_ROOT.as_posix()))
        raw_path = Path(result["raw_path"])
        self.assertTrue(raw_path.exists())

        raw_bytes = raw_path.read_bytes()
        self.assertEqual(
            result["raw_sha256"],
            hashlib.sha256(raw_bytes).hexdigest(),
        )

        envelope = json.loads(raw_bytes.decode("utf-8"))
        self.assertEqual(envelope["source"], "open_meteo_single_runs")
        self.assertEqual(envelope["model"], MODEL)
        self.assertEqual(envelope["run"], "2026-10-03T00:00")
        self.assertEqual(envelope["http_status"], 200)
        self.assertEqual(envelope["payload"], payload)

        raw_path.unlink()

    @override_settings(BASE_DIR=Path(".").resolve())
    @patch("clima.single_runs_acquisition.urllib.request.urlopen")
    def test_api_error_does_not_call_persistence(self, mock_urlopen):
        class ErrorResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            status = 200

            def read(self):
                return json.dumps(
                    {"error": True, "reason": "invalid"}
                ).encode("utf-8")

        mock_urlopen.return_value = ErrorResponse()

        with self.assertRaises(SingleRunAcquisitionError):
            acquire_single_run(run="2026-10-03T00:00")

    @override_settings(BASE_DIR=Path(".").resolve())
    @patch("clima.single_runs_acquisition.persist_single_run")
    @patch("clima.single_runs_acquisition.urllib.request.urlopen")
    def test_acquisition_is_chained_to_persistence(
        self,
        mock_urlopen,
        mock_persist,
    ):
        payload = minimal_success_payload()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        mock_urlopen.return_value = FakeResponse(body)

        fake_model_run = type(
            "FakeModelRun",
            (),
            {"pk": 123, "content_sha256": "abc123"},
        )()
        mock_persist.return_value = (fake_model_run, "CREATED")

        result = acquire_and_persist_single_run(
            run="2026-10-03T00:00"
        )

        mock_persist.assert_called_once()
        self.assertEqual(result["persistence_status"], "CREATED")
        self.assertEqual(result["model_run_id"], 123)
        self.assertEqual(result["content_sha256"], "abc123")

        Path(result["raw_path"]).unlink()
