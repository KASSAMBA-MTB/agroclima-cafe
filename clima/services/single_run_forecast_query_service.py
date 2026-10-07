# ARQUIVO: clima/services/single_run_forecast_query_service.py
# TIPO: código Python — substituir a versão V1.
# FINALIDADE: saída operacional horária de um Single Run persistido.
#
# COMPATIBILIDADE:
# - respeita a assinatura keyword-only do SingleRunDomainService;
# - consome o contrato real "forecasts" produzido pelo domínio;
# - somente organiza a saída;
# - não calcula, agrega, interpola ou altera valores;
# - MISSING permanece value=None;
# - não altera DashboardService, mapa ou frontend.

from __future__ import annotations

from datetime import datetime
from typing import Any

from clima.services.single_run_domain_service import SingleRunDomainService


class SingleRunForecastQueryService:
    """Consulta operacional dos dados horários de um RUN persistido."""

    CONTRACT_VERSION = "1.0"
    FREQUENCY = "HOURLY"

    def __init__(
        self,
        *,
        domain_service: SingleRunDomainService | None = None,
    ) -> None:
        self.domain_service = domain_service or SingleRunDomainService()

    def get_forecast(
        self,
        *,
        source: str,
        model: str,
        run_datetime: datetime,
        lat: float,
        lon: float,
        cell_selection: str,
    ) -> dict[str, Any]:
        """Consulta um RUN pela identidade canônica."""
        context = self.domain_service.get_context(
            source=source,
            model=model,
            run_datetime=run_datetime,
            lat=lat,
            lon=lon,
            cell_selection=cell_selection,
        )
        return self._build_output(context)

    def get_forecast_for_run(self, *, model_run: Any) -> dict[str, Any]:
        """Consulta um ModelRun já resolvido."""
        context = self.domain_service.get_context_for_run(
            model_run=model_run
        )
        return self._build_output(context)

    def _build_output(self, context: dict[str, Any]) -> dict[str, Any]:
        run = context.get("run", {})
        forecasts = context.get("forecasts", [])

        rows: list[dict[str, Any]] = []
        variables: set[str] = set()

        for forecast in forecasts:
            timestamp = forecast.get("forecast_datetime")
            timestamp_variables = forecast.get("variables", {})
            values: dict[str, dict[str, Any]] = {}

            for variable in sorted(timestamp_variables):
                item = timestamp_variables[variable]
                variables.add(variable)

                values[variable] = {
                    "unit": item.get("unit"),
                    "value": item.get("value"),
                    "value_status": item.get("value_status"),
                }

            rows.append(
                {
                    "forecast_datetime": timestamp,
                    "variables": values,
                }
            )

        return {
            "contract_version": self.CONTRACT_VERSION,
            "frequency": self.FREQUENCY,
            "run": {
                "id": run.get("id"),
                "source": run.get("source"),
                "model": run.get("model"),
                "run_datetime": run.get("run_datetime"),
                "lat": run.get("lat"),
                "lon": run.get("lon"),
                "timezone": run.get("timezone"),
                "cell_selection": run.get("cell_selection"),
            },
            "forecast_count": len(rows),
            "record_count": context.get("record_count", 0),
            "variables": sorted(variables),
            "forecast": rows,
        }
