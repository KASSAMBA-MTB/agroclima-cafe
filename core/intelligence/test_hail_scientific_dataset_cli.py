import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

import importlib.util


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = PROJECT_ROOT / "tools" / "build_hail_scientific_validation_dataset.py"

SPEC = importlib.util.spec_from_file_location(
    "hail_scientific_dataset_cli",
    CLI_PATH,
)
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


class HailScientificDatasetCliTests(SimpleTestCase):
    def _record(self, case_id, label, cape):
        return {
            "case_id": case_id,
            "reference_label": label,
            "reference_source": "independent_reference",
            "reference_id": f"reference-{case_id}",
            "valid_time": "2026-10-03T12:00:00+00:00",
            "latitude": -21.7874,
            "longitude": -46.5614,
            "evaluation": {
                "axes": {
                    "instability": {
                        "evidence": {"value": cape},
                    },
                    "organization_shear": {
                        "evidence": {"value": 20.0},
                    },
                    "combined_cape_shear": {
                        "evidence": {"value": cape * 20.0},
                    },
                },
            },
            "provenance": {
                "raw_file": "research_inputs/RAW/sample.json",
                "raw_model": "ecmwf_ifs025",
                "raw_run": "2026-10-03T00:00",
                "time_match_method": "EXACT_UTC_TIMESTAMP",
                "coordinate_match_method": (
                    "EXACT_REQUEST_COORDINATES_ROUNDED_TO_4_DECIMALS"
                ),
            },
        }

    def test_json_preserva_registros_referencias_e_proveniencia(self):
        records = [
            self._record("event-1", "HAIL_CONFIRMED", 900.0),
            self._record("control-1", "CONTROL", 300.0),
        ]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"

            with (
                patch.object(
                    CLI.HailScientificDatasetBuilder,
                    "build_records",
                    return_value=(records, [], 2),
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        "build_hail_scientific_validation_dataset.py",
                        "--manifest",
                        "manifest.csv",
                        "--output",
                        str(output),
                    ],
                ),
            ):
                exit_code = CLI.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(
            report["status"],
            "DESCRIPTIVE_COMPARISON_READY",
        )
        self.assertEqual(len(report["dataset_records"]), 2)
        self.assertEqual(
            report["dataset_records"][0]["reference_source"],
            "independent_reference",
        )
        self.assertEqual(
            report["dataset_records"][0]["provenance"]["raw_file"],
            "research_inputs/RAW/sample.json",
        )
        self.assertEqual(
            report["dataset_records"][0]["provenance"]["time_match_method"],
            "EXACT_UTC_TIMESTAMP",
        )
        self.assertEqual(
            report["dataset_records"][1]["reference_label"],
            "CONTROL",
        )
        self.assertFalse(report["classification_performed"])
        self.assertFalse(report["thresholds_applied"])
        self.assertEqual(
            report["homologation_decision"],
            "NOT_EVALUATED_BY_THIS_COMPONENT",
        )