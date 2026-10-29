"""Aquisição municipal em lote das variáveis experimentais de granizo MP-01.12.

A associação dos resultados é feita pelas coordenadas da grade retornada.
Este serviço não classifica risco de granizo.
"""
import hashlib
import json
import math
import time
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache


class HailMeteorologicalInputService:
    """Obtém e valida entradas meteorológicas experimentais por município."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    SOURCE = "open-meteo-forecast-api"
    MODEL = "ecmwf_ifs025"
    TIMEZONE = "America/Sao_Paulo"
    CACHE_TTL_SECONDS = 900
    TIMEOUT_SECONDS = 20
    MAX_HTTP_ATTEMPTS = 3
    RETRY_BASE_DELAY_SECONDS = 0.5
    GRID_TIE_TOLERANCE = 1e-12

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
        """Retorna entradas por ID municipal, validando identidade da grade."""
        points = list(points or [])
        valid_points = [
            point for point in points
            if self._valid_coordinate(point.get("latitude"), -90, 90)
            and self._valid_coordinate(point.get("longitude"), -180, 180)
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
            result = deepcopy(cached)
            for entry in result.values():
                provenance = entry.setdefault("provenance", {})
                provenance["cache_status"] = "HIT"
            return result

        params = {
            "latitude": ",".join(f"{lat:.6f}" for lat, _ in coordinates),
            "longitude": ",".join(f"{lon:.6f}" for _, lon in coordinates),
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "models": self.MODEL,
            "timezone": self.TIMEZONE,
            "wind_speed_unit": "ms",
            "forecast_hours": 24,
        }

        response = self._request_with_retry(params)
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]

        if len(locations) != len(valid_points):
            raise ValueError(
                "Open-Meteo retornou quantidade de locais diferente da solicitada."
            )

        # Primeiro valida e agrupa os resultados pela identidade da grade.
        grids = {}
        for location in locations:
            if not isinstance(location, dict):
                raise ValueError("Resposta meteorológica de local inválida.")

            latitude = self._finite_number(location.get("latitude"))
            longitude = self._finite_number(location.get("longitude"))

            if (
                latitude is None
                or longitude is None
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
            ):
                raise ValueError(
                    "Resposta sem coordenadas de grade válidas."
                )

            normalized = self._normalise_location(location)
            grid_key = self._grid_key(latitude, longitude)
            normalized["provenance"]["model_grid_latitude"] = latitude
            normalized["provenance"]["model_grid_longitude"] = longitude

            if grid_key in grids:
                previous = grids[grid_key]
                if (
                    previous["series"] != normalized["series"]
                    or previous["valid_from"] != normalized["valid_from"]
                    or previous["valid_to"] != normalized["valid_to"]
                ):
                    raise ValueError(
                        "Open-Meteo retornou séries divergentes para a mesma grade."
                    )
            else:
                grids[grid_key] = normalized

        if not grids:
            raise ValueError("Open-Meteo não retornou coordenadas de grade.")

        grid_items = list(grids.items())
        results = {}
        created_at = datetime.now(
            ZoneInfo(self.TIMEZONE)
        ).isoformat(timespec="seconds")

        # Cada município é associado à grade mais próxima. Empates não
        # são resolvidos pela ordem da resposta: são rejeitados.
        for point, (requested_lat, requested_lon) in zip(
            valid_points, coordinates
        ):
            distances = [
                (
                    (requested_lat - entry["provenance"]["model_grid_latitude"]) ** 2
                    + (requested_lon - entry["provenance"]["model_grid_longitude"]) ** 2,
                    grid_key,
                )
                for grid_key, entry in grid_items
            ]
            minimum = min(distance for distance, _ in distances)
            nearest = [
                grid_key
                for distance, grid_key in distances
                if abs(distance - minimum) <= self.GRID_TIE_TOLERANCE
            ]

            if len(nearest) != 1:
                raise ValueError(
                    "Associação de município à grade meteorológica ambígua."
                )

            entry = deepcopy(grids[nearest[0]])
            provenance = entry["provenance"]
            provenance["requested_latitude"] = requested_lat
            provenance["requested_longitude"] = requested_lon
            provenance["cache_status"] = "MISS"
            provenance["cache_created_at"] = created_at
            provenance["cache_ttl_seconds"] = self.CACHE_TTL_SECONDS
            results[point.get("id")] = entry

        cache.set(cache_key, deepcopy(results), self.CACHE_TTL_SECONDS)
        return results

    def _request_with_retry(self, params):
        """Repete apenas falhas HTTP classificadas como transitórias."""
        for attempt in range(1, self.MAX_HTTP_ATTEMPTS + 1):
            try:
                response = self._http_get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                retryable = isinstance(
                    exc,
                    (requests.ConnectionError, requests.Timeout),
                )

                if isinstance(exc, requests.HTTPError):
                    status = getattr(
                        getattr(exc, "response", None),
                        "status_code",
                        None,
                    )
                    retryable = status == 429 or (
                        isinstance(status, int) and 500 <= status <= 599
                    )

                if not retryable or attempt >= self.MAX_HTTP_ATTEMPTS:
                    raise

                time.sleep(
                    self.RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                )

        raise RuntimeError("Aquisição meteorológica terminou sem resposta.")

    @classmethod
    def _normalise_location(cls, payload):
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            hourly = {}

        times = hourly.get("time")
        if not isinstance(times, list):
            times = []

        valid_index = cls._select_valid_index(times)
        valid_time = times[valid_index] if valid_index is not None else None

        series = {}
        for variable in cls.HOURLY_VARIABLES:
            values = hourly.get(variable)
            value = (
                values[valid_index]
                if valid_index is not None
                and isinstance(values, list)
                and len(values) > valid_index
                else None
            )
            series[variable] = cls._finite_number(value)

        return {
            "series": series,
            "valid_from": valid_time,
            "valid_to": valid_time,
            "provenance": {
                "source": cls.SOURCE,
                "model": cls.MODEL,
                "source_run": payload.get("model_run"),
                "valid_time": valid_time,
                "model_grid_latitude": cls._finite_number(
                    payload.get("latitude")
                ),
                "model_grid_longitude": cls._finite_number(
                    payload.get("longitude")
                ),
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

    @classmethod
    def _select_valid_index(cls, times):
        if not isinstance(times, list) or not times:
            return None

        now = datetime.now(ZoneInfo(cls.TIMEZONE)).replace(tzinfo=None)
        parsed = []

        for index, value in enumerate(times):
            try:
                parsed.append((index, datetime.fromisoformat(value)))
            except (TypeError, ValueError):
                continue

        future_or_current = [
            (index, valid_time)
            for index, valid_time in parsed
            if valid_time >= now
        ]
        if future_or_current:
            return min(future_or_current, key=lambda item: item[1])[0]

        return None

    @staticmethod
    def _finite_number(value):
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _valid_coordinate(cls, value, minimum, maximum):
        number = cls._finite_number(value)
        return number is not None and minimum <= number <= maximum

    @staticmethod
    def _grid_key(latitude, longitude):
        return round(float(latitude), 6), round(float(longitude), 6)

    @staticmethod
    def _cache_key(coordinates):
        serialized = json.dumps(
            coordinates,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"agroclima:hail_inputs:{digest}"