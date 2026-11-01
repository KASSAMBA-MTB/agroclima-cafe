import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Allow the documented direct invocation from any working directory.
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.intelligence.hail_potential_service import HailPotentialService
from core.intelligence.hail_potential_experimental_evaluator import HailPotentialExperimentalEvaluator

p = BASE_DIR / "raw/g74_p0/hail_evidence/hail_evidence_ecmwf_ifs025_20261003T0000_20261010T202559134099Z.json"
raw = json.loads(p.read_text(encoding="utf-8"))
hourly = raw["payload"]["hourly"]

required = [
    "cape", "wind_speed_925hPa", "wind_direction_925hPa",
    "wind_speed_500hPa", "wind_direction_500hPa",
]
complementary = [
    "wet_bulb_temperature_2m", "temperature_850hPa",
    "relative_humidity_850hPa",
]

service = HailPotentialService()
evaluator = HailPotentialExperimentalEvaluator()
results = []

for i, timestamp in enumerate(hourly["time"]):
    series = {
        name: hourly[name][i]
        for name in required + complementary
    }
    context = {
        "source": raw["request"]["endpoint"],
        "model": raw["model"],
        "source_run": raw["run"],
        "valid_from": timestamp,
        "valid_to": timestamp,
        "series": series,
    }
    canonical = service.evaluate(context).as_dict()
    evaluated = evaluator.evaluate(canonical)
    results.append({
        "timestamp": timestamp,
        "service_status": canonical["assessment_status"],
        "evaluator_status": evaluated["classification_status"],
        "reason": evaluated.get("reason"),
        "diagnostics_complete": evaluated["diagnostics_complete"],
        "potential_level": evaluated["potential_level"],
        "cape": series["cape"],
        "shear_925_500_ms": canonical.get("derived", {}).get("shear_925_500_ms"),
        "cape_shear": canonical.get("derived", {}).get("cape_shear"),
    })

out = BASE_DIR / "reports/g74_p0/hail_evidence"
out.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
report = out / f"mp011_mp012_raw_integration_20261003_{timestamp}.json"
if report.exists():
    raise FileExistsError(f"Refusing to overwrite existing report: {report}")
report.write_text(json.dumps({
    "raw_file": str(p.relative_to(BASE_DIR)),
    "model": raw["model"],
    "run": raw["run"],
    "timestamps_processed": len(results),
    "service_assessed": sum(r["service_status"] == "ASSESSED" for r in results),
    "evaluator_results": dict(Counter(r["evaluator_status"] for r in results)),
    "results": results,
}, ensure_ascii=False, indent=2), encoding="utf-8")

print("HORÁRIOS:", len(results))
print("SERVIÇO:", dict(Counter(r["service_status"] for r in results)))
print("AVALIADOR:", dict(Counter(r["evaluator_status"] for r in results)))
print("DIAGNÓSTICOS COMPLETOS:", sum(r["diagnostics_complete"] for r in results))
print("NÍVEL NORMATIVO ATRIBUÍDO:", sum(r["potential_level"] is not None for r in results))
print("RELATÓRIO:", report)
