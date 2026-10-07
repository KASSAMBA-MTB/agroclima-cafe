from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from clima.single_runs_acquisition import (
    REFERENCE_CELL_SELECTION,
    REFERENCE_LATITUDE,
    REFERENCE_LONGITUDE,
    REFERENCE_TIMEZONE,
    SingleRunAcquisitionError,
    acquire_and_persist_single_run,
)


class Command(BaseCommand):
    help = (
        "Adquire um RUN do Open-Meteo Single Runs e o persiste "
        "no contrato físico G7.5/G5."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            required=True,
            help="RUN UTC no formato ISO, por exemplo 2026-10-03T00:00.",
        )
        parser.add_argument(
            "--latitude",
            type=float,
            default=REFERENCE_LATITUDE,
        )
        parser.add_argument(
            "--longitude",
            type=float,
            default=REFERENCE_LONGITUDE,
        )
        parser.add_argument(
            "--timezone",
            default=REFERENCE_TIMEZONE,
        )
        parser.add_argument(
            "--cell-selection",
            default=REFERENCE_CELL_SELECTION,
        )

    def handle(self, *args, **options):
        try:
            result = acquire_and_persist_single_run(
                run=options["run"],
                latitude=options["latitude"],
                longitude=options["longitude"],
                timezone_name=options["timezone"],
                cell_selection=options["cell_selection"],
            )
        except (SingleRunAcquisitionError, ValueError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
