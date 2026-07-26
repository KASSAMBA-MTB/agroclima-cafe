"""
==========================================================
AgroClima Café

Weather Service
==========================================================
"""

from datetime import timedelta

from django.utils import timezone

from clima.models import (
    Provider,
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

        cached = self.cache.get(
            municipio,
            provider,
        )

        if cached:

            dto = self.providers[provider].current_weather_from_cache(
                cached,
                municipio,
            )

        else:

            dto = self.providers[provider].current_weather(
                municipio,
            )

            self.cache.save(
                municipio=municipio,
                provider=provider,
                payload=self.providers[provider].last_payload,
                expires_at=timezone.now()
                + timedelta(minutes=self.CACHE_MINUTES),
            )

        WeatherStation.objects.get_or_create(
            municipio=municipio,
            provider=provider,
            defaults={
                "ativa": True,
            },
        )

        return dto

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

            return self.providers[provider].current_weather_from_cache(
                cached,
                municipio,
            )

        return self.update_current_weather(
            municipio,
            provider,
        )