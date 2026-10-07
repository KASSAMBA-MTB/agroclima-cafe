"""
G7.5 — VALIDAÇÃO OPERACIONAL CONTRA RUNs REAIS PERSISTIDOS

Instalar como:
    tools/verify_single_run_forecast_real_g7_5.py

Executar na raiz:
    python ".\tools\verify_single_run_forecast_real_g7_5.py"

Objetivo:
    validar o consumidor operacional HTTP contra os três RUNs reais já
    persistidos no PostgreSQL.

Importante:
    este script NÃO altera o projeto, NÃO altera ALLOWED_HOSTS e NÃO
    cria/atualiza/remove registros.

A validação usa RequestFactory + resolução direta da URL da aplicação,
evitando o HTTPHost testserver do django.test.Client.
Assim a View é exercitada diretamente no ambiente Django real.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agroclima.settings")

import django

django.setup()

import json
from datetime import datetime, timezone
from decimal import Decimal

from django.test import RequestFactory

from clima.models import ClimateForecastRecord, ClimateModelRun
from clima.views import single_run_forecast


SOURCE = "open_meteo_single_runs"
MODEL = "ecmwf_ifs025"
LAT = Decimal("-21.750000")
LON = Decimal("-46.500000")
CELL_SELECTION = "land"

RUNS = [
    datetime(2026, 10, 3, tzinfo=timezone.utc),
    datetime(2026, 4, 2, tzinfo=timezone.utc),
    datetime(2026, 4, 15, tzinfo=timezone.utc),
]

EXPECTED_VARIABLES = {
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
}


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def call_view(run_datetime):
    factory = RequestFactory()

    query = {
        "source": SOURCE,
        "model": MODEL,
        "run_datetime": run_datetime.isoformat(),
        "lat": str(LAT),
        "lon": str(LON),
        "cell_selection": CELL_SELECTION,
    }

    request = factory.get("/clima/single-run/forecast/", data=query)

    return single_run_forecast(request)


print("=" * 78)
print("G7.5 — CONSUMIDOR OPERACIONAL × RUNs REAIS")
print("=" * 78)

for run_datetime in RUNS:
    run = ClimateModelRun.objects.get(
        source=SOURCE,
        model=MODEL,
        run_datetime=run_datetime,
        lat=LAT,
        lon=LON,
        cell_selection=CELL_SELECTION,
    )

    total_records = ClimateForecastRecord.objects.filter(
        model_run=run
    ).count()

    response = call_view(run_datetime)

    print()
    print(f"RUN: {run_datetime.isoformat()}")
    print(f"  model_run_id: {run.id}")
    print(f"  HTTP: {response.status_code}")
    print(f"  DB records: {total_records}")

    assert_true(
        response.status_code == 200,
        f"Consumidor não retornou HTTP 200: {response.status_code}",
    )

    payload = json.loads(response.content.decode("utf-8"))

    assert_true(
        payload["contract_version"] == "1.0",
        "contract_version divergente.",
    )
    assert_true(
        payload["frequency"] == "HOURLY",
        "frequency divergente.",
    )
    assert_true(
        payload["run"]["id"] == run.id,
        "model_run_id divergente.",
    )
    assert_true(
        payload["forecast_count"] == 48,
        f"forecast_count esperado=48, obtido={payload['forecast_count']}.",
    )
    assert_true(
        payload["record_count"] == 672,
        f"record_count esperado=672, obtido={payload['record_count']}.",
    )

    rows = payload["forecast"]

    assert_true(
        len(rows) == 48,
        "Quantidade de timestamps divergente.",
    )

    first_variables = rows[0]["variables"]

    assert_true(
        set(first_variables) == EXPECTED_VARIABLES,
        "Conjunto de 14 variáveis divergente.",
    )

    precipitation = first_variables["precipitation"]

    assert_true(
        precipitation["value_status"] == "MISSING",
        "Precipitação inicial não está MISSING.",
    )
    assert_true(
        precipitation["value"] is None,
        "Precipitação MISSING foi convertida para zero/valor numérico.",
    )

    assert_true(
        len(rows[-1]["variables"]) == 14,
        "Último timestamp não contém 14 variáveis.",
    )

    print("  contract_version: OK")
    print("  frequency: OK")
    print("  provenance/model_run_id: OK")
    print("  48 timestamps: OK")
    print("  672 records: OK")
    print("  14 variables/timestamp: OK")
    print("  precipitation[0]: MISSING/None: OK")
    print("  RESULTADO: APROVADO")

print()
print("=" * 78)
print("RESULTADO FINAL: G7.5 — CONSUMIDOR OPERACIONAL VALIDADO COM RUNs REAIS")
print("=" * 78)
