"""
==========================================================
Hail Indicator
==========================================================
"""

from core.constants.climate import HAIL_SCORE

from core.intelligence.indicators.base_indicator import BaseIndicator


class HailIndicator(BaseIndicator):

    def score(self, level):

        return HAIL_SCORE.get(level, 0)