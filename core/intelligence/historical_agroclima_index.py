"""
IAC histórico — cálculo com controle de completude.
"""

from core.intelligence.agroclima_index import AgroClimaIndex


class HistoricalAgroClimateIndex:
    REQUIRED_FIELDS = (
        "temperature",
        "humidity",
        "precipitation",
        "frost_level",
        "hail_level",
    )

    def __init__(self, engine=None):
        self.engine = engine or AgroClimaIndex()

    def calculate(self, daily_context):
        if not isinstance(daily_context, dict):
            return None

        if any(
            daily_context.get(field) is None
            for field in self.REQUIRED_FIELDS
        ):
            return None

        return self.engine.calculate(
            temperature=daily_context["temperature"],
            humidity=daily_context["humidity"],
            precipitation=daily_context["precipitation"],
            frost_level=daily_context["frost_level"],
            hail_level=daily_context["hail_level"],
        )
