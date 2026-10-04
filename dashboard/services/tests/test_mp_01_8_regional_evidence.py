from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from core.intelligence.engine import IntelligenceEngine
from core.intelligence.rules.hydric_pressure_rule import HydricPressureRule
from dashboard.services.dashboard_service import DashboardService
from dashboard.services.hydric_balance_service import HydricBalanceService
from dashboard.services.hydric_pressure_regional_service import (
    HydricPressureRegionalService,
)
from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)


def valid_rule_result(municipality_id):
    return HydricPressureRule().evaluate(
        {
            "municipio_id": municipality_id,
            "municipio_nome": f"Município {municipality_id}",
            "analysis_date": date(2026, 10, 4),
            "hydric_balance_method": "REFERENCE_DAILY_RESERVOIR_BALANCE",
            "hydric_balance_scope": "MUNICIPAL",
            "hydric_balance_status": "VALID",
            "cad_mm": 100.0,
            "arm_final_mm": 40.0,
            "arm_final_percentual": 40.0,
            "deficit_hidrico_acumulado": 2.0,
            "excedente_hidrico_acumulado": 0.0,
        }
    )


def regional_evidence(results):
    regional = HydricPressureRegionalService().compose(results)
    return HydricPressureRegionalSynthesisService().synthesize(regional)


class RegionalEvidenceTransportTests(SimpleTestCase):
    def test_dashboard_passes_unchanged_evidence_to_intelligence_and_explainability(self):
        results = [valid_rule_result(index) for index in range(1, 5)]
        expected_evidence = regional_evidence(results)
        snapshot = deepcopy(expected_evidence)

        self.assertEqual(expected_evidence["regional_status"], "VALID")
        self.assertEqual(expected_evidence["valid_count"], 4)
        self.assertEqual(
            expected_evidence["source_rule_id"], "HYDRIC_PRESSURE_001"
        )
        self.assertNotIn("rule_id", expected_evidence)

        engine = IntelligenceEngine()
        dashboard = DashboardService.__new__(DashboardService)
        dashboard.hydric_pressure_regional_service = (
            HydricPressureRegionalService()
        )
        dashboard.hydric_pressure_regional_synthesis_service = (
            HydricPressureRegionalSynthesisService()
        )
        dashboard.frost_risk_service = SimpleNamespace(
            intelligence=engine
        )
        map_points = [
            {"id": result["municipio_id"], "rule_results": [result]}
            for result in results
        ]

        balance = HydricBalanceService()
        rule = HydricPressureRule()
        original_balance_calculate = HydricBalanceService.calculate
        original_rule_evaluate = HydricPressureRule.evaluate

        received = []
        original_explain = engine.explain_regional_evidence

        def capture_and_explain(context):
            evidence = context["hydric_pressure_regional_synthesis"]
            received.append((context, evidence, deepcopy(evidence)))
            return original_explain(context)

        with patch.object(
            HydricBalanceService,
            "calculate",
            autospec=True,
            side_effect=original_balance_calculate,
        ) as balance_spy:
            with patch.object(
                HydricPressureRule,
                "evaluate",
                autospec=True,
                side_effect=original_rule_evaluate,
            ) as rule_spy:
                # Positive controls prove both spies observe the real class
                # entry points before their counters are reset.
                balance.calculate(
                    precipitation_series=[0.0],
                    eto_series=[0.0],
                    cad_mm=100.0,
                    initial_arm_mm=40.0,
                    scope="MUNICIPAL",
                )
                rule.evaluate(
                    {
                        "hydric_balance_method": (
                            "REFERENCE_DAILY_RESERVOIR_BALANCE"
                        ),
                        "hydric_balance_scope": "MUNICIPAL",
                        "hydric_balance_status": "VALID",
                        "cad_mm": 100.0,
                        "arm_final_mm": 40.0,
                    }
                )
                self.assertEqual(balance_spy.call_count, 1)
                self.assertEqual(rule_spy.call_count, 1)
                balance_spy.reset_mock()
                rule_spy.reset_mock()

                with patch.object(
                    engine,
                    "explain_regional_evidence",
                    side_effect=capture_and_explain,
                ) as engine_spy:
                    context = dashboard._attach_hydric_pressure_context(
                        context={},
                        map_points=map_points,
                    )

                self.assertEqual(engine_spy.call_count, 1)
                self.assertEqual(balance_spy.call_count, 0)
                self.assertEqual(rule_spy.call_count, 0)

        received_context, received_evidence, received_snapshot = received[0]
        self.assertIs(received_context, context)
        self.assertEqual(received_snapshot, snapshot)
        self.assertEqual(received_evidence, snapshot)
        self.assertEqual(
            context["hydric_pressure_regional_synthesis"], snapshot
        )
        self.assertEqual(
            context["hydric_pressure_regional_explainability"][
                "regional_evidence"
            ],
            snapshot,
        )
        self.assertEqual(received_evidence, received_snapshot)
        self.assertEqual(expected_evidence, snapshot)
        self.assertEqual(snapshot["participants"][0]["analysis_date"], date(2026, 10, 4))
        self.assertEqual(
            snapshot["participants"][0]["source_rule_id"],
            "HYDRIC_PRESSURE_001",
        )
        self.assertEqual(
            snapshot["participants"][0]["provenance"]["source"],
            "HydricBalanceService",
        )
        self.assertEqual(
            snapshot["state_counts"], {"DEFICIT_OBSERVED": 4}
        )
        self.assertNotIn("hydric_states", snapshot)
        self.assertEqual(
            snapshot["source_regional_context"]["provenance"],
            expected_evidence["source_regional_context"]["provenance"],
        )

    def test_insufficient_evidence_and_absence_are_not_reinterpreted(self):
        insufficient = regional_evidence(
            [valid_rule_result(index) for index in range(1, 4)]
        )
        insufficient_snapshot = deepcopy(insufficient)
        engine = IntelligenceEngine()

        explained = engine.explain_regional_evidence(
            {"hydric_pressure_regional_synthesis": insufficient}
        )
        self.assertEqual(insufficient["regional_status"], "INSUFFICIENT_DATA")
        self.assertEqual(explained["regional_evidence"], insufficient_snapshot)
        self.assertEqual(insufficient, insufficient_snapshot)

        no_evidence = engine.explain_regional_evidence({})
        self.assertNotIn("regional_evidence", no_evidence)
