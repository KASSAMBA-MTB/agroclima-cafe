"""
==========================================================
Precipitation Indicator
==========================================================
"""

from core.constants.climate import PRECIPITATION_SCORE

from core.intelligence.indicators.base_indicator import BaseIndicator


class PrecipitationIndicator(BaseIndicator):

    def score(self, precipitation):

        for interval, points in PRECIPITATION_SCORE:

            minimum, maximum = interval

            if minimum <= precipitation < maximum:

                return points

        return 0