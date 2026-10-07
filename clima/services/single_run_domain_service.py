"""
G7.5 / G6 — Contexto de domínio para leitura dos Single Runs.

Destino:
    clima/services/single_run_domain_service.py

Responsabilidade:
    Consumir exclusivamente o SingleRunReadService e transformar a
    persistência canônica em um contexto climático estruturado para as
    próximas camadas do domínio.

Limites:
    - não realiza aquisição;
    - não acessa a API;
    - não persiste;
    - não recalcula valores;
    - não executa inteligência;
    - não depende do DashboardService;
    - não converte MISSING em zero;
    - mantém unidade e value_status canônicos.
"""

from clima.models import ClimateModelRun
from clima.services.single_run_read_service import SingleRunReadService


class SingleRunDomainService:
    """Transforma a leitura canônica em contexto estruturado de domínio."""

    def __init__(self, *, read_service=None):
        self.read_service = read_service or SingleRunReadService()

    def get_context(
        self,
        *,
        source,
        model,
        run_datetime,
        lat,
        lon,
        cell_selection,
    ):
        """Retorna o contexto estruturado de um RUN pela identidade canônica."""
        model_run = self.read_service.get_run(
            source=source,
            model=model,
            run_datetime=run_datetime,
            lat=lat,
            lon=lon,
            cell_selection=cell_selection,
        )
        return self._build_context(model_run)

    def get_context_for_run(self, *, model_run):
        """Constrói o contexto a partir de um ModelRun já resolvido."""
        return self._build_context(model_run)

    def _build_context(self, model_run):
        records = self.read_service.get_records(model_run=model_run)

        forecasts = {}
        for record in records:
            timestamp = record.forecast_datetime
            forecast = forecasts.setdefault(
                timestamp,
                {
                    "forecast_datetime": timestamp,
                    "variables": {},
                },
            )

            forecast["variables"][record.variable] = {
                "unit": record.unit,
                "value": record.value,
                "value_status": record.value_status,
            }

        ordered_forecasts = [
            forecasts[timestamp]
            for timestamp in sorted(forecasts)
        ]

        return {
            "run": {
                "id": model_run.id,
                "source": model_run.source,
                "model": model_run.model,
                "run_datetime": model_run.run_datetime,
                "lat": model_run.lat,
                "lon": model_run.lon,
                "timezone": model_run.timezone,
                "cell_selection": model_run.cell_selection,
                "requested_lat": model_run.requested_lat,
                "requested_lon": model_run.requested_lon,
                "elevation": model_run.elevation,
                "raw_path": model_run.raw_path,
                "raw_sha256": model_run.raw_sha256,
                "content_sha256": model_run.content_sha256,
                "ingested_at": model_run.ingested_at,
            },
            "forecast_count": len(ordered_forecasts),
            "record_count": sum(
                len(forecast["variables"])
                for forecast in ordered_forecasts
            ),
            "forecasts": ordered_forecasts,
        }
