"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: test_dashboard_service_indicadores_fase2_integracao.py

Objetivo:
    Validar a integração real da Fase 2 no DashboardService, especialmente:

        DashboardService
            -> _attach_climate_data()
            -> AgroClimateIndicatorService
            -> map_points

    O teste não acessa API externa e não altera dados persistidos.
    Os dados meteorológicos e a avaliação oficial de FRI são controlados por
    mocks para validar somente o contrato e o fluxo de integração.
===============================================================================
"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import dashboard.services.dashboard_service as dashboard_service_module
from dashboard.services.agroclimate_indicator_service import (
    AgroClimateIndicatorService,
)
from dashboard.services.dashboard_service import DashboardService


class DashboardServiceFase2IntegracaoTests(TestCase):
    """
    Testes de integração da distribuição dos indicadores da Fase 2.
    """

    def _build_service(self):
        """
        Cria o DashboardService sem executar chamadas reais dos serviços.
        """
        service = DashboardService.__new__(DashboardService)

        service.kpi_service = MagicMock()
        service.chart_service = MagicMock()
        service.ranking_service = MagicMock()
        service.events_service = MagicMock()
        service.map_service = MagicMock()
        service.weather_service = MagicMock()
        service.frost_risk_service = MagicMock()
        service.agroclimate_indicator_service = MagicMock(
            wraps=AgroClimateIndicatorService()
        )
        service._current_weather_dtos = {}

        return service

    @staticmethod
    def _build_observation(
        municipality_name="São João da Boa Vista",
        temperature="22.50",
        precipitation_1h="3.20",
        precipitation_24h="18.40",
    ):
        """Cria uma observação compatível com os atributos consumidos."""
        municipality = SimpleNamespace(nome=municipality_name)
        station = SimpleNamespace(municipio=municipality)

        return SimpleNamespace(
            station=station,
            observation_time=datetime(2026, 9, 4, 12, 0, 0),
            temperatura=Decimal(temperature) if temperature is not None else None,
            umidade=Decimal("72.00"),
            velocidade_vento=Decimal("8.50"),
            cobertura_nuvens=40,
            chuva_agora=False,
            precipitacao_1h=(
                Decimal(precipitation_1h)
                if precipitation_1h is not None
                else None
            ),
            precipitacao_24h=(
                Decimal(precipitation_24h)
                if precipitation_24h is not None
                else None
            ),
            condicao_tempo="Parcialmente nublado",
        )

    @staticmethod
    def _configure_weather_queries(observation=None, historical=None):
        """
        Substitui somente as consultas ORM utilizadas pelo método testado.
        """
        observation_manager = MagicMock()
        observation_manager.select_related.return_value.filter.return_value.order_by.return_value = (
            [observation] if observation is not None else []
        )

        historical_manager = MagicMock()
        historical_manager.select_related.return_value.filter.return_value.order_by.return_value = (
            [historical] if historical is not None else []
        )

        return observation_manager, historical_manager

    def test_attach_climate_data_calls_specialized_indicator_service(self):
        """O DashboardService deve delegar os indicadores ao serviço da Fase 2."""
        service = self._build_service()
        point = {
            "id": 1,
            "nome": "São João da Boa Vista",
        }
        observation = self._build_observation()

        service.agroclimate_indicator_service.calculate.return_value = {
            "temperature": 22.5,
            "temperature_class": "favorable",
            "temperature_class_label": "Faixa favorável",
            "precipitation_1h_mm": 3.2,
            "precipitation_24h_mm": 18.4,
        }

        observation_manager, historical_manager = (
            self._configure_weather_queries(observation=observation)
        )

        with patch.object(
            dashboard_service_module,
            "WeatherObservation",
        ) as weather_model, patch.object(
            dashboard_service_module,
            "HistoricalWeatherDaily",
        ) as historical_model:
            weather_model.objects = observation_manager
            historical_model.objects = historical_manager

            result = service._attach_climate_data([point])

        service.agroclimate_indicator_service.calculate.assert_called_once()
        enriched = result[0]

        self.assertEqual(enriched["temperature"], 22.5)
        self.assertEqual(enriched["temperature_class"], "favorable")
        self.assertEqual(
            enriched["temperature_class_label"],
            "Faixa favorável",
        )
        self.assertEqual(enriched["precipitation_1h_mm"], 3.2)
        self.assertEqual(enriched["precipitation_24h_mm"], 18.4)

    def test_map_points_receive_phase2_fields_through_get_dashboard(self):
        """
        O fluxo get_dashboard deve devolver os indicadores no map_points.
        """
        service = self._build_service()
        point = {
            "id": 1,
            "nome": "São João da Boa Vista",
            "altitude": 700,
        }
        observation = self._build_observation()

        service.kpi_service.get_kpis.return_value = {
            "municipio_id": 1,
            "municipio_nome": "São João da Boa Vista",
        }
        service.chart_service.get_chart.return_value = {}
        service.chart_service.get_chart_periods.return_value = {}
        service.events_service.get_events.return_value = []
        service.map_service.get_points.return_value = [point]
        service.ranking_service.get_ranking.return_value = []
        service.agroclimate_indicator_service.calculate.return_value = {
            "temperature": 22.5,
            "temperature_class": "favorable",
            "temperature_class_label": "Faixa favorável",
            "precipitation_1h_mm": 3.2,
            "precipitation_24h_mm": 18.4,
        }
        service.frost_risk_service.evaluate_frost.return_value = {
            "score": 17.0,
            "severity": "low",
            "confidence": 0.91,
        }

        observation_manager, historical_manager = (
            self._configure_weather_queries(observation=observation)
        )

        with patch.object(
            dashboard_service_module,
            "WeatherObservation",
        ) as weather_model, patch.object(
            dashboard_service_module,
            "HistoricalWeatherDaily",
        ) as historical_model:
            weather_model.objects = observation_manager
            historical_model.objects = historical_manager

            service._refresh_current_weather = MagicMock(
                return_value={
                    "total": 0,
                    "atualizados": 0,
                    "erros": 0,
                    "municipios": [],
                }
            )

            result = service.get_dashboard()

        map_point = result["map_points"][0]

        self.assertEqual(map_point["temperature_class"], "favorable")
        self.assertEqual(map_point["temperature_class_label"], "Faixa favorável")
        self.assertEqual(map_point["precipitation_1h_mm"], 3.2)
        self.assertEqual(map_point["precipitation_24h_mm"], 18.4)
        self.assertEqual(map_point["precipitacao_1h"], 3.2)
        self.assertEqual(map_point["precipitacao_24h"], 18.4)
        self.assertEqual(map_point["precipitation"], 3.2)

    def test_phase2_service_does_not_receive_or_modify_fri_fields(self):
        """
        O serviço especializado não deve receber responsabilidade de FRI.
        """
        service = self._build_service()
        point = {
            "id": 1,
            "nome": "São João da Boa Vista",
            "fri": 88.0,
            "severity": "critical",
            "confidence": 0.77,
        }
        observation = self._build_observation()

        service.agroclimate_indicator_service.calculate.return_value = {
            "temperature": 22.5,
            "temperature_class": "favorable",
            "temperature_class_label": "Faixa favorável",
            "precipitation_1h_mm": 3.2,
            "precipitation_24h_mm": 18.4,
        }

        observation_manager, historical_manager = (
            self._configure_weather_queries(observation=observation)
        )

        with patch.object(
            dashboard_service_module,
            "WeatherObservation",
        ) as weather_model, patch.object(
            dashboard_service_module,
            "HistoricalWeatherDaily",
        ) as historical_model:
            weather_model.objects = observation_manager
            historical_model.objects = historical_manager

            result = service._attach_climate_data([point])

        enriched = result[0]

        self.assertEqual(enriched["fri"], 88.0)
        self.assertEqual(enriched["severity"], "critical")
        self.assertEqual(enriched["confidence"], 0.77)

    def test_frost_evaluation_remains_after_indicator_integration(self):
        """
        O FRI continua sendo materializado pelo FrostRiskService posterior.
        """
        service = self._build_service()
        point = {
            "id": 1,
            "nome": "São João da Boa Vista",
            "altitude": 700,
        }
        observation = self._build_observation()

        service.agroclimate_indicator_service.calculate.return_value = {
            "temperature": 22.5,
            "temperature_class": "favorable",
            "temperature_class_label": "Faixa favorável",
            "precipitation_1h_mm": 3.2,
            "precipitation_24h_mm": 18.4,
        }
        service.frost_risk_service.evaluate_frost.return_value = {
            "score": 42.0,
            "severity": "moderate",
            "confidence": 0.93,
        }

        observation_manager, historical_manager = (
            self._configure_weather_queries(observation=observation)
        )

        with patch.object(
            dashboard_service_module,
            "WeatherObservation",
        ) as weather_model, patch.object(
            dashboard_service_module,
            "HistoricalWeatherDaily",
        ) as historical_model:
            weather_model.objects = observation_manager
            historical_model.objects = historical_manager

            climate_points = service._attach_climate_data([point])
            evaluated_points = service._attach_frost_intelligence(
                climate_points
            )

        self.assertEqual(evaluated_points[0]["fri"], 42.0)
        self.assertEqual(evaluated_points[0]["severity"], "moderate")
        self.assertEqual(evaluated_points[0]["confidence"], 0.93)
        service.frost_risk_service.evaluate_frost.assert_called_once()

    def test_missing_precipitation_remains_none_in_map_point(self):
        """
        Ausência de precipitação não pode ser convertida em zero.
        """
        service = self._build_service()
        point = {
            "id": 1,
            "nome": "São João da Boa Vista",
        }
        observation = self._build_observation(
            precipitation_1h=None,
            precipitation_24h=None,
        )

        service.agroclimate_indicator_service.calculate.return_value = {
            "temperature": 22.5,
            "temperature_class": "favorable",
            "temperature_class_label": "Faixa favorável",
            "precipitation_1h_mm": None,
            "precipitation_24h_mm": None,
        }

        observation_manager, historical_manager = (
            self._configure_weather_queries(observation=observation)
        )

        with patch.object(
            dashboard_service_module,
            "WeatherObservation",
        ) as weather_model, patch.object(
            dashboard_service_module,
            "HistoricalWeatherDaily",
        ) as historical_model:
            weather_model.objects = observation_manager
            historical_model.objects = historical_manager

            result = service._attach_climate_data([point])

        enriched = result[0]

        self.assertIsNone(enriched["precipitation_1h_mm"])
        self.assertIsNone(enriched["precipitation_24h_mm"])
        self.assertIsNone(enriched["precipitacao_1h"])
        self.assertIsNone(enriched["precipitacao_24h"])
        self.assertIsNone(enriched["precipitation"])


if __name__ == "__main__":
    import unittest

    unittest.main()
