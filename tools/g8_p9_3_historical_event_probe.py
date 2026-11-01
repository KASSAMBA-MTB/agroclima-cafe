#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
G8 / P9.3 — Probe histórica do evento de granizo em Andradas.

OBJETIVO
--------
Verificar se o Historical Forecast API consegue recuperar, para Andradas/MG
e para a data de referência 2025-07-25, as variáveis necessárias ao contrato
meteorológico preliminar de MP-01.11.

IMPORTANTE
----------
- Isto NÃO é Single Run.
- A fonte é o Historical Forecast API.
- A data 2025-07-25 NÃO é atribuída ao relatório EMATER 2025.
  A EMATER confirma ocorrência de granizo em Andradas em 2025, mas não informa
  a data específica. A data usada nesta sonda vem de fonte independente já
  utilizada no levantamento anterior e deve permanecer identificada como tal.
- O script não cria limiares, score, probabilidade ou classificação normativa.
- O script preserva as séries horárias retornadas e calcula somente o
  cisalhamento vetorial 925–500 hPa e CAPE-SHEAR definidos em G8/P7.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROBE_VERSION = "G8-P9.3-0.1"

BASE_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs025"
TIMEZONE = "UTC"
WIND_SPEED_UNIT = "ms"

LATITUDE = -22.0686
LONGITUDE = -46.5724
LOCATION_NAME = "Andradas/MG"

START_DATE = "2025-07-25"
END_DATE = "2025-07-25"

VARIABLES = [
    "cape",
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
]

REQUIRED_FOR_CAPE_SHEAR = [
    "cape",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
]

OUTPUT_DIR = Path("reports")
OUTPUT_FILE = OUTPUT_DIR / "G8_P9_3_historical_andradas_20250725.txt"


def build_url() -> str:
    params = {
        "latitude": str(LATITUDE),
        "longitude": str(LONGITUDE),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(VARIABLES),
        "models": MODEL,
        "timezone": TIMEZONE,
        "wind_speed_unit": WIND_SPEED_UNIT,
    }
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgroClimaCafe-G8-P9.3/0.1",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        status = response.status
        payload = json.loads(response.read().decode("utf-8"))
    return status, payload


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def vector_components(speed_ms: float, direction_deg: float) -> tuple[float, float]:
    """
    Convenção meteorológica:
    direção = de onde o vento sopra, em graus a partir do norte.
    u = speed * sin(direction)
    v = speed * cos(direction)
    """
    radians = math.radians(direction_deg)
    u = speed_ms * math.sin(radians)
    v = speed_ms * math.cos(radians)
    return u, v


def calculate_shear(
    speed_925: float,
    direction_925: float,
    speed_500: float,
    direction_500: float,
) -> tuple[float, float, float, float, float]:
    u925, v925 = vector_components(speed_925, direction_925)
    u500, v500 = vector_components(speed_500, direction_500)
    du = u500 - u925
    dv = v500 - v925
    shear = math.sqrt(du * du + dv * dv)
    return u925, v925, u500, v500, shear


