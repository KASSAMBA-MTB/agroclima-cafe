"""
MP-01.11 — Contrato de avaliação do potencial meteorológico de granizo.

Este módulo contém apenas validação/normalização do contrato.
Não define thresholds de granizo.
"""

from dataclasses import dataclass
from typing import Any


REQUIRED_VARIABLES = (
    "cape",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
)

COMPLEMENTARY_VARIABLES = (
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
)

METHOD_VERSION = "MP-01.11.2"
ASSESSMENT_ASSESSED = "ASSESSED"
ASSESSMENT_INSUFFICIENT = "INSUFFICIENT_DATA"

POTENTIAL_NONE = "NONE"
POTENTIAL_LOW = "LOW"
POTENTIAL_MODERATE = "MODERATE"
POTENTIAL_HIGH = "HIGH"


@dataclass(frozen=True)
class HailPotentialContract:
    assessment_status: str
    potential_level: str | None
    method_version: str
    source: str | None
    model: str | None
    source_run: str | None
    valid_from: Any
    valid_to: Any
    required_variables: tuple[str, ...]
    missing_variables: tuple[str, ...]
    drivers: tuple[dict, ...]
    data_quality: dict
    derived: dict
    complementary_values: dict | None = None

    def as_dict(self) -> dict:
        return {
            "assessment_status": self.assessment_status,
            "potential_level": self.potential_level,
            "method_version": self.method_version,
            "source": self.source,
            "model": self.model,
            "source_run": self.source_run,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "required_variables": list(self.required_variables),
            "missing_variables": list(self.missing_variables),
            "drivers": list(self.drivers),
            "data_quality": dict(self.data_quality),
            "derived": dict(self.derived),
            "complementary_values": dict(self.complementary_values or {}),
        }


def is_number(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))
