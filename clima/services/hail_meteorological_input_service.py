"""Aquisição municipal individual das variáveis experimentais MP-01.12.

Cada solicitação contém as coordenadas de um único município e sua resposta
é associada diretamente ao ID que originou a solicitação. A associação não
depende da posição em uma resposta JSON multi-local.

Este serviço fornece entradas meteorológicas. Não classifica risco ou potencial
de granizo e não define limiares operacionais.
"""

import hashlib
import json
import logging
import math
import time
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache


logger = logging.getLogger(__name__)


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
        """Obtém cada município em uma solicitação com identidade própria."""
        points = list(points or [])
        valid_points = [
            point
            for point in points
            if isinstance(point, dict)
            and self._valid_coordinate(point.get("latitude"), -90, 90)
            and self._valid_coordinate(point.get("longitude"), -180, 180)
        ]

        if not valid_points:
            return {}

        point_ids = [point.get("id") for point in valid_points]
        if any(point_id is None for point_id in point_ids):
            raise ValueError(
                "Cada município com coordenadas válidas deve possuir um ID."
            )
        if len(set(point_ids)) != len(point_ids):
            raise ValueError(
                "A solicitação contém IDs municipais duplicados."
            )

        reference_time = datetime.now(
            ZoneInfo(self.TIMEZONE)
        ).replace(tzinfo=None)
        created_at = datetime.now(
            ZoneInfo(self.TIMEZONE)
        ).isoformat(timespec="seconds")

        results = {}
        network_requests = 0
        http_attempts = 0
        cache_hits = 0
        acquired_points = 0
        partial_points = 0
        failed_points = 0

        for point in valid_points:
            point_id = point["id"]
            requested_latitude = float(point["latitude"])
            requested_longitude = float(point["longitude"])
            cache_key = self._cache_key([
                (point_id, requested_latitude, requested_longitude)
            ])

            try:
                cached = cache.get(cache_key)
            except Exception as exc:
                logger.warning(
                    "Cache de entrada MP-01.12 indisponível; município_id=%s "
                    "error_type=%s.",
                    point_id,
                    type(exc).__name__,
                )
                cached = None

            cached_entry = (
                cached.get(point_id)
                if isinstance(cached, dict)
                and set(cached) == {point_id}
                and isinstance(cached.get(point_id), dict)
                else None
            )
            cached_provenance = (
                cached_entry.get("provenance")
                if isinstance(cached_entry, dict)
                else None
            )
            if (
                isinstance(cached_entry, dict)
                and isinstance(cached_provenance, dict)
                and cached_provenance.get("required_variables_complete")
            ):
                entry = deepcopy(cached_entry)
                entry["provenance"]["cache_status"] = "HIT"
                results[point_id] = entry
                cache_hits += 1
                logger.info(
                    "Entrada Open-Meteo MP-01.12: municipio_id=%s result=cache_hit.",
                    point_id,
                )
                continue

            params = {
                "latitude": f"{requested_latitude:.6f}",
                "longitude": f"{requested_longitude:.6f}",
                "hourly": ",".join(self.HOURLY_VARIABLES),
                "models": self.MODEL,
                "timezone": self.TIMEZONE,
                "wind_speed_unit": "ms",
                "forecast_hours": 24,
            }
            network_requests += 1
            point_http_attempts = 0

            def count_http_attempt():
                nonlocal http_attempts, point_http_attempts
                http_attempts += 1
                point_http_attempts += 1

            try:
                response = self._request_with_retry(
                    params,
                    on_attempt=count_http_attempt,
                )
                location = response.json()
                if not isinstance(location, dict) or location.get("error"):
                    raise ValueError("Resposta meteorológica individual inválida.")
                if not isinstance(location.get("hourly"), dict):
                    raise ValueError("Resposta sem estrutura horária válida.")

                grid_latitude = self._finite_number(location.get("latitude"))
                grid_longitude = self._finite_number(location.get("longitude"))
                if (
                    grid_latitude is None
                    or grid_longitude is None
                    or not -90 <= grid_latitude <= 90
                    or not -180 <= grid_longitude <= 180
                ):
                    raise ValueError("Resposta sem coordenadas de grade válidas.")

                # A identidade vem da solicitação individual que produziu
                # esta resposta, nunca da posição em uma lista multi-local.
                entry = self._normalise_location(
                    location,
                    reference_time=reference_time,
                )
                entry["provenance"].update({
                    "requested_latitude": requested_latitude,
                    "requested_longitude": requested_longitude,
                    "model_grid_latitude": grid_latitude,
                    "model_grid_longitude": grid_longitude,
                    "model_grid_elevation": self._finite_number(
                        location.get("elevation")
                    ),
                    "cache_status": "MISS",
                    "cache_created_at": created_at,
                    "cache_ttl_seconds": self.CACHE_TTL_SECONDS,
                })
                results[point_id] = entry

                is_complete = entry["provenance"]["required_variables_complete"]
                # Entradas incompletas não são armazenadas: o consumidor
                # pode refazer somente essa solicitação municipal.
                if is_complete:
                    acquired_points += 1
                    try:
                        cache.set(
                            cache_key,
                            {point_id: deepcopy(entry)},
                            self.CACHE_TTL_SECONDS,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Cache de entrada MP-01.12 não foi atualizado; "
                            "município_id=%s error_type=%s.",
                            point_id,
                            type(exc).__name__,
                        )
                else:
                    partial_points += 1

                logger.info(
                    "Entrada Open-Meteo MP-01.12: municipio_id=%s "
                    "result=%s http_attempts=%s.",
                    point_id,
                    "acquired" if is_complete else "partial",
                    point_http_attempts,
                )
            except Exception as exc:
                failed_points += 1
                logger.warning(
                    "Entrada Open-Meteo MP-01.12 indisponível: municipio_id=%s "
                    "result=failed http_attempts=%s error_type=%s.",
                    point_id,
                    point_http_attempts,
                    type(exc).__name__,
                )

        logger.info(
            "Aquisição individual Open-Meteo MP-01.12 concluída: "
            "valid_points=%s requests=%s http_attempts=%s cache_hits=%s "
            "acquired=%s partial=%s failed=%s.",
            len(valid_points),
            network_requests,
            http_attempts,
            cache_hits,
            acquired_points,
            partial_points,
            failed_points,
        )
        return results

    def _request_with_retry(self, params, on_attempt=None):
        """Repete apenas falhas HTTP classificadas como transitórias."""
        for attempt in range(1, self.MAX_HTTP_ATTEMPTS + 1):
            try:
                if on_attempt is not None:
                    on_attempt()
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

        raise RuntimeError(
            "Aquisição meteorológica terminou sem resposta."
        )

    @classmethod
    def _normalise_location(cls, payload, reference_time=None):
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            hourly = {}

        times = hourly.get("time")
        if not isinstance(times, list):
            times = []

        valid_index = cls._select_valid_index(
            times,
            reference_time=reference_time,
        )
        valid_time = (
            times[valid_index] if valid_index is not None else None
        )

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
                "model_grid_elevation": cls._finite_number(
                    payload.get("elevation")
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
    def _select_valid_index(cls, times, reference_time=None):
        if not isinstance(times, list) or not times:
            return None

        if reference_time is None:
            reference_time = datetime.now(
                ZoneInfo(cls.TIMEZONE)
            ).replace(tzinfo=None)

        if reference_time.tzinfo is not None:
            reference_time = reference_time.astimezone(
                ZoneInfo(cls.TIMEZONE)
            ).replace(tzinfo=None)

        parsed = []
        for index, value in enumerate(times):
            try:
                parsed_time = datetime.fromisoformat(value)
                if parsed_time.tzinfo is not None:
                    parsed_time = parsed_time.astimezone(
                        ZoneInfo(cls.TIMEZONE)
                    ).replace(tzinfo=None)
                parsed.append((index, parsed_time))
            except (TypeError, ValueError, OverflowError):
                continue

        future_or_current = [
            (index, valid_time)
            for index, valid_time in parsed
            if valid_time >= reference_time
        ]
        if not future_or_current:
            return None

        return min(
            future_or_current,
            key=lambda item: item[1],
        )[0]

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
        return (
            number is not None
            and minimum <= number <= maximum
        )

    @classmethod
    def _cache_key(cls, coordinates):
        # Inclui o contrato da consulta para impedir reutilização de cache
        # entre versões de modelo, variáveis ou fuso horário diferentes.
        cache_payload = {
            "coordinates": coordinates,
            "model": cls.MODEL,
            "timezone": cls.TIMEZONE,
            "hourly": cls.HOURLY_VARIABLES,
        }
        serialized = json.dumps(
            cache_payload,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
        digest = hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()
        return f"agroclima:hail_inputs:{digest}"
