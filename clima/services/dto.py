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

    uv_index: float | None = None

    visibility: float | None = None