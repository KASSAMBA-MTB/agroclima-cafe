"""
==========================================================
Temperature Indicator
==========================================================
"""

from core.constants.climate import TEMPERATURE_SCORE

from core.intelligence.indicators.base_indicator import BaseIndicator


class TemperatureIndicator(BaseIndicator):

    """
    Calcula o score da temperatura.
    """

    def score(self, temperature):

        for interval, points in TEMPERATURE_SCORE:

            minimum, maximum = interval

            if minimum <= temperature < maximum:

                return points

        return 0