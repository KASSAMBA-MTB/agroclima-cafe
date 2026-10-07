"""
G7.5 / G6 — Serviço de Indicadores Horários do Single Run.

Responsabilidade:
- receber o contexto canônico produzido pelo SingleRunDomainService;
- calcular somente agregados descritivos sobre a série horária;
- preservar MISSING como ausência;
- não converter ausência em zero;
- não reutilizar o contrato diário do HistoricalClimateIndicatorService;
- não consultar ORM, API ou frontend;
- não produzir FRI, recomendações, alertas ou regras agronômicas.

Este serviço é deliberadamente separado do HistoricalClimateIndicatorService,
que permanece responsável pela série histórica diária.
"""

from math import isfinite


class SingleRunHourlyIndicatorService:
    """Calcula indicadores descritivos sobre um contexto horário de Single Run."""

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

    def calculate(self, context):
        """Retorna agregados descritivos da série horária recebida."""
        data = context or {}
        forecast = data.get("forecast") or {}

        result = {
            "indicator_version": "1.0",
            "frequency": "HOURLY",
            "run": data.get("run"),
            "forecast_count": data.get("forecast_count", 0),
            "record_count": data.get("record_count", 0),
        }

        result["temperature_2m"] = self._aggregate(
            forecast.get("temperature_2m"),
        )
        result["precipitation"] = self._aggregate(
            forecast.get("precipitation"),
            non_negative=True,
        )
        result["relative_humidity_2m"] = self._aggregate(
            forecast.get("relative_humidity_2m"),
        )
        result["wind_speed_10m"] = self._aggregate(
            forecast.get("wind_speed_10m"),
            non_negative=True,
        )

        return result

    @classmethod
    def _aggregate(cls, series, non_negative=False):
        """Calcula count, missing, min, max e mean sem fabricar dados."""
        items = series or []
        numeric = []

        for item in items:
            if not isinstance(item, dict):
                continue

            if item.get("value_status") != "NUMERIC":
                continue

            value = cls._finite_number(item.get("value"))
            if value is None:
                continue

            if non_negative and value < 0:
                continue

            numeric.append(value)

        missing = 0
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("value_status") == "MISSING"
            ):
                missing += 1

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
