"""
G7.4 / P9 — REGRESSÃO CONTROLADA

ARQUIVO OPERACIONAL:
ARQUIVO OPERACIONAL: tools/g74_p0_probe.py

BASE:
    G7.4/P8 — INTEGRAÇÃO CONTROLADA VALIDADA

OBJETIVO
--------
Reexecutar o fluxo P8 e verificar regressão dos contratos já homologados.

FLUXO:
    API -> RAW -> CANONICAL_STAGING -> VALIDATION -> REGRESSION

P9 não cria indicadores, regras de inteligência ou integração Django.

CRITÉRIOS:
- IFS025 permanece autoridade;
- 3 RUNs de controle;
- 48 timestamps por RUN;
- 14 variáveis;
- 672 registros canônicos por RUN;
- precipitation[0] permanece MISSING;
- valores numéricos preservados;
- RAW preservado;
- staging válido;
- HRES somente comparação;
- nenhum código Django é alterado.

A única correção em relação ao P8 é a eliminação da SyntaxWarning do
docstring; não existe alteração funcional decorrente disso.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "raw" / "g74_p0"
REPORT_DIR = BASE_DIR / "reports" / "g74_p0"
STAGING_DIR = RAW_DIR / "canonical_staging"

SINGLE_RUN_URL = "https://single-runs-api.open-meteo.com/v1/forecast"

LATITUDE = -21.7874
LONGITUDE = -46.5614
TIMEZONE = "GMT"
CELL_SELECTION = "land"

MODEL_IFS025 = "ecmwf_ifs025"
MODEL_HRES = "ecmwf_ifs"

RUNS = [
    "2026-04-02T00:00",
    "2026-04-15T00:00",
    "2026-10-03T00:00",
]

VARIABLES = [
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
]

EXPECTED_UNITS = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "dew_point_2m": "°C",
    "precipitation": "mm",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "°",
    "pressure_msl": "hPa",
    "surface_pressure": "hPa",
    "cape": "J/kg",
    "temperature_850hPa": "°C",
    "relative_humidity_850hPa": "%",
    "geopotential_height_850hPa": "m",
    "temperature_500hPa": "°C",
    "geopotential_height_500hPa": "m",
}

FORECAST_DAYS = 2
EXPECTED_TIMESTAMPS = 48
EXPECTED_RECORDS = len(VARIABLES) * EXPECTED_TIMESTAMPS
REQUEST_TIMEOUT = 60


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_params(model: str, run: str) -> dict[str, str]:
    return {
        "latitude": str(LATITUDE),
        "longitude": str(LONGITUDE),
        "timezone": TIMEZONE,
        "cell_selection": CELL_SELECTION,
        "models": model,
        "hourly": ",".join(VARIABLES),
        "forecast_days": str(FORECAST_DAYS),
        "run": run,
    }


def request_json(
    params: dict[str, str],
) -> tuple[int, dict | None, str | None, str]:
    query = urllib.parse.urlencode(params)
    full_url = f"{SINGLE_RUN_URL}?{query}"

    request = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "AgroClimaCafe-G7.4-P9/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), None, full_url

    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(exc)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None

        return (
            exc.code,
            payload,
            f"HTTPError {exc.code}: {body[:2000]}",
            full_url,
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return (
            0,
            None,
            f"{type(exc).__name__}: {exc}",
            full_url,
        )


def is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def parse_timestamp(value: str) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def save_raw(
    model: str,
    run: str,
    status: int,
    params: dict[str, str],
    url: str,
    payload: dict | None,
    error: str | None,
) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DIR / (
        f"p9_{model}_{run.replace('-', '').replace(':', '')}_"
        f"{utc_stamp()}.json"
    )

    path.write_text(
        json.dumps(
            {
                "protocol": "G7.4/P9",
                "model": model,
                "run": run,
                "http_status": status,
                "request": {
                    "endpoint": SINGLE_RUN_URL,
                    "params": params,
                    "url": url,
                },
                "error": error,
                "payload": payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def canonical_record(
    run: str,
    forecast_datetime: str,
    variable: str,
    unit: str,
    value,
) -> dict:
    status = "NUMERIC" if is_number(value) else "MISSING"

    return {
        "source": "Open-Meteo Single Runs API",
        "model": MODEL_IFS025,
        "run_datetime": run,
        "forecast_datetime": forecast_datetime,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "cell_selection": CELL_SELECTION,
        "variable": variable,
        "unit": unit,
        "value": value if status == "NUMERIC" else None,
        "value_status": status,
    }


def build_staging(
    run: str,
    payload: dict,
) -> tuple[list[dict], list[str]]:
    errors = []
    records = []

    hourly = payload.get("hourly")
    units = payload.get("hourly_units")

    if not isinstance(hourly, dict):
        return [], ["hourly ausente"]

    if not isinstance(units, dict):
        return [], ["hourly_units ausente"]

    times = hourly.get("time")

    if not isinstance(times, list):
        return [], ["time ausente"]

    if len(times) != EXPECTED_TIMESTAMPS:
        errors.append(
            f"timestamps={len(times)} != {EXPECTED_TIMESTAMPS}"
        )

    parsed_times = [parse_timestamp(value) for value in times]

    if any(value is None for value in parsed_times):
        errors.append("timestamp não parseável")

    if len(parsed_times) != len(set(parsed_times)):
        errors.append("timestamps duplicados")

    if any(
        right <= left
        for left, right in zip(parsed_times, parsed_times[1:])
        if left is not None and right is not None
    ):
        errors.append("timestamps fora de ordem")

    for variable in VARIABLES:
        values = hourly.get(variable)
        unit = units.get(variable)

        if not isinstance(values, list):
            errors.append(f"{variable}: série ausente")
            continue

        if unit != EXPECTED_UNITS[variable]:
            errors.append(
                f"{variable}: unidade {unit!r} "
                f"!= {EXPECTED_UNITS[variable]!r}"
            )

        if len(values) != len(times):
            errors.append(
                f"{variable}: quantidade divergente"
            )
            continue

        for timestamp, value in zip(times, values):
            records.append(
                canonical_record(
                    run=run,
                    forecast_datetime=timestamp,
                    variable=variable,
                    unit=unit,
                    value=value,
                )
            )

    return records, errors


def validate_records(
    run: str,
    records: list[dict],
) -> list[str]:
    errors = []

    if len(records) != EXPECTED_RECORDS:
        errors.append(
            f"records={len(records)} != {EXPECTED_RECORDS}"
        )

    for record in records:
        required = {
            "source",
            "model",
            "run_datetime",
            "forecast_datetime",
            "latitude",
            "longitude",
            "timezone",
            "cell_selection",
            "variable",
            "unit",
            "value",
            "value_status",
        }

        missing = required.difference(record)

        if missing:
            errors.append(
                f"campos ausentes: {sorted(missing)}"
            )
            continue

        if record["model"] != MODEL_IFS025:
            errors.append("modelo divergente")

        if record["run_datetime"] != run:
            errors.append("run_datetime divergente")

        if parse_timestamp(record["run_datetime"]) is None:
            errors.append("run_datetime inválido")

        if parse_timestamp(record["forecast_datetime"]) is None:
            errors.append("forecast_datetime inválido")

        variable = record["variable"]

        if variable not in VARIABLES:
            errors.append(
                f"variável fora do contrato: {variable}"
            )
            continue

        if record["unit"] != EXPECTED_UNITS[variable]:
            errors.append(
                f"unidade divergente: {variable}"
            )

        status = record["value_status"]

        if status not in {"NUMERIC", "MISSING"}:
            errors.append(
                f"value_status inválido: {variable}"
            )

        if status == "NUMERIC" and not is_number(record["value"]):
            errors.append(
                f"NUMERIC sem valor: {variable}"
            )

        if status == "MISSING" and record["value"] is not None:
            errors.append(
                f"MISSING convertido: {variable}"
            )

    precipitation = [
        record
        for record in records
        if record["variable"] == "precipitation"
    ]

    if len(precipitation) != EXPECTED_TIMESTAMPS:
        errors.append("precipitation incompleta")
    elif precipitation[0]["value_status"] != "MISSING":
        errors.append("precipitation[0] não é MISSING")
    elif precipitation[0]["value"] is not None:
        errors.append("precipitation[0] contém valor")

    return errors


def validate_roundtrip(
    payload: dict,
    records: list[dict],
) -> list[str]:
    errors = []

    hourly = payload.get("hourly", {})
    units = payload.get("hourly_units", {})
    times = hourly.get("time", [])

    if len(records) != len(VARIABLES) * len(times):
        errors.append("quantidade RAW/STAGING divergente")

    for variable in VARIABLES:
        source = hourly.get(variable, [])
        staged = [
            record
            for record in records
            if record["variable"] == variable
        ]

        if len(source) != len(staged):
            errors.append(
                f"{variable}: quantidade alterada"
            )
            continue

        for index, (source_value, record) in enumerate(
            zip(source, staged)
        ):
            expected_status = (
                "NUMERIC"
                if is_number(source_value)
                else "MISSING"
            )

            if record["forecast_datetime"] != times[index]:
                errors.append(
                    f"{variable}[{index}]: timestamp alterado"
                )

            if record["unit"] != units.get(variable):
                errors.append(
                    f"{variable}[{index}]: unidade alterada"
                )

            if record["value_status"] != expected_status:
                errors.append(
                    f"{variable}[{index}]: status alterado"
                )

            if expected_status == "NUMERIC":
                if record["value"] != source_value:
                    errors.append(
                        f"{variable}[{index}]: valor alterado"
                    )
            elif record["value"] is not None:
                errors.append(
                    f"{variable}[{index}]: MISSING convertido"
                )

    return errors


def save_staging(
    run: str,
    records: list[dict],
) -> Path:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    path = STAGING_DIR / (
        f"regression_{MODEL_IFS025}_"
        f"{run.replace('-', '').replace(':', '')}_"
        f"{utc_stamp()}.json"
    )

    path.write_text(
        json.dumps(
            {
                "protocol": "G7.4/P9",
                "model": MODEL_IFS025,
                "run_datetime": run,
                "record_count": len(records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def check_previous_reports() -> dict:
    p7 = sorted(
        REPORT_DIR.glob("p7_contract_validation_*.json")
    )
    p8 = sorted(
        REPORT_DIR.glob("p8_controlled_integration_*.json")
    )

    return {
        "p7_report_present": bool(p7),
        "p8_report_present": bool(p8),
        "latest_p7": (
            str(p7[-1].relative_to(BASE_DIR))
            if p7 else None
        ),
        "latest_p8": (
            str(p8[-1].relative_to(BASE_DIR))
            if p8 else None
        ),
    }


def run_authority() -> list[dict]:
    decisions = []

    for run in RUNS:
        print(f"RUN {run}")
        print("[IFS025] regressão...")

        params = build_params(MODEL_IFS025, run)
        status, payload, error, url = request_json(params)

        raw_path = save_raw(
            MODEL_IFS025,
            run,
            status,
            params,
            url,
            payload,
            error,
        )

        print(
            f"  HTTP: {status} | "
            f"{'COBERTURA_COMPROVADA' if status == 200 else 'ERRO'}"
        )

        if status != 200 or not isinstance(payload, dict):
            decisions.append({
                "run": run,
                "valid": False,
                "errors": [error or "payload inválido"],
                "raw_file": str(raw_path.relative_to(BASE_DIR)),
            })
            print()
            continue

        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])

        print(
            f"  timestamps: {len(times)} | "
            f"primeiro: {times[0] if times else None} | "
            f"último: {times[-1] if times else None}"
        )

        records, build_errors = build_staging(
            run,
            payload,
        )

        validation_errors = validate_records(
            run,
            records,
        )

        roundtrip_errors = validate_roundtrip(
            payload,
            records,
        )

        all_errors = (
            build_errors
            + validation_errors
            + roundtrip_errors
        )

        staging_path = save_staging(
            run,
            records,
        )

        valid = not all_errors

        decisions.append({
            "run": run,
            "valid": valid,
            "http_status": status,
            "record_count": len(records),
            "expected_record_count": EXPECTED_RECORDS,
            "raw_file": str(raw_path.relative_to(BASE_DIR)),
            "staging_file": str(
                staging_path.relative_to(BASE_DIR)
            ),
            "errors": all_errors,
        })

        print(
            f"  registros canônicos: {len(records)}"
        )
        print(
            f"  staging/regressão: "
            f"{'VALIDADO' if valid else 'REPROVADO'}"
        )

        precipitation = [
            record
            for record in records
            if record["variable"] == "precipitation"
        ]

        if precipitation:
            print(
                "  precipitation[0]: "
                f"{precipitation[0]['value_status']} "
                f"value={precipitation[0]['value']!r}"
            )

        print()

    return decisions


def run_hres() -> list[dict]:
    results = []

    for run in RUNS:
        params = build_params(MODEL_HRES, run)
        status, payload, error, url = request_json(params)

        raw_path = save_raw(
            MODEL_HRES,
            run,
            status,
            params,
            url,
            payload,
            error,
        )

        results.append({
            "run": run,
            "http_status": status,
            "status": (
                "COBERTURA_COMPROVADA"
                if status == 200 and isinstance(payload, dict)
                else "ERRO"
            ),
            "raw_file": str(raw_path.relative_to(BASE_DIR)),
        })

    return results


def write_report(
    decisions: list[dict],
    hres: list[dict],
    previous: dict,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    generated = utc_stamp()

    regression_valid = (
        len(decisions) == len(RUNS)
        and all(
            item["valid"]
            for item in decisions
        )
        and previous["p7_report_present"]
        and previous["p8_report_present"]
    )

    classification = (
        "P9_REGRESSAO_CONTROLADA_VALIDADA"
        if regression_valid
        else "P9_REGRESSAO_CONTROLADA_REPROVADA"
    )

    report = {
        "protocol": "G7.4/P9",
        "generated_at_utc": generated,
        "classification": classification,
        "authority_model": MODEL_IFS025,
        "comparison_model": MODEL_HRES,
        "runs": RUNS,
        "variables": VARIABLES,
        "expected_units": EXPECTED_UNITS,
        "expected_timestamps": EXPECTED_TIMESTAMPS,
        "expected_records_per_run": EXPECTED_RECORDS,
        "previous_gate_artifacts": previous,
        "regression_decisions": decisions,
        "hres_comparison": hres,
        "django_changed": False,
        "contract_rules": [
            "MISSING permanece MISSING.",
            "NUMERIC preserva o valor observado.",
            "precipitation[0] permanece MISSING.",
            "run_datetime permanece separado de forecast_datetime.",
            "IFS025 permanece autoridade.",
            "HRES permanece comparação.",
            "RAW permanece preservado.",
            "Nenhum indicador é calculado.",
        ],
    }

    path = REPORT_DIR / (
        f"p9_regression_validation_{generated}.json"
    )

    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def main() -> int:
    print("=" * 78)
    print("G7.4 / P9 — REGRESSÃO CONTROLADA")
    print("=" * 78)
    print(f"Modelo autoridade: {MODEL_IFS025}")
    print(f"Modelo comparação: {MODEL_HRES}")
    print(f"RUNs: {len(RUNS)}")
    print(f"Variáveis: {len(VARIABLES)}")
    print(f"Registros esperados/RUN: {EXPECTED_RECORDS}")
    print("Django: NÃO ALTERADO")
    print()

    previous = check_previous_reports()

    print("ARTEFATOS ANTERIORES")
    print(
        f"  P7 report: "
        f"{'PRESENTE' if previous['p7_report_present'] else 'AUSENTE'}"
    )
    print(
        f"  P8 report: "
        f"{'PRESENTE' if previous['p8_report_present'] else 'AUSENTE'}"
    )
    print()

    decisions = run_authority()

    print("HRES — comparação")
    hres = run_hres()

    for result in hres:
        print(
            f"  RUN {result['run']}: "
            f"HTTP {result['http_status']} | "
            f"{result['status']}"
        )

    report_path = write_report(
        decisions,
        hres,
        previous,
    )

    valid = (
        len(decisions) == len(RUNS)
        and all(item["valid"] for item in decisions)
        and previous["p7_report_present"]
        and previous["p8_report_present"]
    )

    classification = (
        "P9_REGRESSAO_CONTROLADA_VALIDADA"
        if valid
        else "P9_REGRESSAO_CONTROLADA_REPROVADA"
    )

    print()
    print("=" * 78)
    print("P9 PROBE CONCLUÍDO")
    print(f"CLASSIFICAÇÃO: {classification}")
    print(f"REPORT: {report_path.relative_to(BASE_DIR)}")
    print("RAW: preservado em raw\\g74_p0\\")
    print("STAGING: raw\\g74_p0\\canonical_staging\\")
    print("Nenhuma alteração foi feita no Django.")
    print("=" * 78)

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
