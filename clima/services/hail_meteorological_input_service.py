"""Aquisição municipal em lote das variáveis experimentais de granizo MP-01.12.

Este serviço é isolado do provider de clima corrente e do contrato histórico G7.4.
Obtém uma única previsão ECMWF IFS025 para as coordenadas municipais, preserva
a hora válida e deixa valores ausentes como None. Não classifica risco de granizo.
"""
import math

import requests
from django.core.cache import cache
from django.utils import timezone


class HailMeteorologicalInputService:
    """Obtém CAPE e ventos em níveis de pressão para vários municípios em lote."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    SOURCE = "open-meteo-forecast-api"
    MODEL = "ecmwf_ifs025"
    TIMEZONE = "America/Sao_Paulo"
    CACHE_TTL_SECONDS = 900
    TIMEOUT_SECONDS = 20
    HOURLY_VARIABLES = (
        "cape",
        "wind_speed_925hPa",
        "wind_direction_925hPa",
        "wind_speed_500hPa",
        "wind_direction_500hPa",
        "wet_bulb_temperature_2m",
        "temperature_850hPa",
        "relative_humidity_850hPa",
    )
    REQUIRED_VARIABLES = (
        "cape",
        "wind_speed_925hPa",
        "wind_direction_925hPa",
        "wind_speed_500hPa",
        "wind_direction_500hPa",
    )

    def __init__(self, http_get=None):
        self._http_get = http_get or requests.get

    def fetch_for_points(self, points):
        """Retorna entradas indexadas por id municipal, com uma chamada em lote.

        Pontos sem coordenadas válidas permanecem sem entrada meteorológica.
        Falhas da API são propagadas para o chamador decidir como degradar.
        """
        points = list(points or [])
        valid_points = [
            point for point in points
            if self._valid_coordinate(point.get("latitude"))
            and self._valid_coordinate(point.get("longitude"))
        ]
        if not valid_points:
            return {}

        coordinates = [
            (float(point["latitude"]), float(point["longitude"]))
            for point in valid_points
        ]
        cache_key = self._cache_key([
            (point.get("id"), lat, lon)
            for point, (lat, lon) in zip(valid_points, coordinates)
        ])
        cached = cache.get(cache_key)
        if isinstance(cached, dict):
            return cached

        params = {
            "latitude": ",".join(f"{lat:.6f}" for lat, _ in coordinates),
            "longitude": ",".join(f"{lon:.6f}" for _, lon in coordinates),
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "models": self.MODEL,
            "timezone": self.TIMEZONE,
            "wind_speed_unit": "ms",
            "forecast_hours": 24,
        }
        response = self._http_get(
            self.BASE_URL,
            params=params,
            timeout=self.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(valid_points):
            raise ValueError(
                "Open-Meteo retornou quantidade de locais diferente da solicitada."
            )

        results = {}
        for point, location in zip(valid_points, locations):
            results[point.get("id")] = self._normalise_location(location)

        cache.set(cache_key, results, self.CACHE_TTL_SECONDS)
        return results

    @classmethod
    def _normalise_location(cls, payload):
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            hourly = {}
        times = hourly.get("time")
        if not isinstance(times, list) or not times:
            times = []
        valid_index = 0
        valid_time = times[valid_index] if times else None

        series = {}
        for variable in cls.HOURLY_VARIABLES:
            values = hourly.get(variable)
            value = values[valid_index] if isinstance(values, list) and len(values) > valid_index else None
            series[variable] = cls._finite_number(value)

        return {
            "series": series,
            "valid_from": valid_time,
            "valid_to": valid_time,
            "provenance": {
                "source": cls.SOURCE,
                "model": cls.MODEL,
                "source_run": None,
                "valid_time": valid_time,
                "model_grid_latitude": payload.get("latitude"),
                "model_grid_longitude": payload.get("longitude"),
                "timezone": payload.get("timezone"),
                "unit_contract": {
                    "cape": "J/kg",
                    "wind_speed_925hPa": "m/s",
                    "wind_direction_925hPa": "°",
                    "wind_speed_500hPa": "m/s",
                    "wind_direction_500hPa": "°",
                    "wet_bulb_temperature_2m": "°C",
                    "temperature_850hPa": "°C",
                    "relative_humidity_850hPa": "%",
                },
                "required_variables_complete": all(
                    series.get(variable) is not None
                    for variable in cls.REQUIRED_VARIABLES
                ),
            },
        }

    @staticmethod
    def _finite_number(value):
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _valid_coordinate(cls, value):
        return cls._finite_number(value) is not None

    @staticmethod
    def _cache_key(coordinates):
        import hashlib
        import json

        serialised = json.dumps(coordinates, separators=(",", ":"), sort_keys=True)
        digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
        return f"agroclima:hail_inputs:{digest}"
