"""
==========================================================
Humidity Indicator
==========================================================
"""

from core.constants.climate import HUMIDITY_SCORE

from core.intelligence.indicators.base_indicator import BaseIndicator


class HumidityIndicator(BaseIndicator):

    def score(self, humidity):

        for interval, points in HUMIDITY_SCORE:

            minimum, maximum = interval

            if minimum <= humidity < maximum:

                return points

        return 0