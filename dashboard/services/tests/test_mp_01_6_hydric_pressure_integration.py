from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from clima.models import HistoricalWeatherDaily, WeatherStation
from clima.services.history_service import HistoryService
from core.intelligence.engine import IntelligenceEngine
from dashboard.services.agroclimate_indicator_service import (
    AgroClimateIndicatorService,
)
from dashboard.services.dashboard_service import DashboardService
from dashboard.services.hydric_balance_service import HydricBalanceService
from dashboard.services.frost_risk_service import FrostRiskService
from dashboard.services.historical_climate_indicator_service import (
    HistoricalClimateIndicatorService,
)
from dashboard.services.map_service import MapService
from dashboard.services.hydric_pressure_regional_service import (
    HydricPressureRegionalService,
)
from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)
from dashboard.services.thermal_classification_service import (
    ThermalClassificationService,
)
from municipios.models import Municipio


class HydricPressureRegionalIntegrationTests(TestCase):
    def setUp(self):
        self.reference_date = timezone.localdate()
        self.municipios = []

        for index in range(1, 6):
            municipio = Municipio.objects.create(
                nome=f"Município {index}",
                estado="SP",
                latitude=-21.0 - index / 100,
                longitude=-46.0 - index / 100,
                altitude=900,
            )
            station = WeatherStation.objects.create(municipio=municipio)

            for day in (
                self.reference_date - timedelta(days=1),
                self.reference_date,
            ):
                HistoricalWeatherDaily.objects.create(
                    station=station,
                    data=day,
                    temperatura_media=20.0,
                    temperatura_minima=10.0,
                    temperatura_maxima=30.0,
                    precipitacao=0.0,
                    eto_mm_day=None if index == 5 else 15.0,
                )

            self.municipios.append(municipio)

    def test_dashboard_chain_reaches_explainability_without_recalculation(self):
        dashboard = DashboardService.__new__(DashboardService)
        dashboard.kpi_service = SimpleNamespace(
            get_kpis=lambda canonical_context: {
                "municipio_id": self.municipios[0].pk,
                "municipio_nome": self.municipios[0].nome,
            }
        )
        dashboard.chart_service = SimpleNamespace(
            get_chart=lambda: {},
            get_chart_periods=lambda current_kpis: {},
        )
        dashboard.events_service = SimpleNamespace(get_events=lambda: [])
        dashboard.map_service = MapService()
        dashboard.ranking_service = SimpleNamespace(get_ranking=lambda points: [])
        dashboard.weather_service = None
        dashboard.frost_risk_service = FrostRiskService()
        dashboard.thermal_classification_service = ThermalClassificationService()
        dashboard.agroclimate_indicator_service = AgroClimateIndicatorService()
        dashboard.history_service = HistoryService()
        dashboard.historical_climate_indicator_service = (
            HistoricalClimateIndicatorService()
        )
        dashboard.hydric_pressure_regional_service = (
            HydricPressureRegionalService()
        )
        dashboard.hydric_pressure_regional_synthesis_service = (
            HydricPressureRegionalSynthesisService()
        )
        dashboard._current_weather_dtos = {}
        dashboard._refresh_current_weather = lambda: {}
        dashboard._build_canonical_weather_context = lambda: {}

        hydric_config = {
            str(municipio.pk): {
                "cad_mm": 100.0,
                "cad_provenance": {"source": "integration-test-input"},
                "initial_arm_mm": 20.0,
                "initial_arm_method": "EXPLICIT",
            }
            for municipio in self.municipios
        }

        intelligence = dashboard.frost_risk_service.intelligence
        original_process = intelligence.process
        original_explain = intelligence.explain_regional_evidence
        original_balance_calculate = HydricBalanceService.calculate

        with override_settings(AGROCLIMA_HYDRIC_BALANCE_CONFIG=hydric_config):
            with patch.object(
                HydricBalanceService,
                "calculate",
                autospec=True,
                side_effect=original_balance_calculate,
            ) as balance_calculate:
                with patch.object(
                    intelligence,
                    "process",
                    side_effect=original_process,
                ) as process:
                    with patch.object(
                        intelligence,
                        "explain_regional_evidence",
                        side_effect=original_explain,
                    ) as explain_regional:
                        context = dashboard.get_dashboard()

        self.assertEqual(balance_calculate.call_count, 5)
        self.assertEqual(process.call_count, 5)
        self.assertEqual(explain_regional.call_count, 1)

        regional = context["hydric_pressure_regional"]
        synthesis = context["hydric_pressure_regional_synthesis"]
        self.assertEqual(regional["regional_status"], "VALID")
        self.assertEqual(regional["valid_count"], 4)
        self.assertEqual(
            [item["municipio_id"] for item in regional["municipalities"]],
            [municipio.pk for municipio in self.municipios[:4]],
        )

        for item in regional["municipalities"]:
            self.assertEqual(item["rule_id"], "HYDRIC_PRESSURE_001")
            self.assertEqual(item["hydric_state"], "DEFICIT_OBSERVED")
            self.assertEqual(item["analysis_date"], self.reference_date)
            self.assertEqual(item["arm_final_mm"], 0.0)
            self.assertEqual(item["deficit_hidrico_mm"], 10.0)
            self.assertEqual(
                item["provenance"]["source"], "HydricBalanceService"
            )

        self.assertEqual(synthesis["regional_status"], "VALID")
        self.assertEqual(synthesis["state_counts"], {"DEFICIT_OBSERVED": 4})
        self.assertEqual(synthesis["source_rule_id"], "HYDRIC_PRESSURE_001")
        self.assertEqual(
            [item["municipio_id"] for item in synthesis["participants"]],
            [municipio.pk for municipio in self.municipios[:4]],
        )
        self.assertNotIn("regional_state", synthesis)

        explainability = context["hydric_pressure_regional_explainability"]
        self.assertIs(explainability["regional_evidence"], synthesis)
        self.assertIs(
            explain_regional.call_args.args[0][
                "hydric_pressure_regional_synthesis"
            ],
            synthesis,
        )

        municipal_rule_results = [
            result
            for point in context["map_points"]
            for result in point["rule_results"]
            if result.get("rule_id") == "HYDRIC_PRESSURE_001"
        ]
        self.assertEqual(len(municipal_rule_results), 4)
        self.assertEqual(
            [item["municipio_id"] for item in municipal_rule_results],
            [municipio.pk for municipio in self.municipios[:4]],
        )

        missing_data_point = next(
            point
            for point in context["map_points"]
            if point["id"] == self.municipios[4].pk
        )
        self.assertEqual(
            missing_data_point["historical_indicators"]["eto_mm_day"],
            [None, None],
        )
        self.assertEqual(
            missing_data_point["historical_indicators"][
                "hydric_balance_status"
            ],
            "INSUFFICIENT_DATA",
        )
        self.assertFalse(
            any(
                result.get("rule_id") == "HYDRIC_PRESSURE_001"
                for result in missing_data_point["rule_results"]
            )
        )
