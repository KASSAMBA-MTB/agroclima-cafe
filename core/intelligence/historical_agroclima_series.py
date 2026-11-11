from collections import defaultdict

from clima.models import HistoricalWeatherDaily

from core.intelligence.historical_agroclima_index import (
    HistoricalAgroClimateIndex,
)


class HistoricalAgroClimateSeries:
    """
    Processa séries diárias de IAC e cobertura histórica municipal.
    Não preenche componentes meteorológicos ausentes.
    """

    def __init__(self, index_service=None):
        self.index_service = (
            index_service or HistoricalAgroClimateIndex()
        )

    @staticmethod
    def adapt_historical_records(records):
        contexts = []

        for record in records:
            contexts.append({
                "date": record.data,
                "municipality": str(record.station.municipio),
                "temperature": record.temperatura_media,
                "humidity": None,
                "precipitation": record.precipitacao,
                "frost_level": None,
                "hail_level": None,
            })

        return contexts

    def calculate_series(self, daily_contexts):
        results = []

        for context in daily_contexts:
            if not isinstance(context, dict):
                continue

            missing_fields = [
                field
                for field in self.index_service.REQUIRED_FIELDS
                if context.get(field) is None
            ]

            result = self.index_service.calculate(context)

            results.append({
                "date": context.get("date"),
                "municipality": context.get("municipality"),
                "iac": result,
                "status": (
                    "CALCULATED"
                    if result is not None
                    else "INCOMPLETE"
                ),
                "missing_fields": missing_fields,
            })

        return results

    @staticmethod
    def summarize(results):
        total = len(results)
        calculated = sum(
            item["status"] == "CALCULATED"
            for item in results
        )

        return {
            "total_days": total,
            "calculated_days": calculated,
            "incomplete_days": total - calculated,
            "coverage_percent": (
                round(calculated * 100 / total, 2)
                if total else 0.0
            ),
        }

    @staticmethod
    def coverage_report(records=None):
        """
        Consolida cobertura meteorológica e calculabilidade do IAC
        por município, a partir de HistoricalWeatherDaily.
        """
        if records is None:
            records = HistoricalWeatherDaily.objects.select_related(
                "station",
                "station__municipio",
            ).order_by("station__municipio", "data")

        grouped = defaultdict(lambda: {
            "records": 0,
            "dates": set(),
            "first_date": None,
            "last_date": None,
            "temperature": 0,
            "precipitation": 0,
            "eto": 0,
            "humidity": 0,
            "frost": 0,
            "hail": 0,
            "iac_calculable": 0,
        })

        for record in records:
            municipality = str(record.station.municipio)
            item = grouped[municipality]

            item["records"] += 1
            item["dates"].add(record.data)

            if item["first_date"] is None or record.data < item["first_date"]:
                item["first_date"] = record.data

            if item["last_date"] is None or record.data > item["last_date"]:
                item["last_date"] = record.data

            if record.temperatura_media is not None:
                item["temperature"] += 1

            if record.precipitacao is not None:
                item["precipitation"] += 1

            if record.eto_mm_day is not None:
                item["eto"] += 1

            # HistoricalWeatherDaily não possui esses campos.
            # Permanecem zero até existir fonte observacional.
            context = {
                "temperature": record.temperatura_media,
                "humidity": None,
                "precipitation": record.precipitacao,
                "frost_level": None,
                "hail_level": None,
            }

            if all(
                context.get(field) is not None
                for field in HistoricalAgroClimateSeries
                ._required_iac_fields()
            ):
                item["iac_calculable"] += 1

        report = []

        for municipality, item in sorted(grouped.items()):
            total_days = len(item["dates"])

            def percentage(value):
                return round(value * 100 / total_days, 2) if total_days else 0.0

            report.append({
                "municipality": municipality,
                "records": item["records"],
                "distinct_days": total_days,
                "first_date": item["first_date"],
                "last_date": item["last_date"],
                "temperature_days": item["temperature"],
                "temperature_coverage_percent": percentage(item["temperature"]),
                "precipitation_days": item["precipitation"],
                "precipitation_coverage_percent": percentage(item["precipitation"]),
                "eto_days": item["eto"],
                "eto_coverage_percent": percentage(item["eto"]),
                "humidity_days": item["humidity"],
                "humidity_coverage_percent": percentage(item["humidity"]),
                "frost_days": item["frost"],
                "frost_coverage_percent": percentage(item["frost"]),
                "hail_days": item["hail"],
                "hail_coverage_percent": percentage(item["hail"]),
                "iac_calculable_days": item["iac_calculable"],
                "iac_coverage_percent": percentage(item["iac_calculable"]),
            })

        return report

    @staticmethod
    def _required_iac_fields():
        return (
            "temperature",
            "humidity",
            "precipitation",
            "frost_level",
            "hail_level",
        )
