"""
AgroClima Café
Weather Service
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from clima.models import (
    Provider,
    WeatherObservation,
    WeatherStation,
)

from .cache_service import CacheService
from .openmeteo_provider import OpenMeteoProvider


class WeatherService:

    CACHE_MINUTES = 30

    def __init__(self):
        self.cache = CacheService()
        self.providers = {
            Provider.OPEN_METEO: OpenMeteoProvider(),
        }

    def update_current_weather(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        station = self._get_or_create_station(
            municipio,
            provider,
        )

        provider_instance = self.providers[provider]

        cached = self.cache.get(
            municipio,
            provider,
        )

        if cached:
            try:
                dto = provider_instance.current_weather_from_cache(
                    cached,
                    municipio,
                )
            except Exception:
                dto = None

            if self._is_valid_dto(dto):
                observation = self._save_observation(
                    station,
                    dto,
                )
                if observation is not None:
                    return dto

        try:
            dto = provider_instance.current_weather(
                municipio,
            )
        except Exception:
            dto = None

        if self._is_valid_dto(dto):
            payload = getattr(
                provider_instance,
                "last_payload",
                None,
            )

            if isinstance(payload, dict):
                self.cache.save(
                    municipio=municipio,
                    provider=provider,
                    payload=payload,
                    expires_at=(
                        timezone.now()
                        + timedelta(
                            minutes=self.CACHE_MINUTES
                        )
                    ),
                )

            observation = self._save_observation(
                station,
                dto,
            )

            if observation is not None:
                return dto

        fallback = self._get_last_valid_observation(
            station,
        )

        if fallback is not None:
            return fallback

        raise RuntimeError(
            "Não foi possível obter dados meteorológicos válidos."
        )

    def latest(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        cached = self.cache.get(
            municipio,
            provider,
        )

        if cached:
            try:
                dto = self.providers[provider].current_weather_from_cache(
                    cached,
                    municipio,
                )
            except Exception:
                dto = None

            if self._is_valid_dto(dto):
                return dto

        return self.update_current_weather(
            municipio,
            provider,
        )

    def _get_or_create_station(
        self,
        municipio,
        provider,
    ):
        """
        WeatherStation possui 'municipio' como ForeignKey.
        O traceback confirma que o objeto retornado não possui
        o atributo 'nome'. Portanto, não acessar station.nome.
        """

        station, created = WeatherStation.objects.get_or_create(
            municipio=municipio,
            provider=provider,
            defaults={
                "ativa": True,
            },
        )

        if not station.ativa:
            station.ativa = True
            station.save(
                update_fields=["ativa", "updated_at"]
            )

        return station

    def _save_observation(
        self,
        station,
        dto,
    ):
        if not self._is_valid_dto(dto):
            return None

        observation_time = getattr(
            dto,
            "observation_time",
            None,
        )

        if observation_time is None:
            return None

        values = {
            "temperatura": dto.temperature,
            "umidade": dto.humidity,
            "pressao": dto.pressure,
            "velocidade_vento": dto.wind_speed,
            "direcao_vento": dto.wind_direction,
            "precipitacao": dto.precipitation,
            "cobertura_nuvens": dto.cloud_cover,
            "codigo_tempo": dto.weather_code,
        }

        if any(
            value is None
            for value in values.values()
        ):
            return None

        with transaction.atomic():
            observation, _ = (
                WeatherObservation.objects.update_or_create(
                    station=station,
                    observation_time=observation_time,
                    defaults=values,
                )
            )

        return observation

    def _get_last_valid_observation(
        self,
        station,
    ):
        observations = (
            WeatherObservation.objects
            .filter(station=station)
            .order_by("-observation_time")
        )

        for observation in observations:
            if self._observation_is_valid(observation):
                return observation

        return None

    def _is_valid_dto(
        self,
        dto,
    ):
        if dto is None:
            return False

        required = (
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "weather_code",
            "cloud_cover",
        )

        return all(
            hasattr(dto, field)
            and getattr(dto, field) is not None
            for field in required
        )

    def _observation_is_valid(
        self,
        observation,
    ):
        required = (
            "temperatura",
            "umidade",
            "pressao",
            "velocidade_vento",
            "direcao_vento",
            "precipitacao",
            "cobertura_nuvens",
            "codigo_tempo",
        )

        return all(
            getattr(observation, field, None) is not None
            for field in required
        )
