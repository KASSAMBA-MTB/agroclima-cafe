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
            "observed_at",
            None,
        )

        if observation_time is None:
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
            # Campo legado: preservado para compatibilidade.
            "precipitacao": dto.precipitation,
            "cobertura_nuvens": dto.cloud_cover,
            "codigo_tempo": dto.weather_code,
        }

        # --------------------------------------------------
        # Contrato meteorológico canônico — FASE 1
        # --------------------------------------------------
        #
        # Cada variável possui significado próprio:
        #   chuva_agora       -> condição atual
        #   precipitacao_1h   -> precipitação de 1 hora
        #   precipitacao_24h  -> acumulado de 24 horas
        #
        # O campo legado 'precipitacao' permanece somente para
        # compatibilidade com consumidores ainda não migrados.
        canonical_values = {
            "precipitacao_1h": getattr(
                dto,
                "precipitation_1h_mm",
                None,
            ),
            "precipitacao_24h": getattr(
                dto,
                "precipitation_24h_mm",
                None,
            ),
            "chuva_agora": getattr(
                dto,
                "rain_now",
                None,
            ),
            "condicao_tempo": getattr(
                dto,
                "weather_condition",
                None,
            ),
            "tipo_fonte": getattr(
                dto,
                "source_type",
                None,
            ),
            "coletado_em": getattr(
                dto,
                "retrieved_at",
                None,
            ),
            "qualidade_dado": getattr(
                dto,
                "quality_status",
                None,
            ),
            "confianca": getattr(
                dto,
                "confidence",
                None,
            ),
            # --------------------------------------------------
            # Indicadores ambientais — FASE 1
            # --------------------------------------------------
            #
            # Esses campos pertencem à observação persistida e
            # devem acompanhar o DTO até o PostgreSQL.
            #
            # UV máximo:
            #   valor diário fornecido pelo Open-Meteo.
            #
            # Nascer/pôr do sol:
            #   horários locais do município, já normalizados
            #   pelo Provider.
            #
            # Duração da luz do dia:
            #   segundos de luz do dia fornecidos pelo Provider.
            "uv_index_max": getattr(
                dto,
                "uv_index_max",
                None,
            ),
            "sunrise": getattr(
                dto,
                "sunrise",
                None,
            ),
            "sunset": getattr(
                dto,
                "sunset",
                None,
            ),
            "daylight_duration_seconds": getattr(
                dto,
                "daylight_duration_seconds",
                None,
            ),
        }

        model_field_names = {
            field.name
            for field in WeatherObservation._meta.get_fields()
        }

        for field_name, value in canonical_values.items():
            if (
                field_name in model_field_names
                and value is not None
            ):
                values[field_name] = value

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

        # --------------------------------------------------
        # Contrato meteorológico canônico — FASE 1
        # --------------------------------------------------
        # Os campos básicos permanecem obrigatórios para
        # compatibilidade com a cadeia existente.
        #
        # A condição atual de chuva passa a ser validada por
        # rain_now, e não por precipitation.
        #
        # O serviço atual exige o acumulado de 24h porque a Dashboard
        # o oferece como dado operacional. Ausência de 24h não pode ser
        # mascarada como zero ou substituída pelo valor de 1h.
        required = (
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "weather_code",
            "cloud_cover",
            "rain_now",
            "precipitation_1h_mm",
            "precipitation_24h_mm",
            "weather_condition",
            "source_type",
            "observed_at",
            "retrieved_at",
            "quality_status",
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
        # Fallback legado preservado nesta etapa. A migração dos
        # consumidores ocorrerá progressivamente, sem invalidar
        # registros históricos já existentes.
        required = (
            "temperatura",
            "umidade",
            "pressao",
            "velocidade_vento",
            "direcao_vento",
            "precipitacao",
            "cobertura_nuvens",
            "codigo_tempo",
            "precipitacao_1h",
            "precipitacao_24h",
            "chuva_agora",
            "condicao_tempo",
            "tipo_fonte",
            "coletado_em",
            "qualidade_dado",
        )

        return all(
            getattr(observation, field, None) is not None
            for field in required
        )
