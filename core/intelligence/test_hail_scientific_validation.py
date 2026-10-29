from copy import deepcopy

from django.test import SimpleTestCase

from core.intelligence.hail_scientific_validation import (
    HailScientificValidationService,
)


class HailScientificValidationServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = HailScientificValidationService()

    def make_record(self, case_id, label, cape, shear, cape_shear):
        return {
            "case_id": case_id,
            "reference_label": label,
            "reference_source": "independent_reference",
            "reference_id": f"ref-{case_id}",
            "valid_time": "2026-10-01T12:00:00Z",
            "latitude": -21.9,
            "longitude": -46.6,
            "evaluation": {
                "evaluation_status": "EXPERIMENTAL_NOT_HOMOLOGATED",
                "potential_level": None,
                "axes": {
                    "instability": {
                        "evidence": {"value": cape},
                    },
                    "organization_shear": {
                        "evidence": {"value": shear},
                    },
                    "combined_cape_shear": {
                        "evidence": {"value": cape_shear},
                    },
                },
            },
        }

    def test_compara_descritivamente_eventos_e_controles(self):
        records = [
            self.make_record("event-1", "HAIL_CONFIRMED", 900, 20, 18000),
            self.make_record("event-2", "HAIL_CONFIRMED", 1100, 30, 33000),
            self.make_record("control-1", "CONTROL", 300, 8, 2400),
        ]

        report = self.service.build_report(records)

        self.assertEqual(report["status"], "DESCRIPTIVE_COMPARISON_READY")
        self.assertFalse(report["classification_performed"])
        self.assertFalse(report["thresholds_applied"])
        self.assertEqual(report["homologation_decision"], "NOT_EVALUATED_BY_THIS_COMPONENT")
        self.assertEqual(report["reference_groups"]["HAIL_CONFIRMED"]["case_count"], 2)
        self.assertEqual(
            report["reference_groups"]["HAIL_CONFIRMED"]["variables"]["instability"]["mean"],
            1000,
        )
        self.assertEqual(report["reference_groups"]["CONTROL"]["case_count"], 1)

    def test_valores_ausentes_nao_viram_zero(self):
        record = self.make_record("event-1", "HAIL_CONFIRMED", None, 20, None)
        report = self.service.build_report([record])

        variable = report["reference_groups"]["HAIL_CONFIRMED"]["variables"]["instability"]
        self.assertIsNone(variable["mean"])
        self.assertEqual(variable["available_count"], 0)
        self.assertEqual(variable["missing_count"], 1)

    def test_eventos_incerto_sao_excluidos_da_comparacao(self):
        records = [
            self.make_record("event-1", "HAIL_CONFIRMED", 900, 20, 18000),
            self.make_record("control-1", "CONTROL", 300, 8, 2400),
            self.make_record("uncertain-1", "UNCERTAIN", 700, 12, 8400),
        ]

        report = self.service.build_report(records)

        self.assertEqual(report["uncertain_records_excluded_from_comparison"], 1)
        self.assertEqual(report["records_accepted"], 3)
        self.assertEqual(report["reference_groups"]["HAIL_CONFIRMED"]["case_count"], 1)
        self.assertEqual(report["reference_groups"]["CONTROL"]["case_count"], 1)

    def test_registro_invalido_e_id_duplicado_sao_reportados(self):
        valid = self.make_record("same-id", "HAIL_CONFIRMED", 900, 20, 18000)
        duplicate = deepcopy(valid)
        report = self.service.build_report([valid, duplicate, {"case_id": ""}])

        self.assertEqual(report["status"], "DATA_QUALITY_REVIEW_REQUIRED")
        self.assertEqual(report["records_accepted"], 1)
        self.assertEqual(report["records_rejected"], 2)
        self.assertEqual(report["errors"][0]["reason"], "DUPLICATE_CASE_ID")

    def test_sem_dois_grupos_nao_declara_comparacao_pronta(self):
        record = self.make_record("event-1", "HAIL_CONFIRMED", 900, 20, 18000)
        report = self.service.build_report([record])

        self.assertEqual(report["status"], "INSUFFICIENT_REFERENCE_GROUPS")
        self.assertEqual(report["homologation_decision"], "NOT_EVALUATED_BY_THIS_COMPONENT")
