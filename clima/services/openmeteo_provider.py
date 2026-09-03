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

            # Série horária usada para calcular o acumulado
            # móvel de precipitação das últimas 24 horas.
            # O campo current.precipitation representa somente
            # a precipitação da hora anterior e não substitui
            # o acumulado de 24 horas.
            "hourly": "precipitation",

            # Variáveis diárias ambientais usadas pelo contrato
            # agroclimático da FASE 1.
            #
            # uv_index_max = índice UV máximo do dia.
            # sunrise/sunset = horários locais do nascer e pôr do sol.
            # daylight_duration = duração do período de luz, em segundos.
            "daily": ",".join([
                "uv_index_max",
                "sunrise",
                "sunset",
                "daylight_duration",
            ]),

            "past_days": 1,

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
    # CONTRATO METEOROLÓGICO CANÔNICO — FASE 1
    # ======================================================

    @staticmethod
    def _weather_condition_from_code(
        weather_code,
    ):
        """
        Normaliza o código WMO da Open-Meteo para o contrato
        meteorológico canônico do AgroClima.

        Neve não é condição operacional para a região
        monitorada. Granizo somente é reconhecido quando a
        fonte informa os códigos WMO 96/99.
        """

        code = int(weather_code)

        if code == 0:
            return "CLEAR"

        if code in (1, 2, 3):
            return "CLOUDY"

        if code in (45, 48):
            return "FOG"

        if code in (51, 53, 55, 56, 57):
            return "DRIZZLE"

        if code in (61, 63, 65, 66, 67):
            return "RAIN"

        if code in (80, 81, 82):
            return "RAIN_SHOWER"

        if code == 95:
            return "THUNDERSTORM"

        if code in (96, 99):
            return "HAIL"

        return "UNKNOWN"

    @classmethod
    def _rain_now_from_code(
        cls,
        weather_code,
    ):
        """
        Determina evidência de chuva atual a partir do
        weather_code.

        Trata-se de evidência de MODELO, não de observação
        física. A resolução entre fontes ocorrerá em fase
        posterior.
        """

        condition = cls._weather_condition_from_code(
            weather_code
        )

        if condition in (
            "DRIZZLE",
            "RAIN",
            "RAIN_SHOWER",
            "THUNDERSTORM",
            "HAIL",
        ):
            return True

        if condition in (
            "CLEAR",
            "CLOUDY",
            "FOG",
        ):
            return False

        return None

    # ======================================================
    # PRECIPITAÇÃO ACUMULADA — ÚLTIMAS 24 HORAS
    # ======================================================

    def _precipitation_24h_from_hourly(
        self,
        payload,
        observation_time,
    ):
        """
        Calcula o acumulado móvel real das últimas 24 horas.

        O cálculo usa exclusivamente a série
        ``hourly.precipitation`` retornada pela Open-Meteo.

        A regra é:

        1. localizar o horário da observação;
        2. usar exatamente 24 intervalos horários;
        3. terminar o intervalo no horário da observação;
        4. nunca utilizar horário futuro;
        5. rejeitar valores ausentes ou inválidos;
        6. devolver o total em milímetros.

        ``current.precipitation`` não é utilizado para construir
        o acumulado de 24 horas. Ele permanece disponível como
        precipitação do intervalo horário atual.

        O resultado retorna ``None`` somente quando a série não
        possui informação suficiente para produzir um acumulado
        confiável.
        """

        if not isinstance(payload, dict):
            return None

        hourly = payload.get(
            "hourly",
            {},
        )

        if not isinstance(hourly, dict):
            return None

        times = hourly.get(
            "time",
            [],
        )

        precipitations = hourly.get(
            "precipitation",
            [],
        )

        if not isinstance(times, list):
            return None

        if not isinstance(precipitations, list):
            return None

        total = min(
            len(times),
            len(precipitations),
        )

        if total < 24:
            return None

        parsed_times = []

        for index in range(total):

            raw_time = times[index]

            try:

                parsed_time = datetime.fromisoformat(
                    str(raw_time)
                )

            except (
                TypeError,
                ValueError,
            ):

                parsed_times.append(None)

                continue

            if parsed_time.tzinfo is not None:

                parsed_time = (
                    parsed_time.replace(
                        tzinfo=None
                    )
                )

            parsed_times.append(
                parsed_time
            )

        target_time = None

        if observation_time is not None:

            target_time = (
                observation_time.replace(
                    tzinfo=None
                )
            )

        target_index = None

        if target_time is not None:

            exact_candidates = [

                index

                for index, parsed_time
                in enumerate(parsed_times)

                if (
                    parsed_time is not None
                    and parsed_time == target_time
                )

            ]

            if exact_candidates:

                target_index = (
                    exact_candidates[-1]
                )

            else:

                eligible_candidates = [

                    index

                    for index, parsed_time
                    in enumerate(parsed_times)

                    if (
                        parsed_time is not None
                        and parsed_time <= target_time
                    )

                ]

                if eligible_candidates:

                    target_index = (
                        eligible_candidates[-1]
                    )

        if target_index is None:

            valid_candidates = [

                index

                for index, parsed_time
                in enumerate(parsed_times)

                if parsed_time is not None

            ]

            if not valid_candidates:

                return None

            target_index = (
                valid_candidates[-1]
            )

        start_index = (
            target_index - 23
        )

        if start_index < 0:
            return None

        selected_times = parsed_times[
            start_index : target_index + 1
        ]

        selected_values = precipitations[
            start_index : target_index + 1
        ]

        if len(selected_times) != 24:
            return None

        if len(selected_values) != 24:
            return None

        if any(
            parsed_time is None
            for parsed_time
            in selected_times
        ):
            return None

        numeric_values = []

        for value in selected_values:

            if value is None:
                return None

            try:

                numeric_value = float(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):

                return None

            if numeric_value < 0:
                return None

            numeric_values.append(
                numeric_value
            )

        accumulated = sum(
            numeric_values
        )

        return round(
            accumulated,
            2,
        )


    # ======================================================
    # VALIDAÇÃO DO ACUMULADO ANTES DO WEATHERDTO
    # ======================================================

    @staticmethod
    def _validate_precipitation_24h_result(
        value,
    ):
        """
        Valida o valor calculado antes de entregá-lo ao
        WeatherDTO.

        A ausência de informação permanece representada por
        ``None``. Um valor presente precisa ser numérico e não
        negativo.

        Esta função não cria dados. Ela apenas impede que um
        resultado estruturalmente inválido atravesse a fronteira
        do Provider.
        """

        if value is None:
            return None

        try:

            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if numeric_value < 0:
            return None

        return round(
            numeric_value,
            2,
        )

    # ======================================================
    # DADOS AMBIENTAIS DIÁRIOS
    # ======================================================

    def _daily_environmental_data(
        self,
        payload,
        observation_time,
    ):
        """
        Extrai as variáveis ambientais diárias da resposta
        Open-Meteo para a data da observação.

        A função não cria valores. Quando a resposta não possui
        a série diária, a data não é localizada ou um valor é
        inválido, o campo correspondente permanece None.
        """

        if not isinstance(payload, dict):
            return {
                "uv_index_max": None,
                "sunrise": None,
                "sunset": None,
                "daylight_duration_seconds": None,
            }

        daily = payload.get(
            "daily",
            {},
        )

        if not isinstance(daily, dict):
            return {
                "uv_index_max": None,
                "sunrise": None,
                "sunset": None,
                "daylight_duration_seconds": None,
            }

        dates = daily.get(
            "time",
            [],
        )

        uv_values = daily.get(
            "uv_index_max",
            [],
        )

        sunrise_values = daily.get(
            "sunrise",
            [],
        )

        sunset_values = daily.get(
            "sunset",
            [],
        )

        daylight_values = daily.get(
            "daylight_duration",
            [],
        )

        if not isinstance(dates, list):
            dates = []

        if not isinstance(uv_values, list):
            uv_values = []

        if not isinstance(sunrise_values, list):
            sunrise_values = []

        if not isinstance(sunset_values, list):
            sunset_values = []

        if not isinstance(daylight_values, list):
            daylight_values = []

        target_date = None

        if observation_time is not None:
            target_date = observation_time.date().isoformat()

        target_index = None

        if target_date is not None:
            for index, raw_date in enumerate(dates):
                if str(raw_date) == target_date:
                    target_index = index
                    break

        if target_index is None:
            return {
                "uv_index_max": None,
                "sunrise": None,
                "sunset": None,
                "daylight_duration_seconds": None,
            }

        local_timezone = ZoneInfo(
            self.TIMEZONE
        )

        uv_index_max = None

        if target_index < len(uv_values):
            raw_uv = uv_values[target_index]

            if raw_uv is not None:
                try:
                    numeric_uv = float(raw_uv)

                    if numeric_uv >= 0:
                        uv_index_max = round(
                            numeric_uv,
                            2,
                        )
                except (
                    TypeError,
                    ValueError,
                ):
                    uv_index_max = None

        sunrise = self._parse_daily_local_datetime(
            sunrise_values,
            target_index,
            local_timezone,
        )

        sunset = self._parse_daily_local_datetime(
            sunset_values,
            target_index,
            local_timezone,
        )

        daylight_duration_seconds = None

        if target_index < len(daylight_values):
            raw_duration = daylight_values[target_index]

            if raw_duration is not None:
                try:
                    numeric_duration = float(
                        raw_duration
                    )

                    if numeric_duration >= 0:
                        daylight_duration_seconds = round(
                            numeric_duration,
                            2,
                        )
                except (
                    TypeError,
                    ValueError,
                ):
                    daylight_duration_seconds = None

        return {
            "uv_index_max": uv_index_max,
            "sunrise": sunrise,
            "sunset": sunset,
            "daylight_duration_seconds": (
                daylight_duration_seconds
            ),
        }

    @staticmethod
    def _parse_daily_local_datetime(
        values,
        index,
        local_timezone,
    ):
        """
        Converte um horário diário ISO retornado pela Open-Meteo
        em datetime com o fuso America/Sao_Paulo.
        """

        if index >= len(values):
            return None

        raw_value = values[index]

        if raw_value is None:
            return None

        try:
            parsed_value = datetime.fromisoformat(
                str(raw_value)
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if timezone.is_naive(
            parsed_value
        ):
            parsed_value = parsed_value.replace(
                tzinfo=local_timezone
            )

        return parsed_value

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

        environmental_data = (
            self._daily_environmental_data(
                payload,
                observation_time,
            )
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

            # uv_index permanece preservado para compatibilidade.
            # O novo campo uv_index_max recebe o valor diário canônico.
            uv_index=None,

            uv_index_max=(
                environmental_data[
                    "uv_index_max"
                ]
            ),

            visibility=None,

            sunrise=(
                environmental_data[
                    "sunrise"
                ]
            ),

            sunset=(
                environmental_data[
                    "sunset"
                ]
            ),

            daylight_duration_seconds=(
                environmental_data[
                    "daylight_duration_seconds"
                ]
            ),

            # Contrato meteorológico canônico — FASE 1.
            rain_now=(
                self._rain_now_from_code(
                    current[
                        "weather_code"
                    ]
                )
            ),

            # current.precipitation representa a hora
            # precedente na Open-Meteo. Não é precipitação 24h.
            precipitation_1h_mm=(
                current[
                    "precipitation"
                ]
            ),

            # Acumulado móvel real das últimas 24 observações
            # horárias retornadas pela Open-Meteo.
            # O cálculo é realizado na origem para que o valor
            # percorra o contrato WeatherDTO como dado próprio.
            precipitation_24h_mm=(
                self._validate_precipitation_24h_result(
                    self._precipitation_24h_from_hourly(
                        payload,
                        observation_time,
                    )
                )
            ),

            weather_condition=(
                self._weather_condition_from_code(
                    current[
                        "weather_code"
                    ]
                )
            ),

            source="OPEN_METEO",

            source_type="MODEL",

            observed_at=(
                observation_time
            ),

            retrieved_at=(
                timezone.now()
            ),

            quality_status="MODEL_ESTIMATE",

            # A confiança comparativa será definida pelo
            # resolver após integração das fontes observacionais.
            confidence=None,

        )