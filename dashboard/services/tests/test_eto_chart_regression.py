"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃƒO PAULO - UNIVESP

Curso...........: Bacharelado em CiÃªncia de Dados
Projeto.........: AgroClima CafÃ©
MÃ³dulo..........: Dashboard
Arquivo.........: test_eto_chart_regression.py

Objetivo:
    Proteger a cadeia canÃ´nica de ETo no Dashboard:

        DashboardService
            -> canonical_context
            -> KPIService
            -> ChartService
            -> perÃodo "hoje"

    O teste nÃ£o acessa API externa e nÃ£o altera dados persistidos.
===============================================================================
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from dashboard.services.chart_service import ChartService
from dashboard.services.kpi_service import KPIService


class EToChartRegressionTests(TestCase):
    """Testes de regressÃ£o do transporte da ETo atÃ© o grÃ¡fico."""

    def _build_kpi_context(self):
        """Monta um contexto canÃ´nico totalmente controlado pelo teste."""
        municipio = MagicMock(
            id=1,
            nome="SÃ£o JoÃ£o da Boa Vista",
        )

        return {
            "municipio": municipio,
            "observation": None,
            "temperature": 22.2,
            "humidity": 68.7,
            "precipitation_1h_mm": 0.0,
            "precipitation_24h_mm": 5.0,
            "precipitation_7d_mm": 32.4,
            "precipitation_30d_mm": 212.8,
            "precipitation_24h_values": [5.0] * 6,
            "rain_now": False,
            "wind_speed": 4.9,
            "cloud_cover": 33.5,
            "eto_mm_day": 3.763333333333333,
        }

    def _build_historical_frost_context(self):
        """Retorno histÃ³rico controlado para isolar o contrato testado."""
        return {
            "historical_frost": False,
            "historical_total_days": 0,
            "historical_frost_days": 0,
            "historical_frost_frequency": 0.0,
            "historical_frost_episodes": 0,
            "historical_min_temperature": None,
        }

    def test_kpi_service_consumes_canonical_eto(self):
        """O KPIService deve transportar a ETo do contexto canÃ´nico."""
        service = KPIService()
        context = self._build_kpi_context()

        with patch(
            "dashboard.services.kpi_service.Municipio.objects.count",
            return_value=6,
        ), patch(
            "dashboard.services.kpi_service.Municipio.objects.all",
        ) as all_municipios, patch.object(
            service.iac,
            "calculate",
            return_value={
                "index": 50.0,
                "classification": "Moderado",
                "color": "#999999",
                "icon": "bi-dash-circle",
                "scores": {},
            },
        ), patch.object(
            service,
            "_get_historical_frost_context",
            return_value=self._build_historical_frost_context(),
        ):
            all_municipios.return_value.order_by.return_value = [
                context["municipio"]
            ]

            result = service.get_kpis(
                canonical_context=context
            )

        self.assertEqual(result["eto_mm_day"], 3.76)
        self.assertEqual(result["municipios"], 6)

    def test_chart_today_uses_persisted_eto_source(self):
        """O perÃodo Hoje deve utilizar a ETo fornecida por _get_today_eto()."""
        current_kpis = {
            "temperatura_media": 22.2,
            "precipitacao_24h": 5.0,
            "eto_mm_day": 3.763333333333333,
        }

        service = ChartService()

        result = service.get_chart_periods(
            current_kpis=current_kpis
        )

        today = result["hoje"]

        self.assertEqual(
            today["eto_mm_day"],
            [3.763333333333333],
        )
        self.assertEqual(
            today["resumo"]["eto_media_diaria"],
            3.76,
        )
        self.assertEqual(
            today["resumo"]["eto_acumulada"],
            3.76,
        )
        self.assertEqual(
            today["resumo"]["eto_dias_validos"],
            1,
        )
