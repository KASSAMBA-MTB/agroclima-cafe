# ARQUIVO: clima/views.py
# TIPO: código Python — substituir o conteúdo atual.
# G7.5 — primeiro consumidor HTTP operacional do contrato Single Run.
#
# Responsabilidade:
# - receber a identidade canônica de um RUN;
# - consultar exclusivamente SingleRunForecastQueryService;
# - devolver o contrato operacional como JSON;
# - não adquirir dados;
# - não calcular indicadores;
# - não alterar persistência;
# - não depender do DashboardService.
#
# A serialização JSON usa o DjangoJSONEncoder, preservando datetime e Decimal
# como representações JSON válidas, sem modificar os tipos no serviço de domínio.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from clima.models import ClimateModelRun
from clima.services.single_run_forecast_query_service import (
    SingleRunForecastQueryService,
)


def _parse_datetime(value: str) -> datetime:
    """Converte ISO-8601 recebido pela URL para datetime timezone-aware."""
    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    result = datetime.fromisoformat(normalized)

    if result.tzinfo is None:
        raise ValueError("run_datetime deve conter timezone.")

    return result


def _parse_decimal(value: str) -> Decimal:
    """Converte coordenada textual sem passar por float."""
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("coordenada inválida.")


@require_GET
def single_run_forecast(request):
    """
    Consumidor HTTP do contrato operacional Single Run.

    Parâmetros obrigatórios:
        source
        model
        run_datetime
        lat
        lon
        cell_selection
    """

    required = (
        "source",
        "model",
        "run_datetime",
        "lat",
        "lon",
        "cell_selection",
    )

    missing = [
        name
        for name in required
        if not request.GET.get(name)
    ]

    if missing:
        return JsonResponse(
            {
                "error": "Parâmetros obrigatórios ausentes.",
                "missing": missing,
            },
            status=400,
            encoder=DjangoJSONEncoder,
        )

    try:
        run_datetime = _parse_datetime(
            request.GET["run_datetime"]
        )
        lat = _parse_decimal(
            request.GET["lat"]
        )
        lon = _parse_decimal(
            request.GET["lon"]
        )
    except ValueError as exc:
        return JsonResponse(
            {
                "error": str(exc),
            },
            status=400,
            encoder=DjangoJSONEncoder,
        )

    try:
        result = SingleRunForecastQueryService().get_forecast(
            source=request.GET["source"],
            model=request.GET["model"],
            run_datetime=run_datetime,
            lat=lat,
            lon=lon,
            cell_selection=request.GET["cell_selection"],
        )
    except ClimateModelRun.DoesNotExist:
        return JsonResponse(
            {
                "error": "RUN não encontrado.",
            },
            status=404,
            encoder=DjangoJSONEncoder,
        )

    return JsonResponse(
        result,
        status=200,
        encoder=DjangoJSONEncoder,
        json_dumps_params={
            "ensure_ascii": False,
            "sort_keys": False,
        },
    )
