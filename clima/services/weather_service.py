"""
==========================================================
AgroClima Café

Weather Service

Responsável pela obtenção, cache e persistência dos
dados meteorológicos atuais e históricos.

==========================================================
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
        # PERSISTÊNCIA DA OBSERVAÇÃO ATUAL
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
    # COLETA HISTÓRICA
    # ==========================================================

    def collect_historical_weather(
        self,
        municipio,
        days=7,
        provider=Provider.OPEN_METEO,
    ):
        """
        Obtém dados meteorológicos horários históricos através
        do provider configurado e persiste as observações no
        banco de dados.

        Os dados são reais e provenientes da série horária
        retornada pelo Open-Meteo.

        A mesma observação não é duplicada, pois o modelo
        WeatherObservation utiliza a combinação:

            station + observation_time

        como chave única lógica.

        Retorna um resumo da operação.
        """

        try:

            days = int(days)

        except (
            TypeError,
            ValueError,
        ):

            days = 7

        days = max(
            1,
            min(days, 92),
        )

        provider_instance = (
            self.providers.get(provider)
        )

        if provider_instance is None:

            raise ValueError(
                f"Provider não suportado: {provider}"
            )

        # ======================================================
        # ESTAÇÃO
        # ======================================================

        station = (
            self._get_or_create_station(
                municipio=municipio,
                provider=provider,
            )
        )

        # ======================================================
        # OBTENÇÃO DO HISTÓRICO
        # ======================================================

        historical_data = (
            provider_instance
            .historical_hourly_weather(
                municipio=municipio,
                days=days,
            )
        )

        if not historical_data:

            return {
                "municipio": municipio,
                "provider": provider,
                "dias": days,
                "total_recebido": 0,
                "total_persistido": 0,
                "total_atualizado": 0,
            }

        # ======================================================
        # PERSISTÊNCIA
        # ======================================================

        total_persistido = 0

        total_atualizado = 0

        with transaction.atomic():

            for item in historical_data:

                observation_time = (
                    item.get(
                        "observation_time"
                    )
                )

                if observation_time is None:

                    continue

                observation, created = (
                    WeatherObservation.objects
                    .update_or_create(

                        station=station,

                        observation_time=(
                            observation_time
                        ),

                        defaults={

                            "temperatura": (
                                item.get(
                                    "temperatura",
                                    0,
                                )
                            ),

                            "umidade": (
                                item.get(
                                    "umidade",
                                    0,
                                )
                            ),

                            "pressao": (
                                item.get(
                                    "pressao",
                                    0,
                                )
                            ),

                            "velocidade_vento": (
                                item.get(
                                    "velocidade_vento",
                                    0,
                                )
                            ),

                            "direcao_vento": (
                                item.get(
                                    "direcao_vento",
                                    0,
                                )
                            ),

                            "precipitacao": (
                                item.get(
                                    "precipitacao",
                                    0,
                                )
                            ),

                            "cobertura_nuvens": (
                                item.get(
                                    "cobertura_nuvens",
                                    0,
                                )
                            ),

                            "codigo_tempo": (
                                item.get(
                                    "codigo_tempo",
                                    0,
                                )
                            ),

                        },
                    )
                )

                if created:

                    total_persistido += 1

                else:

                    total_atualizado += 1

        # ======================================================
        # RESULTADO
        # ======================================================

        return {

            "municipio": municipio,

            "provider": provider,

            "dias": days,

            "total_recebido": len(
                historical_data
            ),

            "total_persistido": (
                total_persistido
            ),

            "total_atualizado": (
                total_atualizado
            ),

        }

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

        O objeto Municipio é utilizado diretamente na relação
        com WeatherStation.
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
    # OBSERVAÇÃO ATUAL
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