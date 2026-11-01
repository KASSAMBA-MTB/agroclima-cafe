"""Independent reference and end-to-end tests for the HIToB spatial path."""

import json
import hashlib
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import geopandas as gpd
from shapely import from_wkt

from tools.validacao_espacial_hitob_corrigida_v2 import (
    decode_validate_blob,
    intersecting_municipalities,
    read_event_blob,
    write_validation_report,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "hitob_independent_reference.json"
DB_PATH = ROOT / "research_inputs" / "HIToB" / "HIToB_v1.db"
SHP_PATH = (
    ROOT / "research_inputs" / "HIToB" / "geography" / "IBGE_2024"
    / "SP" / "SP_Municipios_2024.shp"
)
FULL_REPORT = (
    ROOT / "research_outputs" / "HIToB"
    / "HIToB_VALIDACAO_ESPACIAL_CORRIGIDA_20261014_175401.txt"
)


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class IndependentSpatialE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_fixture()

    def test_real_geometry_matches_independent_gdal_fixture(self):
        expected = self.reference["sample_event_1"]
        blob = read_event_blob(DB_PATH, expected["rowid"])
        geom, status = decode_validate_blob(blob)
        independent = from_wkt(expected["wkt"])

        self.assertEqual(status, "VALID")
        self.assertEqual(geom.geom_type, expected["geometry_type"])
        self.assertEqual(tuple(geom.bounds), tuple(expected["bounds"]))
        self.assertEqual(geom.area, expected["area"])
        self.assertTrue(geom.equals_exact(independent, tolerance=0))
        self.assertEqual(len(geom.exterior.coords), len(independent.exterior.coords))

    def test_controlled_unique_multiple_and_absent_associations(self):
        for case in self.reference["controlled_association_cases"]:
            with self.subTest(case=case["case"]):
                event = from_wkt(case["event_wkt"])
                boundaries = {
                    code: from_wkt(wkt)
                    for code, wkt in case["boundaries_wkt"].items()
                }
                observed = list(intersecting_municipalities(event, boundaries))
                self.assertEqual(observed, case["expected"])

    def test_existing_full_run_matches_independent_gdal_totals(self):
        fixture = self.reference["full_reference"]
        report = FULL_REPORT.read_text(encoding="utf-8")

        def number(pattern):
            match = re.search(pattern, report)
            self.assertIsNotNone(match, f"missing report field: {pattern}")
            return int(match.group(1))

        self.assertEqual(number(r"Total storm_events: (\d+)"), fixture["storm_event_count"])
        self.assertEqual(number(r"Geometrias nulas: (\d+)"), fixture["null_geometries"])
        self.assertEqual(number(r"Geometrias inválidas/vazias: (\d+)"), fixture["invalid_geometries"])
        self.assertEqual(number(r"Geometrias fora de limites geográficos plausíveis: (\d+)"), fixture["implausible_geometries"])
        self.assertEqual(number(r"Erros de decodificação/processamento: (\d+)"), 0)
        self.assertEqual(number(r"Eventos sem associação em EPSG:4326: (\d+)"), fixture["events_unassociated"])
        self.assertEqual(number(r"Eventos associados a mais de um município em EPSG:4326: (\d+)"), fixture["events_multiple_associations"])
        self.assertEqual(number(r"Eventos com conjuntos de municípios divergentes entre CRS: (\d+)"), 0)
        for code, expected in fixture["municipality_event_association_counts"].items():
            match = re.search(rf"\({code}\): EPSG:4326=(\d+); EPSG:4674=(\d+)", report)
            self.assertIsNotNone(match, f"municipality count missing: {code}")
            self.assertEqual((int(match.group(1)), int(match.group(2))), (expected, expected))

    def test_real_read_decode_crs_spatial_check_and_report_are_reproducible(self):
        expected = self.reference["sample_event_1"]
        municipality_reference = self.reference["municipality_reference"]
        municipalities = gpd.read_file(SHP_PATH)
        municipalities["CD_MUN"] = (
            municipalities["CD_MUN"].astype(str)
            .str.replace(r"\.0$", "", regex=True).str.zfill(7)
        )
        selected = municipalities[
            municipalities["CD_MUN"].isin(municipality_reference["selected_municipality_codes"])
        ].copy()
        self.assertEqual(municipalities.crs.to_epsg(), 4674)
        selected = selected.to_crs("EPSG:4326")
        self.assertEqual(
            tuple(float(v) for v in selected.total_bounds),
            tuple(municipality_reference["selected_bounds_epsg4326"]),
        )
        boundaries = {
            str(row["CD_MUN"]): row.geometry
            for _, row in selected.iterrows()
        }

        outputs = []
        results = []
        for _ in range(2):
            blob = read_event_blob(DB_PATH, expected["rowid"])
            geom, status = decode_validate_blob(blob)
            hits = list(intersecting_municipalities(geom, boundaries))
            result = {
                "rowid": expected["rowid"],
                "input_blob_bytes": len(blob),
                "geometry_status": status,
                "geometry_type": geom.geom_type,
                "bounds": list(geom.bounds),
                "municipality_codes": hits,
                "error_count": 0,
            }
            lines = [
                "HIToB independent E2E reference case",
                f"rowid={result['rowid']}",
                f"status={result['geometry_status']}",
                f"type={result['geometry_type']}",
                f"bounds={result['bounds']}",
                f"municipalities={','.join(hits) or 'none'}",
                f"errors={result['error_count']}",
            ]
            # Exercise the production writer without creating side-effect files.
            with patch("pathlib.Path.write_text", autospec=True) as write_text:
                write_validation_report(ROOT / "sample.txt", lines)
                write_text.assert_called_once_with(
                    ROOT / "sample.txt", "\n".join(lines) + "\n", encoding="utf-8"
                )
                outputs.append(write_text.call_args.args[1].encode("utf-8"))
            results.append(result)

        self.assertEqual(results[0], results[1])
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(results[0]["geometry_status"], "VALID")
        self.assertEqual(results[0]["municipality_codes"], expected["expected_municipality_codes"])
        self.assertEqual(results[0]["error_count"], 0)

    def test_bad_blob_fails_loudly_with_header_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "Assinatura SpatiaLite inválida"):
            decode_validate_blob(b"not-a-spatialite-blob")

    def test_importing_validation_modules_has_no_execution_side_effects(self):
        command = (
            "import tools.HIToB_G27d_validacao_independente; "
            "import tools.validacao_espacial_hitob_corrigida_v2"
        )
        completed = subprocess.run(
            [sys.executable, "-c", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")

    def test_original_database_and_geographic_files_match_reference_hashes(self):
        inputs = self.reference["inputs"]
        self.assertTrue(inputs["unchanged"])
        self.assertEqual(inputs["sha256_before"], inputs["sha256_after"])
        for relative_path, expected_hash in inputs["sha256_after"].items():
            digest = hashlib.sha256()
            with (ROOT / relative_path).open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            self.assertEqual(digest.hexdigest(), expected_hash, relative_path)


if __name__ == "__main__":
    unittest.main()
