"""
==========================================================
Frost Indicator
==========================================================
"""

from core.constants.climate import FROST_SCORE

from core.intelligence.indicators.base_indicator import BaseIndicator


class FrostIndicator(BaseIndicator):

    def score(self, level):

        return FROST_SCORE.get(level, 0)