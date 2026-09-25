"""
MP-01.5 — Pressão Hídrica Agroclimática

Testa a transformação do balanço hídrico canônico em interpretação,
sem criação de score ou limiar agronômico adicional.
"""

from datetime import datetime

from django.test import SimpleTestCase

from core.intelligence.engine import IntelligenceEngine
from core.intelligence.rules.hydric_pressure_rule import HydricPressureRule


def valid_context(**overrides):
    context = {
        "hydric_balance_version": "1.0.0",
        "hydric_balance_method": "REFERENCE_DAILY_RESERVOIR_BALANCE",
        "hydric_balance_status": "VALID",
        "hydric_balance_scope": "MUNICIPAL",
        "cad_mm": 100.0,
        "arm_final_mm": 72.0,
        "arm_final_percentual": 72.0,
        "deficit_hidrico_acumulado": 0.0,
        "excedente_hidrico_acumulado": 0.0,
        "municipio_id": 1,
        "municipio_nome": "Poços de Caldas",
        "analysis_date": datetime(2026, 9, 25, 12, 0, 0),
    }
    context.update(overrides)
    return context


class HydricPressureRuleTests(SimpleTestCase):

    def setUp(self):
        self.rule = HydricPressureRule()

    def test_01_sem_deficit_observado(self):
        result = self.rule.evaluate(valid_context())

        self.assertIsNotNone(result)
        self.assertEqual(result["hydric_state"], "NO_DEFICIT_OBSERVED")
        self.assertEqual(result["pressure_status"], "NOT_OBSERVED")
        self.assertIsNone(result.get("score"))
        self.assertNotIn("severity", result)

    def test_02_deficit_observado(self):
        result = self.rule.evaluate(
            valid_context(
                arm_final_mm=38.0,
                arm_final_percentual=38.0,
                deficit_hidrico_acumulado=12.4,
            )
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["hydric_state"], "DEFICIT_OBSERVED")
        self.assertEqual(result["pressure_status"], "OBSERVED")
        self.assertEqual(result["deficit_hidrico_mm"], 12.4)
        self.assertIsNone(result.get("score"))
        self.assertNotIn("severity", result)

    def test_03_excedente_observado(self):
        result = self.rule.evaluate(
            valid_context(
                arm_final_mm=100.0,
                arm_final_percentual=100.0,
                excedente_hidrico_acumulado=18.7,
            )
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["hydric_state"], "EXCESS_OBSERVED")
        self.assertEqual(result["pressure_status"], "NOT_OBSERVED")
        self.assertEqual(result["excedente_hidrico_mm"], 18.7)

    def test_04_dados_insuficientes_nao_gera_interpretacao(self):
        result = self.rule.evaluate(
            valid_context(
                hydric_balance_status="INSUFFICIENT_DATA",
                arm_final_mm=None,
                arm_final_percentual=None,
                deficit_hidrico_acumulado=None,
                excedente_hidrico_acumulado=None,
            )
        )

        self.assertIsNone(result)

    def test_05_metodo_incompativel_nao_gera_interpretacao(self):
        result = self.rule.evaluate(
            valid_context(hydric_balance_method="OUTRO_METODO")
        )

        self.assertIsNone(result)

    def test_06_engine_registra_a_nova_regra(self):
        engine = IntelligenceEngine()
        rule_ids = [
            getattr(rule, "id", getattr(rule, "ID", None))
            for rule in engine.rule_engine.rules
        ]

        self.assertEqual(
            rule_ids,
            [
                "FROST_001",
                "METEO_ALERT_001",
                "HYDRIC_PRESSURE_001",
            ],
        )

    def test_07_engine_preserva_regra_hidrica_fora_do_insight(self):
        engine = IntelligenceEngine()

        result = engine.process(
            valid_context(
                municipio_id=99,
                municipio_nome="Poços de Caldas",
                arm_final_mm=35.0,
                arm_final_percentual=35.0,
                deficit_hidrico_acumulado=9.5,
            )
        )

        hydric = next(
            item
            for item in result["coordinated_results"]
            if item.get("rule_id") == "HYDRIC_PRESSURE_001"
        )

        self.assertEqual(hydric["hydric_state"], "DEFICIT_OBSERVED")
        self.assertNotIn(
            "HYDRIC_PRESSURE_001",
            [item.get("id") for item in result["insights"]],
        )
