"""
Classificador de potencial de granizo.

Classificações produzidas por este módulo não são homologadas.
A homologação depende de decisão verificável do HailHomologationGate.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Optional


NOT_CONFIGURED = "NOT_CONFIGURED"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
CLASSIFIED = "CLASSIFIED"
NOT_CLASSIFIED_OUT_OF_RANGE = "NOT_CLASSIFIED_OUT_OF_RANGE"


@dataclass(frozen=True)
class HailPotentialClassification:
    status: str
    potential_level: Optional[str]
    homologated: bool
    thresholds_version: Optional[str]
    thresholds_source: Optional[str]
    cape: Optional[float]
    shear_925_500: Optional[float]
    reason: str

    def as_dict(self):
        return {
            "classification_status": self.status,
            "potential_level": self.potential_level,
            "homologated": self.homologated,
            "thresholds_version": self.thresholds_version,
            "thresholds_source": self.thresholds_source,
            "cape": self.cape,
            "shear_925_500": self.shear_925_500,
            "reason": self.reason,
        }


class HailPotentialClassifier:
    """
    Classificador backend experimental.

    Nunca declara homologação por configuração.
    HOMOLOGATED depende exclusivamente do Gate científico.
    """

    def __init__(self, configuration=None):
        self.configuration = configuration

    @staticmethod
    def _number(value):
        if value is None or isinstance(value, bool):
            return None

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None

        return number if isfinite(number) else None

    def classify(self, cape, shear_925_500):
        cape_value = self._number(cape)
        shear_value = self._number(shear_925_500)

        config = self.configuration

        if not isinstance(config, dict):
            return self._result(
                NOT_CONFIGURED, None, False, None, None,
                cape_value, shear_value,
                "Conjunto de limiares inexistente.",
            )

        version = config.get("version")
        source = config.get("source")
        levels = config.get("levels")

        if (
            not version
            or not source
            or not isinstance(levels, list)
            or not levels
        ):
            return self._result(
                NOT_CONFIGURED, None, False, version, source,
                cape_value, shear_value,
                "Conjunto de limiares incompleto.",
            )

        if cape_value is None or shear_value is None:
            return self._result(
                INSUFFICIENT_DATA, None, False, version, source,
                cape_value, shear_value,
                "CAPE ou cisalhamento indisponível ou inválido.",
            )

        matching_levels = []

        for level in levels:
            if not isinstance(level, dict):
                continue

            name = level.get("name")
            cape_min = self._number(level.get("cape_min"))
            shear_min = self._number(level.get("shear_min"))

            if (
                name
                and cape_min is not None
                and shear_min is not None
                and cape_value >= cape_min
                and shear_value >= shear_min
            ):
                matching_levels.append(
                    (cape_min + shear_min, cape_min, shear_min, str(name))
                )

        if matching_levels:
            # Seleciona a faixa mais restritiva entre as correspondentes.
            _, _, _, selected_level = max(matching_levels)

            return self._result(
                CLASSIFIED,
                selected_level,
                False,
                version,
                source,
                cape_value,
                shear_value,
                "Classificação experimental; homologação não autorizada.",
            )

        return self._result(
            NOT_CLASSIFIED_OUT_OF_RANGE,
            None,
            False,
            version,
            source,
            cape_value,
            shear_value,
            "Dados fora das faixas configuradas; nenhum nível atribuído.",
        )

    @staticmethod
    def _result(
        status,
        level,
        homologated,
        version,
        source,
        cape,
        shear,
        reason,
    ):
        return HailPotentialClassification(
            status=status,
            potential_level=level,
            homologated=homologated,
            thresholds_version=version,
            thresholds_source=source,
            cape=cape,
            shear_925_500=shear,
            reason=reason,
        )
