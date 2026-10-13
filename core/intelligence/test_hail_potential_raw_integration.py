"""Regressão reproduzível da integração MP-01.11 → MP-01.12 sobre RAW versionado.

Executar:
python manage.py test core.intelligence.test_hail_potential_raw_integration

O teste usa somente o RAW preservado no repositório. Não consulta API, ORM,
banco de dados, DashboardService ou regras operacionais.
"""

import json
from pathlib import Path

from django.test import SimpleTestCase

from core.intelligence.hail_potential_experimental_evaluator import (
    CLASSIFICATION_STATUS,
    HailPotentialExperimentalEvaluator,
)
from core.intelligence.hail_potential_service import HailPotentialService


RAW_RELATIVE_PATH = Path(
    "raw/g74_p0/hail_evidence/"
    "hail_evidence_ecmwf_ifs025_20261003T0000_20261010T202559134099Z.json"
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
EXPECTED_CLASSIFICATION = "NOT_CLASSIFIED_NO_HOMOLOGATED_THRESHOLDS"


class HailPotentialRawIntegrationTests(SimpleTestCase):
    """Confirma a integração dos componentes usando evidência RAW versionada."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.raw_path = Path(__file__).resolve().parents[2] / RAW_RELATIVE_PATH
        if not cls.raw_path.is_file():
            raise AssertionError(f"RAW de integração não encontrado: {cls.raw_path}")

        cls.raw = json.loads(cls.raw_path.read_text(encoding="utf-8"))
        cls.hourly = cls.raw["payload"]["hourly"]

    def test_raw_has_complete_and_aligned_48_hour_series(self):
        self.assertEqual(self.raw["http_status"], 200)
        self.assertEqual(self.raw["model"], "ecmwf_ifs025")
        self.assertEqual(self.raw["run"], "2026-10-03T00:00")
        self.assertEqual(len(self.hourly["time"]), 48)

        for variable in REQUIRED_VARIABLES + COMPLEMENTARY_VARIABLES:
            with self.subTest(variable=variable):
                self.assertIn(variable, self.hourly)
                self.assertEqual(len(self.hourly[variable]), 48)
                self.assertTrue(
                    all(value is not None for value in self.hourly[variable]),
                    f"RAW contém valor ausente em {variable}",
                )

    def test_all_raw_hours_flow_through_service_and_experimental_evaluator(self):
        service = HailPotentialService()
        evaluator = HailPotentialExperimentalEvaluator()
        timestamps = self.hourly["time"]

        self.assertEqual(len(timestamps), 48)

        for index, timestamp in enumerate(timestamps):
            with self.subTest(timestamp=timestamp):
                series = {
                    variable: self.hourly[variable][index]
                    for variable in REQUIRED_VARIABLES + COMPLEMENTARY_VARIABLES
                }
                context = {
                    "source": self.raw["request"]["endpoint"],
                    "model": self.raw["model"],
                    "source_run": self.raw["run"],
                    "valid_from": timestamp,
                    "valid_to": timestamp,
                    "series": series,
                }

                canonical = service.evaluate(context).as_dict()
                result = evaluator.evaluate(canonical)

                self.assertEqual(canonical["assessment_status"], "ASSESSED")
                self.assertEqual(result["classification_status"], EXPECTED_CLASSIFICATION)
                self.assertTrue(result["diagnostics_complete"])
                self.assertIsNone(result["potential_level"])
                self.assertFalse(result["operational"])
                self.assertFalse(result["homologated"])
                self.assertEqual(result["provenance"]["source_run"], self.raw["run"])
                self.assertEqual(
                    result["axes"]["thermodynamics"]["status"],
                    "AVAILABLE",
                )
                self.assertEqual(
                    set(result["axes"]["thermodynamics"]["values"]),
                    set(COMPLEMENTARY_VARIABLES),
                )

    def test_evaluator_never_assigns_a_normative_level_without_homologation(self):
        service = HailPotentialService()
        evaluator = HailPotentialExperimentalEvaluator()
        index = 0
        timestamp = self.hourly["time"][index]
        series = {
            variable: self.hourly[variable][index]
            for variable in REQUIRED_VARIABLES + COMPLEMENTARY_VARIABLES
        }
        canonical = service.evaluate({
            "source": self.raw["request"]["endpoint"],
            "model": self.raw["model"],
            "source_run": self.raw["run"],
            "valid_from": timestamp,
            "valid_to": timestamp,
            "series": series,
        }).as_dict()

        result = evaluator.evaluate(canonical)

        self.assertEqual(result["classification_status"], CLASSIFICATION_STATUS)
        self.assertIsNone(result["potential_level"])
        self.assertFalse(result["homologated"])
        self.assertFalse(result["operational"])
