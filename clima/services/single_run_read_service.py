"""
G7.5 / G6 — Serviço de leitura da persistência Single Runs.

Arquivo entregue em TXT.
Destino no projeto:
    clima/services/single_run_read_service.py

Responsabilidade:
    Expor leitura somente da persistência canônica ClimateModelRun /
    ClimateForecastRecord, sem aquisição, sem canonicalização, sem
    regras de inteligência e sem dependência do DashboardService.

Contrato:
    - leitura é somente leitura;
    - um RUN é identificado por source + model + run_datetime +
      lat + lon + cell_selection;
    - registros são retornados na ordem forecast_datetime, variable;
    - MISSING permanece com value=None;
    - NUMERIC permanece com seu valor persistido;
    - nenhuma conversão de MISSING para zero;
    - ausência de RUN gera ClimateModelRun.DoesNotExist;
    - o serviço não cria, atualiza ou remove dados.
"""

from django.db.models import QuerySet

from clima.models import ClimateForecastRecord, ClimateModelRun


class SingleRunReadService:
    """Leitura canônica e somente leitura dos Single Runs persistidos."""

    def get_run(
        self,
        *,
        source: str,
        model: str,
        run_datetime,
        lat,
        lon,
        cell_selection: str,
    ) -> ClimateModelRun:
        """
        Retorna exatamente um ModelRun pela identidade canônica.

        Nenhum fallback por data, município ou modelo é aplicado.
        """
        return (
            ClimateModelRun.objects
            .get(
                source=source,
                model=model,
                run_datetime=run_datetime,
                lat=lat,
                lon=lon,
                cell_selection=cell_selection,
            )
        )

    def list_runs(
        self,
        *,
        source: str | None = None,
        model: str | None = None,
    ) -> QuerySet[ClimateModelRun]:
        """
        Lista RUNs persistidos, sem alterar o banco.

        A ordenação é determinística:
            run_datetime DESC, id DESC
        """
        queryset = ClimateModelRun.objects.all()

        if source is not None:
            queryset = queryset.filter(source=source)

        if model is not None:
            queryset = queryset.filter(model=model)

        return queryset.order_by("-run_datetime", "-id")

    def get_records(
        self,
        *,
        model_run: ClimateModelRun,
        variable: str | None = None,
    ) -> QuerySet[ClimateForecastRecord]:
        """
        Retorna os registros canônicos de um RUN.

        A ordenação é determinística por forecast_datetime e variable.
        """
        queryset = (
            ClimateForecastRecord.objects
            .filter(model_run=model_run)
            .order_by("forecast_datetime", "variable")
        )

        if variable is not None:
            queryset = queryset.filter(variable=variable)

        return queryset

    def get_record(
        self,
        *,
        model_run: ClimateModelRun,
        forecast_datetime,
        variable: str,
    ) -> ClimateForecastRecord:
        """Retorna um único registro canônico pela identidade do registro."""
        return (
            ClimateForecastRecord.objects
            .get(
                model_run=model_run,
                forecast_datetime=forecast_datetime,
                variable=variable,
            )
        )

    def get_run_contract(
        self,
        *,
        model_run: ClimateModelRun,
    ) -> dict:
        """
        Expõe um DTO de leitura estável, sem devolver objetos de domínio
        adicionais e sem recalcular qualquer valor.
        """
        records = self.get_records(model_run=model_run)

        return {
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
            "records": [
                {
                    "forecast_datetime": record.forecast_datetime,
                    "variable": record.variable,
                    "unit": record.unit,
                    "value": record.value,
                    "value_status": record.value_status,
                }
                for record in records
            ],
        }
