import csv
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.intelligence.hail_scientific_dataset_builder import (
    HailScientificDatasetBuilder,
)
from core.intelligence.hail_scientific_validation import (
    HailScientificValidationService,
)


VARIABLES = {
    "cape": ([100.0, 250.0], "J/kg"),
    "wind_speed_925hPa": ([5.0, 6.0], "m/s"),
    "wind_direction_925hPa": ([90.0, 100.0], "°"),
    "wind_speed_500hPa": ([20.0, 22.0], "m/s"),
    "wind_direction_500hPa": ([270.0, 280.0], "°"),
    "wet_bulb_temperature_2m": ([15.0, 16.0], "°C"),
    "temperature_850hPa": ([12.0, 13.0], "°C"),
    "relative_humidity_850hPa": ([80.0, 85.0], "%"),
}


class HailScientificDatasetBuilderTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw_path = self.root / "sample_raw.json"
        self.manifest_path = self.root / "manifest.csv"
        self._write_raw()
        self.builder = HailScientificDatasetBuilder(project_root=self.root)

    def tearDown(self):
        self.temp.cleanup()

    def _write_raw(self):
        hourly = {
            "time": ["2026-10-03T12:00", "2026-10-03T13:00"],
        }
        units = {"time": "iso8601"}

        for name, (values, unit) in VARIABLES.items():
            hourly[name] = values
            units[name] = unit

        raw = {
            "protocol": "G7.4/MP-01.12-EVIDENCE",
            "model": "ecmwf_ifs025",
            "run": "2026-10-03T00:00",
            "http_status": 200,
            "request": {
                "endpoint": "https://example.invalid/forecast",
                "params": {
                    "latitude": "-21.7874",
                    "longitude": "-46.5614",
                    "timezone": "GMT",
                },
            },
            "payload": {
                "latitude": -21.75,
                "longitude": -46.5,
                "hourly": hourly,
                "hourly_units": units,
            },
        }
        self.raw_path.write_text(
            json.dumps(raw), encoding="utf-8"
        )

    def _write_manifest(self, rows):
        columns = [
            "case_id", "reference_label", "reference_source",
            "reference_id", "valid_time", "latitude", "longitude",
            "raw_file",
        ]
        with self.manifest_path.open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def _row(self, case_id, label, time):
        return {
            "case_id": case_id,
            "reference_label": label,
            "reference_source": "independent_reference",
            "reference_id": f"ref-{case_id}",
            "valid_time": time,
            "latitude": "-21.7874",
            "longitude": "-46.5614",
            "raw_file": "sample_raw.json",
        }

    def test_monta_dois_grupos_com_evidencia_raw_e_avaliador_real(self):
        self._write_manifest([
            self._row("event-1", "HAIL_CONFIRMED", "2026-10-03T12:00:00Z"),
            self._row("control-1", "CONTROL", "2026-10-03T13:00:00+00:00"),
        ])

        records, errors, received = self.builder.build_records("manifest.csv")
        report = HailScientificValidationService().build_report(records)

        self.assertEqual(received, 2)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(report["status"], "DESCRIPTIVE_COMPARISON_READY")
        self.assertEqual(report["reference_groups"]["HAIL_CONFIRMED"]["case_count"], 1)
        self.assertEqual(report["reference_groups"]["CONTROL"]["case_count"], 1)
        self.assertFalse(records[0]["evaluation"]["operational"])
        self.assertFalse(records[0]["evaluation"]["homologated"])
        self.assertEqual(
            records[0]["provenance"]["time_match_method"],
            "EXACT_UTC_TIMESTAMP",
        )

    def test_rejeita_coordenadas_diferentes_sem_fazer_associacao_espacial(self):
        row = self._row(
            "event-1", "HAIL_CONFIRMED", "2026-10-03T12:00:00Z"
        )
        row["latitude"] = "-22.0000"
        self._write_manifest([row])

        records, errors, received = self.builder.build_records("manifest.csv")

        self.assertEqual(received, 1)
        self.assertEqual(records, [])
        self.assertEqual(errors[0]["reason"], "RAW_REQUEST_COORDINATE_MISMATCH")

    def test_rejeita_horario_que_nao_existe_no_raw(self):
        self._write_manifest([
            self._row("event-1", "HAIL_CONFIRMED", "2026-10-03T14:00:00Z")
        ])

        records, errors, _ = self.builder.build_records("manifest.csv")

        self.assertEqual(records, [])
        self.assertEqual(
            errors[0]["reason"],
            "RAW_TIMESTAMP_NOT_UNIQUE_EXACT_MATCH",
        )

    def test_nao_aceita_rotulo_inventado_ou_invalido(self):
        self._write_manifest([
            self._row("event-1", "MODEL_SAYS_HAIL", "2026-10-03T12:00:00Z")
        ])

        records, errors, _ = self.builder.build_records("manifest.csv")

        self.assertEqual(records, [])
        self.assertEqual(errors[0]["reason"], "INVALID_REFERENCE_LABEL")

    def test_rejeita_unidade_incompativel(self):
        raw = json.loads(self.raw_path.read_text(encoding="utf-8"))
        raw["payload"]["hourly_units"]["cape"] = "°C"
        self.raw_path.write_text(json.dumps(raw), encoding="utf-8")

        self._write_manifest([
            self._row("event-1", "HAIL_CONFIRMED", "2026-10-03T12:00:00Z")
        ])

        records, errors, _ = self.builder.build_records("manifest.csv")

        self.assertEqual(records, [])
        self.assertEqual(errors[0]["reason"], "RAW_UNIT_MISMATCH:cape")
