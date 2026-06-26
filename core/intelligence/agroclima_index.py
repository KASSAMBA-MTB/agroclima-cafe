"""
==========================================================
AgroClima Café

AgroClima Index (IAC)

Motor responsável pelo cálculo do Índice AgroClima.

Versão: 1.0

Autor:
Walter Junio Pontes Teixeira

==========================================================
"""

from core.constants.climate import (
    TEMPERATURE_WEIGHT,
    HUMIDITY_WEIGHT,
    PRECIPITATION_WEIGHT,
    FROST_WEIGHT,
    HAIL_WEIGHT,
    IAC_LEVELS,
    IAC_COLORS,
    IAC_ICONS,
)

from core.intelligence.indicators import (
    TemperatureIndicator,
    HumidityIndicator,
    PrecipitationIndicator,
    FrostIndicator,
    HailIndicator,
)


class AgroClimaIndex:
    """
    Calcula o Índice AgroClima (IAC).

    O índice varia entre 0 e 100.
    """

    def __init__(self):

        self.temperature = TemperatureIndicator()

        self.humidity = HumidityIndicator()

        self.precipitation = PrecipitationIndicator()

        self.frost = FrostIndicator()

        self.hail = HailIndicator()

    def calculate(
        self,
        temperature,
        humidity,
        precipitation,
        frost_level,
        hail_level,
    ):

        temperature_score = self.temperature.score(temperature)

        humidity_score = self.humidity.score(humidity)

        precipitation_score = self.precipitation.score(
            precipitation
        )

        frost_score = self.frost.score(frost_level)

        hail_score = self.hail.score(hail_level)

        index = (

            temperature_score * TEMPERATURE_WEIGHT

            + humidity_score * HUMIDITY_WEIGHT

            + precipitation_score * PRECIPITATION_WEIGHT

            + frost_score * FROST_WEIGHT

            + hail_score * HAIL_WEIGHT

        )

        index = round(index, 1)

        classification = self._classification(index)

        return {

            "index": index,

            "classification": classification,

            "color": IAC_COLORS[classification],

            "icon": IAC_ICONS[classification],

            "scores": {

                "temperature": temperature_score,

                "humidity": humidity_score,

                "precipitation": precipitation_score,

                "frost": frost_score,

                "hail": hail_score,

            }

        }

    def _classification(self, value):

        for minimum, maximum, level in IAC_LEVELS:

            if minimum <= value <= maximum:

                return level

        return "Crítico"