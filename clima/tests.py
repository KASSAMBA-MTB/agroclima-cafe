from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from clima.services.dto import WeatherDTO
from clima.services.openmeteo_provider import OpenMeteoProvider


class WeatherDTOContractTests(TestCase):
    """
    Testes do contrato meteorológico canônico — FASE 1.

    Estes testes não dependem de chamadas externas à Open-Meteo.
    """

    def test_dto_exposes_canonical_weather_fields(self):
        dto = WeatherDTO(
            municipio_id=1,
            observation_time=datetime(
                2026,
                8,
                26,
                14,
                0,
                tzinfo=ZoneInfo("America/Sao_Paulo"),
            ),
            temperature=19.4,
            humidity=80.0,
            pressure=900.0,
            wind_speed=5.0,
            wind_direction=180,
            precipitation=0.0,
            weather_code=61,
            cloud_cover=80,
            rain_now=True,
            precipitation_1h_mm=0.0,
            precipitation_24h_mm=None,
            weather_condition="RAIN",
            source="OPEN_METEO",
            source_type="MODEL",
            observed_at=datetime(
                2026,
                8,
                26,
                14,
                0,
                tzinfo=ZoneInfo("America/Sao_Paulo"),
            ),
            retrieved_at=datetime(
                2026,
                8,
                26,
                14,
                1,
                tzinfo=ZoneInfo("America/Sao_Paulo"),
            ),
            quality_status="MODEL_ESTIMATE",
            confidence=None,
        )

        self.assertTrue(dto.rain_now)
        self.assertEqual(dto.precipitation_1h_mm, 0.0)
        self.assertIsNone(dto.precipitation_24h_mm)
        self.assertEqual(dto.weather_condition, "RAIN")
        self.assertEqual(dto.source, "OPEN_METEO")
        self.assertEqual(dto.source_type, "MODEL")


class OpenMeteoWeatherConditionTests(TestCase):
    """
    Testes da normalização WMO → contrato canônico.
    """

    def test_rain_now_is_not_derived_from_precipitation_zero(self):
        provider = OpenMeteoProvider()

        rain_now = provider._rain_now_from_code(61)

        self.assertTrue(rain_now)

    def test_clear_weather_is_not_rain(self):
        provider = OpenMeteoProvider()

        rain_now = provider._rain_now_from_code(0)

        self.assertFalse(rain_now)

    def test_rain_shower_is_rain_now(self):
        provider = OpenMeteoProvider()

        rain_now = provider._rain_now_from_code(80)

        self.assertTrue(rain_now)

    def test_thunderstorm_is_rain_now(self):
        provider = OpenMeteoProvider()

        rain_now = provider._rain_now_from_code(95)

        self.assertTrue(rain_now)

    def test_hail_codes_are_hail(self):
        provider = OpenMeteoProvider()

        self.assertEqual(
            provider._weather_condition_from_code(96),
            "HAIL",
        )

        self.assertEqual(
            provider._weather_condition_from_code(99),
            "HAIL",
        )

    def test_snow_is_not_converted_to_hail(self):
        provider = OpenMeteoProvider()

        self.assertNotEqual(
            provider._weather_condition_from_code(71),
            "HAIL",
        )

    def test_unknown_code_returns_unknown(self):
        provider = OpenMeteoProvider()

        self.assertEqual(
            provider._weather_condition_from_code(999),
            "UNKNOWN",
        )


class OpenMeteoDTOIntegrationTests(TestCase):
    """
    Testa a transformação de um payload Open-Meteo no WeatherDTO.

    Não realiza HTTP. O payload é controlado pelo teste.
    """

    def test_current_payload_populates_canonical_fields(self):
        provider = OpenMeteoProvider()

        class MunicipioStub:
            id = 1

        payload = {
            "current": {
                "time": "2026-08-26T14:00",
                "temperature_2m": 19.4,
                "relative_humidity_2m": 80,
                "apparent_temperature": 19.0,
                "pressure_msl": 900.0,
                "precipitation": 0.0,
                "weather_code": 61,
                "cloud_cover": 80,
                "wind_speed_10m": 5.0,
                "wind_direction_10m": 180,
            }
        }

        dto = provider._to_dto(
            payload,
            MunicipioStub(),
        )

        self.assertTrue(dto.rain_now)
        self.assertEqual(
            dto.precipitation_1h_mm,
            0.0,
        )
        self.assertIsNone(
            dto.precipitation_24h_mm,
        )
        self.assertEqual(
            dto.weather_condition,
            "RAIN",
        )
        self.assertEqual(
            dto.source,
            "OPEN_METEO",
        )
        self.assertEqual(
            dto.source_type,
            "MODEL",
        )
        self.assertIsNotNone(
            dto.observed_at,
        )
        self.assertIsNotNone(
            dto.retrieved_at,
        )
        self.assertEqual(
            dto.quality_status,
            "MODEL_ESTIMATE",
        )
