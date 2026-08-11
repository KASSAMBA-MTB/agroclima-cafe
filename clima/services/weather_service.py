"""
==========================================================
AgroClima Café

Weather Service

Responsável pela obtenção, cache e persistência dos
dados meteorológicos atuais.

==========================================================
"""

from datetime import timedelta

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

    # ==========================================================
    # ATUALIZAÇÃO DO CLIMA
    # ==========================================================

    def update_current_weather(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        """
        Obtém o clima atual, utilizando o cache quando disponível,
        garante a existência da estação meteorológica e persiste
        a observação climática.

        Retorna o WeatherDTO produzido pelo provider.
        """

        cached = self.cache.get(
            municipio,
            provider,
        )

        # ======================================================
        # OBTENÇÃO DOS DADOS
        # ======================================================

        if cached:

            dto = (
                self.providers[provider]
                .current_weather_from_cache(
                    cached,
                    municipio,
                )
            )

        else:

            dto = (
                self.providers[provider]
                .current_weather(
                    municipio,
                )
            )

            self.cache.save(
                municipio=municipio,
                provider=provider,
                payload=(
                    self.providers[provider]
                    .last_payload
                ),
                expires_at=(
                    timezone.now()
                    + timedelta(
                        minutes=self.CACHE_MINUTES
                    )
                ),
            )

        # ======================================================
        # ESTAÇÃO METEOROLÓGICA
        # ======================================================

        station = (
            self._get_or_create_station(
                municipio=municipio,
                provider=provider,
            )
        )

        # ======================================================
        # PERSISTÊNCIA DA OBSERVAÇÃO
        # ======================================================

        self._save_observation(
            station=station,
            dto=dto,
        )

        return dto

    # ==========================================================
    # ÚLTIMA OBSERVAÇÃO
    # ==========================================================

    def latest(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        """
        Retorna o clima mais recente disponível.

        Quando existe cache válido, utiliza o cache e também
        garante a persistência da observação correspondente.

        Quando não existe cache, realiza uma nova coleta.
        """

        cached = self.cache.get(
            municipio,
            provider,
        )

        if cached:

            dto = (
                self.providers[provider]
                .current_weather_from_cache(
                    cached,
                    municipio,
                )
            )

            station = (
                self._get_or_create_station(
                    municipio=municipio,
                    provider=provider,
                )
            )

            self._save_observation(
                station=station,
                dto=dto,
            )

            return dto

        return self.update_current_weather(
            municipio,
            provider,
        )

    # ==========================================================
    # ESTAÇÃO
    # ==========================================================

    def _get_or_create_station(
        self,
        municipio,
        provider,
    ):
        """
        Obtém ou cria a estação climática associada ao município.

        WeatherStation possui uma ForeignKey para Municipio.
        Portanto, o objeto Municipio é utilizado diretamente.
        """

        station, _ = (
            WeatherStation.objects.get_or_create(

                municipio=municipio,

                provider=provider,

                defaults={
                    "ativa": True,
                },
            )
        )

        return station

    # ==========================================================
    # OBSERVAÇÃO
    # ==========================================================

    def _save_observation(
        self,
        station,
        dto,
    ):
        """
        Persiste a observação meteorológica retornada pelo
        provider.

        A combinação:

            station + observation_time

        é única no modelo WeatherObservation.

        update_or_create evita duplicação quando a mesma
        observação for processada novamente a partir do cache.
        """

        if dto is None:

            return None

        if dto.observation_time is None:

            return None

        observation, _ = (
            WeatherObservation.objects
            .update_or_create(

                station=station,

                observation_time=(
                    dto.observation_time
                ),

                defaults={

                    "temperatura": (
                        dto.temperature
                    ),

                    "umidade": (
                        dto.humidity
                    ),

                    "pressao": (
                        dto.pressure
                    ),

                    "velocidade_vento": (
                        dto.wind_speed
                    ),

                    "direcao_vento": (
                        dto.wind_direction
                    ),

                    "precipitacao": (
                        dto.precipitation
                    ),

                    "cobertura_nuvens": (
                        dto.cloud_cover
                    ),

                    "codigo_tempo": (
                        dto.weather_code
                    ),
                },
            )
        )

        return observation