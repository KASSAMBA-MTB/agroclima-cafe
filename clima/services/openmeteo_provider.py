"""
==========================================================
AgroClima Café

Open-Meteo Provider

==========================================================
"""

from datetime import datetime

import requests
from django.utils import timezone

from .dto import WeatherDTO
from .provider import WeatherProvider


class OpenMeteoProvider(WeatherProvider):

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    TIMEOUT = 15

    def __init__(self):

        self.last_payload = None

    def current_weather(self, municipio):

        params = {

            "latitude": float(municipio.latitude),

            "longitude": float(municipio.longitude),

            "current": ",".join([

                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "pressure_msl",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "wind_speed_10m",
                "wind_direction_10m"

            ])

        }

        try:

            response = requests.get(

                self.BASE_URL,

                params=params,

                timeout=self.TIMEOUT

            )

            response.raise_for_status()

        except requests.RequestException as exc:

            raise RuntimeError(

                f"Erro ao consultar Open-Meteo: {exc}"

            ) from exc

        payload = response.json()

        self.last_payload = payload

        return self._to_dto(

            payload,

            municipio

        )

    def current_weather_from_cache(

        self,

        payload,

        municipio

    ):

        return self._to_dto(

            payload,

            municipio

        )

    def _to_dto(

        self,

        payload,

        municipio

    ):

        current = payload["current"]

        observation_time = current.get("time")

        if observation_time:

            observation_time = datetime.fromisoformat(

                observation_time

            )

            observation_time = timezone.make_aware(

                observation_time

            )

        else:

            observation_time = timezone.now()

        return WeatherDTO(

            municipio_id=municipio.id,

            observation_time=observation_time,

            temperature=current["temperature_2m"],

            apparent_temperature=current.get(

                "apparent_temperature"

            ),

            humidity=current["relative_humidity_2m"],

            pressure=current["pressure_msl"],

            wind_speed=current["wind_speed_10m"],

            wind_direction=current["wind_direction_10m"],

            precipitation=current["precipitation"],

            weather_code=current["weather_code"],

            cloud_cover=current["cloud_cover"],

            dew_point=None,

            solar_radiation=None,

            uv_index=None,

            visibility=None

        )