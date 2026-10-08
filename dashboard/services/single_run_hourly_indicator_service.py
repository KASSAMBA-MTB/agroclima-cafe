"""
G7.7 — Serviço de Indicadores Horários do Single Run.

Responsabilidade:
- receber o contexto horário canônico disponibilizado pelo G7.6;
- expor integralmente as 14 séries canônicas aos consumidores de indicadores;
- preservar timestamp, valor, status e unidade;
- manter os agregados descritivos já homologados para as variáveis que
  possuem contrato de agregação existente;
- preservar MISSING como ausência;
- não criar agregações sem contrato semântico;
- não converter ausência em zero;
- não produzir FRI, recomendações, alertas ou regras agronômicas;
- não criar ETo nem contrato diário.

Princípio G7.7:
    Exposição canônica precede interpretação derivada.

As quatro agregações históricas já existentes permanecem:
    - temperature_2m
    - precipitation
    - relative_humidity_2m
    - wind_speed_10m

As demais variáveis ficam disponíveis integralmente em ``series`` até que
um contrato específico autorize uma operação derivada.
"""

from math import isfinite


class SingleRunHourlyIndicatorService:
    """Consome e expõe o contrato horário Single Run sem criar semântica nova."""

    VARIABLES = (
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_direction_10m",
        "pressure_msl",
        "surface_pressure",
        "cape",
        "temperature_850hPa",
        "relative_humidity_850hPa",
        "geopotential_height_850hPa",
        "temperature_500hPa",
        "geopotential_height_500hPa",
    )

    AGGREGATED_VARIABLES = (
        "temperature_2m",
        "precipitation",
        "relative_humidity_2m",
        "wind_speed_10m",
    )

    def calculate(self, context):
        """Retorna exposição canônica horária e os agregados já contratados."""
        data = context or {}
        series = self._canonical_series(data)

        result = {
            "indicator_version": "1.1",
            "frequency": "HOURLY",
            "run": data.get("run"),
            "forecast_count": data.get(
                "forecast_count",
                len(next(iter(series.values()), {}).get("timestamps", [])),
            ),
            "record_count": data.get("record_count", 0),
            "variables": list(self.VARIABLES),
            "series": series,
        }

        for variable in self.AGGREGATED_VARIABLES:
            result[variable] = self._aggregate(
                series[variable],
                non_negative=variable in {
                    "precipitation",
                    "wind_speed_10m",
                },
            )

        return result

    @classmethod
    def _canonical_series(cls, context):
        """
        Normaliza as duas entradas já existentes:

        1. ``series`` produzido pelo SingleRunIndicatorAdapter G7.6;
        2. ``forecast`` usado pelo contrato/testes horários anteriores.

        A normalização não calcula valores. Ela somente preserva os quatro
        campos canônicos: timestamps, values, statuses e units.
        """
        source = context.get("series")
        if isinstance(source, dict):
            return {
                variable: cls._copy_series(source.get(variable))
                for variable in cls.VARIABLES
            }

        return cls._series_from_legacy_forecast(
            context.get("forecast") or {}
        )

    @classmethod
    def _series_from_legacy_forecast(cls, forecast):
        result = {
            variable: {
                "timestamps": [],
                "values": [],
                "statuses": [],
                "units": [],
            }
            for variable in cls.VARIABLES
        }

        for variable in cls.VARIABLES:
            items = forecast.get(variable) or []
            for item in items:
                if not isinstance(item, dict):
                    continue

                result[variable]["timestamps"].append(
                    item.get("forecast_datetime")
                )
                result[variable]["values"].append(item.get("value"))
                result[variable]["statuses"].append(
                    item.get("value_status")
                )
                result[variable]["units"].append(item.get("unit"))

        return result

    @staticmethod
    def _copy_series(series):
        series = series or {}
        return {
            "timestamps": list(series.get("timestamps") or []),
            "values": list(series.get("values") or []),
            "statuses": list(series.get("statuses") or []),
            "units": list(series.get("units") or []),
        }

    @classmethod
    def _aggregate(cls, series, non_negative=False):
        """Calcula apenas os agregados previamente contratados."""
        values = series.get("values") or []
        statuses = series.get("statuses") or []

        numeric = []

        for value, status in zip(values, statuses):
            if status != "NUMERIC":
                continue

            number = cls._finite_number(value)
            if number is None:
                continue

            if non_negative and number < 0:
                continue

            numeric.append(number)

        missing = sum(
            1
            for status in statuses
            if status == "MISSING"
        )

        if not numeric:
            minimum = None
            maximum = None
            mean = None
        else:
            minimum = min(numeric)
            maximum = max(numeric)
            mean = sum(numeric) / len(numeric)

        return {
            "numeric_count": len(numeric),
            "missing_count": missing,
            "min": minimum,
            "max": maximum,
            "mean": mean,
        }

    @staticmethod
    def _finite_number(value):
        if value is None or isinstance(value, bool):
            return None

        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if not isfinite(number):
            return None

        return number
