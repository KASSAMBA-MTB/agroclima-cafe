"""MP-01.13 — Base experimental para validacao cientifica de granizo.

Consome avaliacoes experimentais existentes e referencias independentes.
Nao adquire dados, nao recalcula indicadores meteorologicos, nao classifica
potencial operacional e nao altera FRI, DashboardService ou contratos MP-01.11/12.
"""

from datetime import datetime
from math import isfinite
from statistics import mean, median


class HailScientificValidationService:
    """Valida amostras pareadas e resume evidencias por grupo de referencia."""

    METHOD_VERSION = "MP-01.13.0"
    COMPONENT_ID = "HAIL_SCIENTIFIC_VALIDATION"

    LABEL_CONFIRMED = "HAIL_CONFIRMED"
    LABEL_CONTROL = "CONTROL"
    LABEL_UNCERTAIN = "UNCERTAIN"

    SUPPORTED_LABELS = {
        LABEL_CONFIRMED,
        LABEL_CONTROL,
        LABEL_UNCERTAIN,
    }

    AXIS_FIELDS = {
        "instability": ("instability", "evidence", "value"),
        "organization_shear": ("organization_shear", "evidence", "value"),
        "combined_cape_shear": ("combined_cape_shear", "evidence", "value"),
    }

    def build_report(self, records):
        """Gera relatorio reproduzivel a partir de registros pareados.

        Cada registro deve conter:
        case_id, reference_label, reference_source, reference_id, valid_time,
        latitude, longitude e evaluation (saida experimental MP-01.12).

        Registros UNCERTAIN sao preservados na contagem, mas nao entram
        na comparacao entre eventos confirmados e controles.
        """
        if not isinstance(records, (list, tuple)):
            records = []

        errors = []
        accepted = []
        seen_ids = set()

        for index, record in enumerate(records):
            error = self._validate_record(record, seen_ids)
            if error:
                errors.append({
                    "record_index": index,
                    "case_id": (
                        record.get("case_id")
                        if isinstance(record, dict)
                        else None
                    ),
                    "reason": error,
                })
                continue

            seen_ids.add(record["case_id"])
            accepted.append(self._normalize_record(record))

        confirmed = [
            item for item in accepted
            if item["reference_label"] == self.LABEL_CONFIRMED
        ]
        controls = [
            item for item in accepted
            if item["reference_label"] == self.LABEL_CONTROL
        ]
        uncertain_count = sum(
            item["reference_label"] == self.LABEL_UNCERTAIN
            for item in accepted
        )

        groups = {
            self.LABEL_CONFIRMED: self._summarize_group(confirmed),
            self.LABEL_CONTROL: self._summarize_group(controls),
        }

        if errors:
            status = "DATA_QUALITY_REVIEW_REQUIRED"
        elif confirmed and controls:
            status = "DESCRIPTIVE_COMPARISON_READY"
        else:
            status = "INSUFFICIENT_REFERENCE_GROUPS"

        return {
            "schema": "hail_scientific_validation_report.v1",
            "method_version": self.METHOD_VERSION,
            "component_id": self.COMPONENT_ID,
            "status": status,
            "homologation_decision": "NOT_EVALUATED_BY_THIS_COMPONENT",
            "classification_performed": False,
            "thresholds_applied": False,
            "records_received": len(records),
            "records_accepted": len(accepted),
            "records_rejected": len(errors),
            "uncertain_records_excluded_from_comparison": uncertain_count,
            "reference_groups": groups,
            "errors": errors,
            "limitations": [
                "Comparacao descritiva nao demonstra causalidade.",
                "A qualidade depende da independencia e confiabilidade da referencia.",
                "Valores ausentes nao sao convertidos em zero.",
                "Este componente nao homologa nem classifica potencial de granizo.",
            ],
        }

    def _validate_record(self, record, seen_ids):
        if not isinstance(record, dict):
            return "RECORD_NOT_OBJECT"

        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            return "CASE_ID_REQUIRED"
        if case_id in seen_ids:
            return "DUPLICATE_CASE_ID"

        label = record.get("reference_label")
        if label not in self.SUPPORTED_LABELS:
            return "INVALID_REFERENCE_LABEL"

        for field in ("reference_source", "reference_id", "valid_time"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                return f"{field.upper()}_REQUIRED"

        try:
            parsed_time = datetime.fromisoformat(
                record["valid_time"].replace("Z", "+00:00")
            )
            if parsed_time.tzinfo is None:
                return "VALID_TIME_MUST_INCLUDE_TIMEZONE"
        except (ValueError, TypeError):
            return "INVALID_VALID_TIME"

        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if not self._is_number(latitude) or not -90 <= latitude <= 90:
            return "INVALID_LATITUDE"
        if not self._is_number(longitude) or not -180 <= longitude <= 180:
            return "INVALID_LONGITUDE"

        evaluation = record.get("evaluation")
        if not isinstance(evaluation, dict):
            return "EXPERIMENTAL_EVALUATION_REQUIRED"

        axes = evaluation.get("axes")
        if not isinstance(axes, dict):
            return "EVALUATION_AXES_REQUIRED"

        return None

    def _normalize_record(self, record):
        evaluation = record["evaluation"]
        axes = evaluation["axes"]
        values = {}

        for output_name, path in self.AXIS_FIELDS.items():
            current = axes
            for key in path:
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)

            values[output_name] = (
                float(current) if self._is_number(current) else None
            )

        return {
            "case_id": record["case_id"],
            "reference_label": record["reference_label"],
            "values": values,
        }

    def _summarize_group(self, records):
        summary = {"case_count": len(records), "variables": {}}

        for variable in self.AXIS_FIELDS:
            values = [
                item["values"][variable]
                for item in records
                if item["values"][variable] is not None
            ]

            summary["variables"][variable] = {
                "available_count": len(values),
                "missing_count": len(records) - len(values),
                "mean": mean(values) if values else None,
                "median": median(values) if values else None,
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
            }

        return summary

    @staticmethod
    def _is_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
        )
