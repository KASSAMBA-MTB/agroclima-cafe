"""
==========================================================
AgroClima Café

DTOs

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
    # A distinção evita atribuir ao campo legado um
    # significado diferente daquele que já possui.
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
    # O Provider será responsável por preenchê-los quando
    # a fonte disponibilizar as variáveis correspondentes.
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
    # precipitation continua existindo neste DTO, mas não
    # deverá ser interpretado como precipitação de 24 horas.
    # A migração dos consumidores ocorrerá nas fases seguintes.
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
