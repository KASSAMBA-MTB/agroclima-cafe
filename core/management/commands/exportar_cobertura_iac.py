import csv

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.intelligence.historical_agroclima_series import (
    HistoricalAgroClimateSeries,
)


class Command(BaseCommand):
    help = "Exporta cobertura histórica municipal e calculabilidade do IAC."

    def handle(self, *args, **options):
        rows = HistoricalAgroClimateSeries.coverage_report()

        if not rows:
            raise CommandError(
                "Nenhum município encontrado para exportação."
            )

        output_dir = Path(settings.BASE_DIR) / "research_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        filename = f"PVCA02_COBERTURA_IAC_{timestamp}.csv"
        output_path = output_dir / filename

        try:
            with output_path.open(
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=list(rows[0].keys()),
                )
                writer.writeheader()
                writer.writerows(rows)

        except OSError as exc:
            raise CommandError(
                f"Falha ao gravar CSV: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"CSV GERADO: {output_path}"
            )
        )
        self.stdout.write(f"MUNICIPIOS: {len(rows)}")
        self.stdout.write(
            f"IAC CALCULAVEL: "
            f"{sum(r['iac_calculable_days'] for r in rows)} dias"
        )
