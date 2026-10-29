"""Executa a montagem MP-01.13 a partir de um manifesto CSV local."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.intelligence.hail_scientific_dataset_builder import (
    HailScientificDatasetBuilder,
)
from core.intelligence.hail_scientific_validation import (
    HailScientificValidationService,
)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Monta o conjunto pareado experimental de validacao de granizo."
    )
    parser.add_argument(
        "--manifest",
        default="research_inputs/hail_scientific_reference_manifest.csv",
        help="CSV local com rotulos de referencia independentes.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Destino JSON; por padrao gera um arquivo novo com timestamp UTC.",
    )
    args = parser.parse_args()

    builder = HailScientificDatasetBuilder(project_root=root)
    records, build_errors, rows_received = builder.build_records(args.manifest)

    report = HailScientificValidationService().build_report(records)
    report["method_version"] = "MP-01.13.1"
    report["manifest_rows_received"] = rows_received
    report["records_received"] = rows_received
    report["records_rejected"] += len(build_errors)
    report["dataset_build_errors"] = build_errors
    report["dataset_builder"] = {
        "component_id": "HAIL_SCIENTIFIC_DATASET_BUILDER",
        "method_version": HailScientificDatasetBuilder.METHOD_VERSION,
        "matching": {
            "time": "EXACT_UTC_TIMESTAMP",
            "coordinates": "EXACT_REQUEST_COORDINATES_ROUNDED_TO_4_DECIMALS",
        },
        "reference_labels_inferred_from_weather": False,
    }

    if build_errors:
        report["status"] = "DATA_QUALITY_REVIEW_REQUIRED"

    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = root / "reports" / "g74_p0" / (
            f"hail_scientific_validation_{stamp}.json"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Manifesto: {args.manifest}")
    print(f"Linhas recebidas: {rows_received}")
    print(f"Registros montados: {len(records)}")
    print(f"Erros de montagem: {len(build_errors)}")
    print(f"Status: {report['status']}")
    print(f"Relatorio: {output}")

    if build_errors:
        return 2
    if report["status"] != "DESCRIPTIVE_COMPARISON_READY":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
