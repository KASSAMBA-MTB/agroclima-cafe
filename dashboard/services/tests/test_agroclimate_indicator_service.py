"""
===============================================================================
AgroClima Café
Testes do Serviço de Indicadores Agroclimáticos

FASE 2 — Testes unitários
===============================================================================
"""

import math
import unittest

from dashboard.services.agroclimate_indicator_service import (
    AgroClimateIndicatorService,
)
from dashboard.services.thermal_classification_service import (
    ThermalClassificationService,
)


class AgroClimateIndicatorServiceTests(unittest.TestCase):
    """Testes unitários dos indicadores derivados da FASE 2."""

    def setUp(self):
        self.service = AgroClimateIndicatorService()

    def test_temperature_frost_boundary(self):
        result = self.service.calculate({"temperature": 0})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_FROST,
        )
        self.assertEqual(
            result["temperature_class_label"],
            "Geada / extremo frio",
        )

    def test_temperature_very_cold_boundary(self):
        result = self.service.calculate({"temperature": 8})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_VERY_COLD,
        )

    def test_temperature_cold_boundary(self):
        result = self.service.calculate({"temperature": 14})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_COLD,
        )

    def test_temperature_cool_boundary(self):
        result = self.service.calculate({"temperature": 17.9})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_COOL,
        )

    def test_temperature_favorable_boundary(self):
        result = self.service.calculate({"temperature": 24})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_FAVORABLE,
        )

    def test_temperature_warm_boundary(self):
        result = self.service.calculate({"temperature": 28})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_WARM,
        )

    def test_temperature_hot_boundary(self):
        result = self.service.calculate({"temperature": 28.1})
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_HOT,
        )
        self.assertEqual(
            result["temperature_class_label"],
            "Muito quente",
        )

    def test_precipitation_fields_and_aliases(self):
        result = self.service.calculate(
            {
                "temperature": 20,
                "precipitation_1h_mm": 2.5,
                "precipitation_24h_mm": 18.75,
            }
        )

        self.assertEqual(result["temperature"], 20.0)
        self.assertEqual(result["precipitation_1h_mm"], 2.5)
        self.assertEqual(result["precipitation_24h_mm"], 18.75)

        alias_result = self.service.calculate(
            {
                "temperature": 20,
                "precipitacao_1h": 3.25,
                "precipitacao_24h": 21.5,
            }
        )

        self.assertEqual(alias_result["precipitation_1h_mm"], 3.25)
        self.assertEqual(alias_result["precipitation_24h_mm"], 21.5)

    def test_missing_data_is_preserved(self):
        result = self.service.calculate(
            {
                "temperature": None,
                "precipitation_1h_mm": None,
                "precipitation_24h_mm": None,
            }
        )

        self.assertIsNone(result["temperature"])
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_UNAVAILABLE,
        )
        self.assertEqual(
            result["temperature_class_label"],
            ThermalClassificationService.LABELS[
                ThermalClassificationService.CLASS_UNAVAILABLE
            ],
        )
        self.assertIsNone(result["precipitation_1h_mm"])
        self.assertIsNone(result["precipitation_24h_mm"])

    def test_none_input_returns_empty_result(self):
        result = self.service.calculate(None)

        self.assertIsNone(result["temperature"])
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_UNAVAILABLE,
        )
        self.assertEqual(
            result["temperature_class_label"],
            "Sem dado",
        )
        self.assertIsNone(result["precipitation_1h_mm"])
        self.assertIsNone(result["precipitation_24h_mm"])

    def test_non_finite_values_do_not_create_indicators(self):
        for value in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            result = self.service.calculate(
                {
                    "temperature": value,
                    "precipitation_1h_mm": value,
                    "precipitation_24h_mm": value,
                }
            )

            self.assertIsNone(result["temperature"])
            self.assertEqual(
                result["temperature_class"],
                ThermalClassificationService.CLASS_UNAVAILABLE,
            )
            self.assertIsNone(result["precipitation_1h_mm"])
            self.assertIsNone(result["precipitation_24h_mm"])

    def test_boolean_temperature_is_not_treated_as_number(self):
        result = self.service.calculate(
            {
                "temperature": True,
                "precipitation_1h_mm": False,
                "precipitation_24h_mm": True,
            }
        )

        self.assertIsNone(result["temperature"])
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_UNAVAILABLE,
        )
        self.assertIsNone(result["precipitation_1h_mm"])
        self.assertIsNone(result["precipitation_24h_mm"])

    def test_calculate_from_dto_compatible_object(self):
        class WeatherDTOStub:
            temperature = 21.5
            precipitation_1h_mm = 1.2
            precipitation_24h_mm = 9.8

        result = self.service.calculate_from_dto(
            WeatherDTOStub()
        )

        self.assertEqual(result["temperature"], 21.5)
        self.assertEqual(
            result["temperature_class"],
            ThermalClassificationService.CLASS_FAVORABLE,
        )
        self.assertEqual(result["precipitation_1h_mm"], 1.2)
        self.assertEqual(result["precipitation_24h_mm"], 9.8)

    def test_no_fri_or_risk_fields_are_created(self):
        result = self.service.calculate(
            {
                "temperature": 20,
                "precipitation_1h_mm": 0.5,
                "precipitation_24h_mm": 4.0,
            }
        )

        self.assertNotIn("fri", result)
        self.assertNotIn("severity", result)
        self.assertNotIn("confidence", result)
        self.assertNotIn("frost_risk", result)


if __name__ == "__main__":
    unittest.main()
