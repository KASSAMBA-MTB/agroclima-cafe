"""
==========================================================
AgroClima Café

DTOs meteorológicos canônicos

FASE 6 — ETo e indicadores hídricos
==========================================================
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class WeatherDTO:

    municipio_id: int

    observation_time: datetime

    temperature: float

    humidity: float

    pressure: float

    wind_speed: float

    wind_direction: int

    precipitation: float

    weather_code: int

    cloud_cover: int

    apparent_temperature: float | None = None

    dew_point: float | None = None

    solar_radiation: float | None = None

    # ------------------------------------------------------
    # Índice UV
    # ------------------------------------------------------
    #
    # uv_index é preservado por compatibilidade com os
    # consumidores existentes.
    #
    # uv_index_max representa o índice UV máximo previsto/
    # calculado para o dia de referência da observação.
    # ------------------------------------------------------

    uv_index: float | None = None

    uv_index_max: float | None = None

    visibility: float | None = None

    # ------------------------------------------------------
    # Informações solares e astronômicas — FASE 1
    # ------------------------------------------------------
    #
    # sunrise e sunset representam os horários locais de
    # nascer e pôr do sol para a data de referência.
    #
    # daylight_duration_seconds representa a duração do
    # período entre nascer e pôr do sol, em segundos.
    #
    # Os campos são opcionais porque nem toda fonte,
    # histórico ou observação existente possui esses dados.
    # ------------------------------------------------------

    sunrise: datetime | None = None

    sunset: datetime | None = None

    daylight_duration_seconds: float | None = None

    # ------------------------------------------------------
    # Contrato meteorológico canônico — FASE 1
    # ------------------------------------------------------
    #
    # Os campos legados acima são preservados para manter
    # compatibilidade com os consumidores atuais.
    #
    # precipitation não representa precipitação de 24 horas.
    # ------------------------------------------------------

    rain_now: bool | None = None

    precipitation_1h_mm: float | None = None

    precipitation_24h_mm: float | None = None

    weather_condition: str | None = None

    source: str | None = None

    source_type: str | None = None

    observed_at: datetime | None = None

    retrieved_at: datetime | None = None

    quality_status: str | None = None

    confidence: str | None = None

    # ------------------------------------------------------
    # Evapotranspiração de referência — FASE 6
    # ------------------------------------------------------
    #
    # ETo é transportada pelo DTO como dado diário da fonte.
    #
    # Unidade canônica:
    #     milímetros por dia (mm/dia)
    #
    # O DTO somente transporta o valor. A metodologia de
    # cálculo e a validação pertencem à camada de serviço/
    # provider correspondente.
    #
    # None significa dado indisponível e não deve ser
    # convertido automaticamente para zero.
    # ------------------------------------------------------

    eto_mm_day: float | None = None
