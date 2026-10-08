"""
G7.6 — Adaptador controlado do contexto Single Run para indicadores.

Responsabilidade:
    Expor integralmente as 14 séries horárias do contrato canônico Single Run
    aos consumidores de indicadores, preservando valor, status, unidade e
    timestamp.

Limites:
    - não acessa ORM;
    - não acessa API;
    - não persiste;
    - não calcula indicadores;
    - não altera DashboardService;
    - não executa inteligência;
    - não converte MISSING em zero;
    - não cria ETo;
    - preserva value_status e unidades.
"""


class SingleRunIndicatorAdapter:
    """Adapta contexto canônico para consumo de indicadores."""

    VARIABLES = (
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_direction_10m",
        "pressure_msl",
        "surface_pressure",
        "cape",
        "temperature_850hPa",
        "relative_humidity_850hPa",
        "geopotential_height_850hPa",
        "temperature_500hPa",
        "geopotential_height_500hPa",
    )

    def build_series(self, context):
        """Extrai as 14 séries canônicas sem produzir valores derivados."""
        context = context or {}
        forecasts = context.get("forecasts") or []

        series = {
            variable: {
                "timestamps": [],
                "values": [],
                "statuses": [],
                "units": [],
            }
            for variable in self.VARIABLES
        }

        for forecast in forecasts:
            timestamp = forecast.get("forecast_datetime")
            variables = forecast.get("variables") or {}

            for variable in self.VARIABLES:
                item = variables.get(variable)
                if item is None:
                    continue

                series[variable]["timestamps"].append(timestamp)
                series[variable]["values"].append(item.get("value"))
                series[variable]["statuses"].append(
                    item.get("value_status")
                )
                series[variable]["units"].append(item.get("unit"))

        return {
            "run": context.get("run"),
            "series": series,
            "forecast_count": context.get("forecast_count", 0),
            "record_count": context.get("record_count", 0),
        }

    def build_indicator_input(self, context):
        """
        Expõe integralmente as séries canônicas aos indicadores.

        O campo ``series`` contém as 14 variáveis exatamente na forma
        produzida por ``build_series``. Os aliases históricos em português
        permanecem para compatibilidade dos consumidores já existentes.

        Nenhuma média, soma, classificação ou interpretação é realizada aqui.
        """
        adapted = self.build_series(context)
        series = adapted["series"]

        return {
            "run": adapted["run"],
            "series": {
                variable: {
                    "timestamps": list(series[variable]["timestamps"]),
                    "values": list(series[variable]["values"]),
                    "statuses": list(series[variable]["statuses"]),
                    "units": list(series[variable]["units"]),
                }
                for variable in self.VARIABLES
            },
            "dias": list(series["temperature_2m"]["timestamps"]),
            "temperatura": list(series["temperature_2m"]["values"]),
            "temperatura_status": list(
                series["temperature_2m"]["statuses"]
            ),
            "precipitacao": list(series["precipitation"]["values"]),
            "precipitacao_status": list(
                series["precipitation"]["statuses"]
            ),
            "eto_mm_day": [],
            "eto_status": [],
            "units": {
                variable: self._first_unit(series[variable])
                for variable in self.VARIABLES
            },
            "forecast_count": adapted["forecast_count"],
            "record_count": adapted["record_count"],
        }

    @staticmethod
    def _first_unit(series):
        units = series.get("units") or []
        return units[0] if units else None