def fmt(value, decimals: int = 3) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def write_report(status_code: int, data: dict | None, error: str | None, url: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("G8 / P9.3 — HISTORICAL FORECAST / ANDRADAS / 2025-07-25")
    lines.append("=" * 100)
    lines.append(f"PROBE_VERSION: {PROBE_VERSION}")
    lines.append(f"EXECUTED_AT_UTC: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("IDENTIDADE DA CONSULTA")
    lines.append(f"LOCATION: {LOCATION_NAME}")
    lines.append(f"LATITUDE: {LATITUDE}")
    lines.append(f"LONGITUDE: {LONGITUDE}")
    lines.append(f"DATE: {START_DATE} -> {END_DATE}")
    lines.append(f"MODEL_REQUESTED: {MODEL}")
    lines.append(f"TIMEZONE: {TIMEZONE}")
    lines.append(f"WIND_SPEED_UNIT: {WIND_SPEED_UNIT}")
    lines.append("DATASET: HISTORICAL_FORECAST_API")
    lines.append("")
    lines.append("PROVENIÊNCIA DO EVENTO")
    lines.append("EMATER-MG 2025: confirma ocorrência de granizo em Andradas em 2025,")
    lines.append("com 204,0 ha afetados, sendo 200 ha de café e 4 ha de olericultura.")
    lines.append("O relatório EMATER não informa a data específica do evento.")
    lines.append("A data 2025-07-25 usada nesta sonda vem de fonte independente anterior")
    lines.append("ao relatório EMATER e não deve ser atribuída à EMATER.")
    lines.append("")
    lines.append("URL DA CONSULTA")
    lines.append(url)
    lines.append("")
    lines.append("RESULTADO HTTP")
    lines.append(f"HTTP_STATUS: {status_code}")

    if error:
        lines.append(f"ERROR: {error}")
        lines.append("")
        lines.append("DECISÃO P9.3: NÃO CONCLUSIVA — a consulta histórica não retornou")
        lines.append("um conjunto de dados utilizável. Não criar regra nem limiar.")
        OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    if not isinstance(data, dict):
        lines.append("ERROR: resposta JSON não é objeto.")
        OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("")
    lines.append("METADADOS RETORNADOS")
    for key in [
        "latitude",
        "longitude",
        "elevation",
        "timezone",
        "timezone_abbreviation",
        "utc_offset_seconds",
        "generationtime_ms",
        "model",
    ]:
        if key in data:
            lines.append(f"{key}: {data[key]}")

    hourly = data.get("hourly")
    units = data.get("hourly_units", {})

    lines.append("")
    lines.append("UNIDADES RETORNADAS")
    if isinstance(units, dict):
        for variable in VARIABLES:
            lines.append(f"{variable}: {units.get(variable, 'NAO_INFORMADO')}")

    if not isinstance(hourly, dict) or "time" not in hourly:
        lines.append("")
        lines.append("ERRO_CONTRATO: bloco hourly ausente ou sem time.")
        lines.append("DECISÃO P9.3: NÃO CONCLUSIVA.")
        OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    times = hourly.get("time", [])
    count = len(times)

    lines.append("")
    lines.append("COBERTURA HORÁRIA")
    lines.append(f"TIMESTAMP_COUNT: {count}")
    if times:
        lines.append(f"FIRST_TIMESTAMP: {times[0]}")
        lines.append(f"LAST_TIMESTAMP: {times[-1]}")

    lines.append("")
    lines.append("COMPLETUDE POR VARIÁVEL")
    completeness: dict[str, tuple[int, int]] = {}
    for variable in VARIABLES:
        values = hourly.get(variable, [])
        valid = sum(1 for value in values if is_number(value))
        nulls = len(values) - valid
        completeness[variable] = (valid, nulls)
        lines.append(
            f"{variable}: count={len(values)} valid={valid} null={nulls}"
        )

    lines.append("")
    lines.append("SÉRIE HORÁRIA + DERIVAÇÕES G8/P7")
    header = (
        "timestamp | cape | wet_bulb_2m | temp_850 | rh_850 | "
        "wind925_ms | dir925_deg | wind500_ms | dir500_deg | "
        "shear_925_500_ms | cape_shear"
    )
    lines.append(header)
    lines.append("-" * len(header))

    rows_with_shear = 0

    for i, timestamp in enumerate(times):
        values = {
            variable: (
                hourly.get(variable, [None] * count)[i]
                if i < len(hourly.get(variable, []))
                else None
            )
            for variable in VARIABLES
        }

        shear = None
        cape_shear = None

        mandatory_ok = all(is_number(values[var]) for var in REQUIRED_FOR_CAPE_SHEAR)
        if mandatory_ok:
            _, _, _, _, shear = calculate_shear(
                float(values["wind_speed_925hPa"]),
                float(values["wind_direction_925hPa"]),
                float(values["wind_speed_500hPa"]),
                float(values["wind_direction_500hPa"]),
            )
            cape_shear = float(values["cape"]) * shear
            rows_with_shear += 1

        lines.append(
            f"{timestamp} | "
            f"{fmt(values['cape'])} | "
            f"{fmt(values['wet_bulb_temperature_2m'])} | "
            f"{fmt(values['temperature_850hPa'])} | "
            f"{fmt(values['relative_humidity_850hPa'])} | "
            f"{fmt(values['wind_speed_925hPa'])} | "
            f"{fmt(values['wind_direction_925hPa'])} | "
            f"{fmt(values['wind_speed_500hPa'])} | "
            f"{fmt(values['wind_direction_500hPa'])} | "
            f"{fmt(shear)} | "
            f"{fmt(cape_shear)}"
        )

    lines.append("")
    lines.append("VALIDAÇÃO P9.3")
    lines.append(f"ROWS_WITH_CAPE_SHEAR: {rows_with_shear}")
    lines.append(f"TOTAL_ROWS: {count}")

    all_required_complete = all(
        completeness[var][0] == count and count > 0
        for var in REQUIRED_FOR_CAPE_SHEAR
    )

    if count == 0:
        decision = "NÃO CONCLUSIVA — nenhuma observação horária retornada."
    elif all_required_complete:
        decision = (
            "EVIDÊNCIA DISPONÍVEL — Historical Forecast retornou o conjunto "
            "mínimo necessário para reproduzir G8/P7 no período consultado."
        )
    else:
        decision = (
            "EVIDÊNCIA PARCIAL — faltam valores em uma ou mais variáveis "
            "obrigatórias para CAPE-SHEAR."
        )

    lines.append(f"DECISÃO_P9_3: {decision}")
    lines.append("")
    lines.append("RESTRIÇÕES")
    lines.append("- Não interpretar CAPE-SHEAR como probabilidade de granizo.")
    lines.append("- Não aplicar thresholds de NONE/LOW/MODERATE/HIGH.")
    lines.append("- Não declarar ocorrência de granizo a partir desta série.")
    lines.append("- Não misturar esta série com Single Runs.")
    lines.append("- Não alterar código de produção nesta etapa.")
    lines.append("")
    lines.append("RAW_RESPONSE_METADATA")
    safe_meta = {
        key: data.get(key)
        for key in data.keys()
        if key not in {"hourly", "hourly_units"}
    }
    lines.append(json.dumps(safe_meta, ensure_ascii=False, indent=2, default=str))

    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    url = build_url()
    print("=" * 80)
    print("G8 / P9.3 — HISTORICAL FORECAST / ANDRADAS / 2025-07-25")
    print("=" * 80)
    print(f"Endpoint: {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"Date: {START_DATE}")
    print(f"Output: {OUTPUT_FILE}")

    try:
        status, data = fetch_json(url)
        write_report(status, data, None, url)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        error = f"HTTPError {exc.code}: {exc.reason}; body={body[:2000]}"
        write_report(exc.code, None, error, url)
        print(error, file=sys.stderr)
        print(f"Relatório: {OUTPUT_FILE}")
        return 2
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        write_report(0, None, error, url)
        print(error, file=sys.stderr)
        print(f"Relatório: {OUTPUT_FILE}")
        return 3

    print("Consulta concluída.")
    print(f"Relatório gerado: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
