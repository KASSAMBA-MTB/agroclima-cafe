"""
G7.4 — SONDAGEM DE EVIDÊNCIAS METEOROLÓGICAS PARA MP-01.11 / MP-01.12

Componente experimental e isolado. Não altera o protocolo P9 existente,
contratos canônicos, DashboardService, mapa, FRI ou IntelligenceEngine.

Uso:
    python tools/g74_p0_hail_evidence_probe.py

A sondagem preserva cada resposta RAW com nome único e gera relatórios TXT/JSON.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "raw" / "g74_p0" / "hail_evidence"
REPORT_DIR = BASE_DIR / "reports" / "g74_p0" / "hail_evidence"

ENDPOINT = "https://single-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs025"
LATITUDE = -21.7874
LONGITUDE = -46.5614
TIMEZONE = "GMT"
CELL_SELECTION = "land"
FORECAST_DAYS = 2
REQUEST_TIMEOUT = 60

RUNS = [
    "2026-04-02T00:00",
    "2026-04-15T00:00",
    "2026-10-03T00:00",
]

# União explícita das entradas obrigatórias e complementares do MP-01.11.
# Os nomes correspondem às variáveis da API Open-Meteo ECMWF IFS 0.25°.
VARIABLES = [
    "cape",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
]

EXPECTED_UNITS = {
    "cape": "J/kg",
    "wind_speed_925hPa": "m/s",
    "wind_direction_925hPa": "°",
    "wind_speed_500hPa": "m/s",
    "wind_direction_500hPa": "°",
    "wet_bulb_temperature_2m": "°C",
    "temperature_850hPa": "°C",
    "relative_humidity_850hPa": "%",
}

REQUIRED_FOR_MP011 = [
    "cape",
    "wind_speed_925hPa",
    "wind_direction_925hPa",
    "wind_speed_500hPa",
    "wind_direction_500hPa",
]
COMPLEMENTARY_FOR_MP0112 = [
    "wet_bulb_temperature_2m",
    "temperature_850hPa",
    "relative_humidity_850hPa",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def build_params(run: str) -> dict[str, str]:
    return {
        "latitude": str(LATITUDE),
        "longitude": str(LONGITUDE),
        "timezone": TIMEZONE,
        "cell_selection": CELL_SELECTION,
        "wind_speed_unit": "ms",
        "models": MODEL,
        "hourly": ",".join(VARIABLES),
        "forecast_days": str(FORECAST_DAYS),
        "run": run,
    }


def request_json(params: dict[str, str]) -> tuple[int, dict | None, str | None, str]:
    query = urllib.parse.urlencode(params)
    url = f"{ENDPOINT}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgroClimaCafe-G7.4-HailEvidence/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), None, url
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        return exc.code, payload, f"HTTPError {exc.code}: {body[:2000]}", url
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return 0, None, f"{type(exc).__name__}: {exc}", url


def save_raw(
    run: str,
    status: int,
    params: dict[str, str],
    url: str,
    payload: dict | None,
    error: str | None,
) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    safe_run = run.replace("-", "").replace(":", "")
    path = RAW_DIR / f"hail_evidence_{MODEL}_{safe_run}_{utc_stamp()}.json"
    document = {
        "protocol": "G7.4/MP-01.12-EVIDENCE",
        "model": MODEL,
        "run": run,
        "http_status": status,
        "request": {"endpoint": ENDPOINT, "params": params, "url": url},
        "error": error,
        "payload": payload,
    }
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def inventory_payload(payload: dict) -> dict:
    """Inspeciona séries sem corrigir, preencher ou converter os dados de origem."""
    hourly = payload.get("hourly")
    units = payload.get("hourly_units")
    issues: list[str] = []

    if not isinstance(hourly, dict):
        return {
            "valid_structure": False,
            "issues": ["payload.hourly ausente ou inválido"],
            "timestamps": 0,
            "first_timestamp": None,
            "last_timestamp": None,
            "variables": {},
            "required_variables_complete": False,
            "complementary_variables_complete": False,
        }
    if not isinstance(units, dict):
        return {
            "valid_structure": False,
            "issues": ["payload.hourly_units ausente ou inválido"],
            "timestamps": 0,
            "first_timestamp": None,
            "last_timestamp": None,
            "variables": {},
            "required_variables_complete": False,
            "complementary_variables_complete": False,
        }

    times = hourly.get("time")
    if not isinstance(times, list):
        times = []
        issues.append("hourly.time ausente ou inválido")

    parsed_times = [parse_time(item) for item in times]
    if any(item is None for item in parsed_times):
        issues.append("um ou mais timestamps são inválidos")
    valid_times = [item for item in parsed_times if item is not None]
    if len(valid_times) != len(set(valid_times)):
        issues.append("timestamps duplicados")
    if any(right <= left for left, right in zip(valid_times, valid_times[1:])):
        issues.append("timestamps fora de ordem")

    variable_report: dict[str, dict] = {}
    for variable in VARIABLES:
        values = hourly.get(variable)
        actual_unit = units.get(variable)
        variable_issues = []
        if not isinstance(values, list):
            variable_report[variable] = {
                "expected_unit": EXPECTED_UNITS[variable],
                "actual_unit": actual_unit,
                "timestamps": len(times),
                "value_count": 0,
                "numeric_count": 0,
                "missing_count": len(times),
                "sample_numeric_values": [],
                "series_present": False,
                "unit_matches": actual_unit == EXPECTED_UNITS[variable],
                "issues": ["série ausente ou não é lista"],
            }
            continue

        numeric_values = [value for value in values if is_finite_number(value)]
        missing_count = len(values) - len(numeric_values)
        if len(values) != len(times):
            variable_issues.append(
                f"comprimento da série ({len(values)}) difere dos timestamps ({len(times)})"
            )
        if actual_unit != EXPECTED_UNITS[variable]:
            variable_issues.append(
                f"unidade retornada {actual_unit!r}; esperada {EXPECTED_UNITS[variable]!r}"
            )
        if not values:
            variable_issues.append("série vazia")

        variable_report[variable] = {
            "expected_unit": EXPECTED_UNITS[variable],
            "actual_unit": actual_unit,
            "timestamps": len(times),
            "value_count": len(values),
            "numeric_count": len(numeric_values),
            "missing_count": missing_count,
            "sample_numeric_values": numeric_values[:5],
            "series_present": True,
            "unit_matches": actual_unit == EXPECTED_UNITS[variable],
            "issues": variable_issues,
        }

    def complete(names: list[str]) -> bool:
        return all(
            variable_report.get(name, {}).get("series_present") is True
            and variable_report[name].get("unit_matches") is True
            and variable_report[name].get("value_count") == len(times)
            and variable_report[name].get("numeric_count") == len(times)
            for name in names
        )

    for name, details in variable_report.items():
        for issue in details["issues"]:
            issues.append(f"{name}: {issue}")

    return {
        "valid_structure": not issues,
        "issues": issues,
        "timestamps": len(times),
        "first_timestamp": times[0] if times else None,
        "last_timestamp": times[-1] if times else None,
        "variables": variable_report,
        "required_variables_complete": complete(REQUIRED_FOR_MP011),
        "complementary_variables_complete": complete(COMPLEMENTARY_FOR_MP0112),
        "required_variables": REQUIRED_FOR_MP011,
        "complementary_variables": COMPLEMENTARY_FOR_MP0112,
    }


def inventory_text(run: str, status: int, raw_path: Path, result: dict) -> str:
    lines = [
        "AGROCLIMA CAFE — INVENTARIO DE EVIDENCIA METEOROLOGICA",
        f"Protocolo: G7.4/MP-01.12-EVIDENCE",
        f"Modelo: {MODEL}",
        f"RUN solicitado: {run}",
        f"HTTP: {status}",
        f"RAW preservado: {raw_path.relative_to(BASE_DIR)}",
        f"Timestamps: {result.get('timestamps', 0)}",
        f"Primeiro timestamp: {result.get('first_timestamp')}",
        f"Ultimo timestamp: {result.get('last_timestamp')}",
        f"Entradas obrigatorias MP-01.11 completas: {result.get('required_variables_complete', False)}",
        f"Variaveis complementares completas: {result.get('complementary_variables_complete', False)}",
        "",
        "INVENTARIO POR VARIAVEL",
    ]
    for name in VARIABLES:
        item = result.get("variables", {}).get(name, {})
        lines.extend([
            f"- {name}",
            f"  Unidade esperada: {item.get('expected_unit')}",
            f"  Unidade retornada: {item.get('actual_unit')}",
            f"  Serie presente: {item.get('series_present', False)}",
            f"  Quantidade de valores: {item.get('value_count', 0)}",
            f"  Valores numericos finitos: {item.get('numeric_count', 0)}",
            f"  Ausencias/valores invalidos: {item.get('missing_count', 0)}",
            f"  Amostras numericas: {item.get('sample_numeric_values', [])}",
            f"  Problemas: {item.get('issues', [])}",
        ])
    lines.extend(["", "PROBLEMAS GERAIS"])
    lines.extend([f"- {issue}" for issue in result.get("issues", [])] or ["- Nenhum problema estrutural detectado."])
    lines.extend([
        "",
        "INTERPRETACAO",
        "Este inventario descreve apenas os valores efetivamente retornados pela API.",
        "Serie ausente, valor nulo, nao numerico ou unidade divergente nao e corrigido automaticamente.",
        "A completude do inventario nao homologa MP-01.12 nem define classificacao de granizo.",
        "",
    ])
    return "\n".join(lines)


def save_report(run: str, status: int, raw_path: Path, inventory: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    safe_run = run.replace("-", "").replace(":", "")
    stem = f"hail_evidence_{MODEL}_{safe_run}_{stamp}"
    txt_path = REPORT_DIR / f"{stem}.txt"
    json_path = REPORT_DIR / f"{stem}.json"
    txt_path.write_text(inventory_text(run, status, raw_path, inventory), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "protocol": "G7.4/MP-01.12-EVIDENCE",
                "model": MODEL,
                "run": run,
                "http_status": status,
                "raw_file": str(raw_path.relative_to(BASE_DIR)),
                "inventory": inventory,
                "operational": False,
                "homologated": False,
                "classification_created": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return txt_path, json_path


def run_one(run: str) -> dict:
    params = build_params(run)
    status, payload, error, url = request_json(params)
    raw_path = save_raw(run, status, params, url, payload, error)

    if status != 200 or not isinstance(payload, dict):
        inventory = {
            "valid_structure": False,
            "issues": [error or f"resposta HTTP {status} sem payload JSON válido"],
            "timestamps": 0,
            "first_timestamp": None,
            "last_timestamp": None,
            "variables": {},
            "required_variables_complete": False,
            "complementary_variables_complete": False,
        }
    else:
        inventory = inventory_payload(payload)

    txt_path, json_path = save_report(run, status, raw_path, inventory)
    passed = (
        status == 200
        and inventory.get("required_variables_complete") is True
        and inventory.get("complementary_variables_complete") is True
    )
    return {
        "run": run,
        "http_status": status,
        "evidence_complete": passed,
        "raw_file": str(raw_path.relative_to(BASE_DIR)),
        "txt_report": str(txt_path.relative_to(BASE_DIR)),
        "json_report": str(json_path.relative_to(BASE_DIR)),
        "inventory": inventory,
    }


def main() -> int:
    print("=" * 78)
    print("G7.4 — SONDAGEM DE EVIDENCIAS PARA MP-01.11 / MP-01.12")
    print("=" * 78)
    print(f"Modelo: {MODEL}")
    print(f"Variaveis solicitadas: {len(VARIABLES)}")
    print("Escopo: somente coleta e auditoria de evidencia; sem alteracao Django.")
    print()

    results = []
    for run in RUNS:
        print(f"Consultando RUN {run}...")
        try:
            result = run_one(run)
        except Exception as exc:
            # Falha inesperada não deve interromper a coleta das demais RUNs.
            result = {
                "run": run,
                "http_status": 0,
                "evidence_complete": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(result)
        print(f"  HTTP: {result.get('http_status')}")
        print(f"  Evidencia completa: {result.get('evidence_complete')}")
        print(f"  TXT: {result.get('txt_report', 'nao gerado')}")
        print()

    complete_count = sum(item.get("evidence_complete") is True for item in results)
    print("=" * 78)
    print(f"RUNs com evidencias completas: {complete_count}/{len(RUNS)}")
    print("MP-01.12: permanece experimental, nao homologada e nao operacional.")
    print("RAW anterior: nao alterado. Novos RAWs usam diretorio dedicado.")
    print("=" * 78)
    return 0 if complete_count == len(RUNS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
