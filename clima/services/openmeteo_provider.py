"""
==========================================================
AgroClima Café

Open-Meteo Provider

Responsável pela comunicação com a API Open-Meteo para
obtenção de dados meteorológicos atuais e históricos.

==========================================================
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.utils import timezone

from .dto import WeatherDTO
from .provider import WeatherProvider


class OpenMeteoProvider(WeatherProvider):

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    TIMEOUT = 15

    TIMEZONE = "America/Sao_Paulo"

    def __init__(self):

        self.last_payload = None

    # ======================================================
    # CLIMA ATUAL
    # ======================================================

    def current_weather(
        self,
        municipio,
    ):

        params = {

            "latitude": float(
                municipio.latitude
            ),

            "longitude": float(
                municipio.longitude
            ),

            "current": ",".join([

                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "pressure_msl",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "wind_speed_10m",
                "wind_direction_10m",

            ]),

            "timezone": self.TIMEZONE,

            "temperature_unit": "celsius",

            "precipitation_unit": "mm",

        }

        try:

            response = requests.get(

                self.BASE_URL,

                params=params,

                timeout=self.TIMEOUT,

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

            municipio,

        )

    # ======================================================
    # CLIMA ATUAL A PARTIR DO CACHE
    # ======================================================

    def current_weather_from_cache(
        self,
        payload,
        municipio,
    ):

        return self._to_dto(

            payload,

            municipio,

        )

    # ======================================================
    # HISTÓRICO HORÁRIO
    # ======================================================

    def historical_hourly_weather(
        self,
        municipio,
        days=7,
    ):
        """
        Obtém dados meteorológicos horários reais dos
        últimos dias através da API Open-Meteo.

        Não replica valores.

        Cada registro retornado representa uma observação
        horária independente.

        Exemplo:

            09/08 00:00
            09/08 01:00
            09/08 02:00
            ...
            15/08 18:00

        Os dados são preparados para persistência no modelo
        WeatherObservation.
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

        params = {

            "latitude": float(
                municipio.latitude
            ),

            "longitude": float(
                municipio.longitude
            ),

            "hourly": ",".join([

                "temperature_2m",
                "relative_humidity_2m",
                "pressure_msl",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "wind_speed_10m",
                "wind_direction_10m",

            ]),

            "past_days": max(
                0,
                days - 1,
            ),

            "forecast_days": 1,

            "timezone": self.TIMEZONE,

            "temperature_unit": "celsius",

            "precipitation_unit": "mm",

            "wind_speed_unit": "kmh",

        }

        try:

            response = requests.get(

                self.BASE_URL,

                params=params,

                timeout=self.TIMEOUT,

            )

            response.raise_for_status()

        except requests.RequestException as exc:

            raise RuntimeError(

                "Erro ao consultar histórico horário "
                f"Open-Meteo: {exc}"

            ) from exc

        payload = response.json()

        hourly = payload.get(
            "hourly",
            {},
        )

        times = hourly.get(
            "time",
            [],
        )

        temperatures = hourly.get(
            "temperature_2m",
            [],
        )

        humidities = hourly.get(
            "relative_humidity_2m",
            [],
        )

        pressures = hourly.get(
            "pressure_msl",
            [],
        )

        precipitations = hourly.get(
            "precipitation",
            [],
        )

        weather_codes = hourly.get(
            "weather_code",
            [],
        )

        cloud_covers = hourly.get(
            "cloud_cover",
            [],
        )

        wind_speeds = hourly.get(
            "wind_speed_10m",
            [],
        )

        wind_directions = hourly.get(
            "wind_direction_10m",
            [],
        )

        total = min(

            len(times),

            len(temperatures),

            len(humidities),

            len(pressures),

            len(precipitations),

            len(weather_codes),

            len(cloud_covers),

            len(wind_speeds),

            len(wind_directions),

        )

        historical = []

        local_timezone = ZoneInfo(
            self.TIMEZONE
        )

        for index in range(total):

            if (
                temperatures[index] is None
                or humidities[index] is None
                or pressures[index] is None
                or precipitations[index] is None
                or weather_codes[index] is None
                or cloud_covers[index] is None
                or wind_speeds[index] is None
                or wind_directions[index] is None
            ):

                continue

            observation_time = (
                datetime.fromisoformat(
                    times[index]
                )
            )

            if timezone.is_naive(
                observation_time
            ):

                observation_time = (
                    observation_time.replace(
                        tzinfo=local_timezone
                    )
                )

            historical.append({

                "observation_time": (
                    observation_time
                ),

                "temperatura": (
                    float(
                        temperatures[index]
                    )
                ),

                "umidade": (
                    float(
                        humidities[index]
                    )
                ),

                "pressao": (
                    float(
                        pressures[index]
                    )
                ),

                "precipitacao": (
                    float(
                        precipitations[index]
                    )
                ),

                "codigo_tempo": int(
                    weather_codes[index]
                ),

                "cobertura_nuvens": int(
                    cloud_covers[index]
                ),

                "velocidade_vento": (
                    float(
                        wind_speeds[index]
                    )
                ),

                "direcao_vento": int(
                    round(
                        wind_directions[index]
                    )
                ) % 360,

            })

        return historical

    # ======================================================
    # HISTÓRICO DIÁRIO
    # ======================================================

    def historical_weather(
        self,
        municipio,
        days=7,
    ):
        """
        Mantém a série diária disponível para outros
        componentes do sistema.

        A coleta histórica principal utilizada para
        WeatherObservation é a série horária.
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

        params = {

            "latitude": float(
                municipio.latitude
            ),

            "longitude": float(
                municipio.longitude
            ),

            "daily": ",".join([

                "temperature_2m_mean",
                "temperature_2m_min",
                "temperature_2m_max",
                "precipitation_sum",

            ]),

            "past_days": max(
                0,
                days - 1,
            ),

            "forecast_days": 1,

            "timezone": self.TIMEZONE,

            "temperature_unit": "celsius",

            "precipitation_unit": "mm",

        }

        try:

            response = requests.get(

                self.BASE_URL,

                params=params,

                timeout=self.TIMEOUT,

            )

            response.raise_for_status()

        except requests.RequestException as exc:

            raise RuntimeError(

                "Erro ao consultar histórico diário "
                f"Open-Meteo: {exc}"

            ) from exc

        payload = response.json()

        daily = payload.get(
            "daily",
            {},
        )

        dates = daily.get(
            "time",
            [],
        )

        temperatures = daily.get(
            "temperature_2m_mean",
            [],
        )

        temperatures_min = daily.get(
            "temperature_2m_min",
            [],
        )

        temperatures_max = daily.get(
            "temperature_2m_max",
            [],
        )

        precipitation = daily.get(
            "precipitation_sum",
            [],
        )

        historical = []

        total = min(

            len(dates),

            len(temperatures),

            len(precipitation),

        )

        for index in range(total):

            temperature = (
                temperatures[index]
            )

            rain = (
                precipitation[index]
            )

            if temperature is None:

                continue

            historical.append({

                "data": dates[index],

                "temperatura": round(
                    float(
                        temperature
                    ),
                    1,
                ),

                "temperatura_min": (

                    round(
                        float(
                            temperatures_min[index]
                        ),
                        1,
                    )

                    if (
                        index
                        < len(
                            temperatures_min
                        )
                        and temperatures_min[index]
                        is not None
                    )

                    else None

                ),

                "temperatura_max": (

                    round(
                        float(
                            temperatures_max[index]
                        ),
                        1,
                    )

                    if (
                        index
                        < len(
                            temperatures_max
                        )
                        and temperatures_max[index]
                        is not None
                    )

                    else None

                ),

                "precipitacao": round(

                    float(
                        rain
                        if rain is not None
                        else 0
                    ),

                    1,

                ),

            })

        if len(historical) > days:

            historical = historical[-days:]

        return historical

    # ======================================================
    # CONVERSÃO PARA WEATHER DTO
    # ======================================================

    def _to_dto(
        self,
        payload,
        municipio,
    ):

        current = payload["current"]

        observation_time = (
            current.get("time")
        )

        if observation_time:

            observation_time = (
                datetime.fromisoformat(
                    observation_time
                )
            )

            if timezone.is_naive(
                observation_time
            ):

                observation_time = (
                    observation_time.replace(
                        tzinfo=ZoneInfo(
                            self.TIMEZONE
                        )
                    )
                )

        else:

            observation_time = (
                timezone.now()
            )

        return WeatherDTO(

            municipio_id=municipio.id,

            observation_time=(
                observation_time
            ),

            temperature=(
                current[
                    "temperature_2m"
                ]
            ),

            apparent_temperature=(
                current.get(
                    "apparent_temperature"
                )
            ),

            humidity=(
                current[
                    "relative_humidity_2m"
                ]
            ),

            pressure=(
                current[
                    "pressure_msl"
                ]
            ),

            wind_speed=(
                current[
                    "wind_speed_10m"
                ]
            ),

            wind_direction=(
                current[
                    "wind_direction_10m"
                ]
            ),

            precipitation=(
                current[
                    "precipitation"
                ]
            ),

            weather_code=(
                current[
                    "weather_code"
                ]
            ),

            cloud_cover=(
                current[
                    "cloud_cover"
                ]
            ),

            dew_point=None,

            solar_radiation=None,

            uv_index=None,

            visibility=None,

        )