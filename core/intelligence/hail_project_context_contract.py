"""Contrato canônico do contexto global de avaliação meteorológica de granizo.

Transporta avaliações municipais já calculadas. Não define limiares, não
classifica potencial e não representa ocorrência factual de granizo.
"""
from dataclasses import dataclass
from typing import Any


CONTEXT_SCHEMA = "hail_project_context.v1"
CONTEXT_TYPE_ASSESSMENT = "meteorological_assessment"
CONTEXT_INCLUDED = "INCLUDED"
CLASSIFICATION_NOT_PERFORMED = "NOT_CLASSIFIED"
FACTUAL_EVENT = False


@dataclass(frozen=True)
class HailProjectContextContract:
    municipio_id: Any
    municipio_nome: str | None
    assessment_status: str
    method_version: str | None
    source: str | None
    model: str | None
    source_run: str | None
    valid_from: Any
    valid_to: Any
    missing_variables: tuple[str, ...]
    data_quality: dict
    derived: dict
    municipal_result: dict

    @classmethod
    def from_municipal_result(
        cls,
        *,
        hail: dict,
        municipio_id: Any = None,
        municipio_nome: str | None = None,
    ) -> "HailProjectContextContract":
        """Normalize an existing municipal assessment without recalculation."""
        if not isinstance(hail, dict):
            raise TypeError("hail deve ser um dicionário de avaliação municipal")

        status = hail.get("assessment_status")
        if not isinstance(status, str) or not status.strip():
            status = "INSUFFICIENT_DATA"

        missing = hail.get("missing_variables")
        if not isinstance(missing, (list, tuple)):
            missing = ()

        data_quality = hail.get("data_quality")
        if not isinstance(data_quality, dict):
            data_quality = {}

        derived = hail.get("derived")
        if not isinstance(derived, dict):
            derived = {}

        return cls(
            municipio_id=hail.get("municipio_id", municipio_id),
            municipio_nome=hail.get("municipio_nome", municipio_nome),
            assessment_status=status,
            method_version=hail.get("method_version"),
            source=hail.get("source"),
            model=hail.get("model"),
            source_run=hail.get("source_run"),
            valid_from=hail.get("valid_from"),
            valid_to=hail.get("valid_to"),
            missing_variables=tuple(str(item) for item in missing),
            data_quality=dict(data_quality),
            derived=dict(derived),
            municipal_result=dict(hail),
        )

    def as_dict(self) -> dict:
        """Return the stable project-level context consumed downstream."""
        municipal_result = dict(self.municipal_result)
        # Never leak a potential classification through the nested source payload.
        municipal_result["potential_level"] = None

        return {
            "schema": CONTEXT_SCHEMA,
            "context_type": CONTEXT_TYPE_ASSESSMENT,
            "context_inclusion_status": CONTEXT_INCLUDED,
            "classification_status": CLASSIFICATION_NOT_PERFORMED,
            "is_factual_event": FACTUAL_EVENT,
            "municipio_id": self.municipio_id,
            "municipio_nome": self.municipio_nome,
            "assessment_status": self.assessment_status,
            # Deliberately no potential_level: this rule does not classify hail.
            "potential_level": None,
            "method_version": self.method_version,
            "source": self.source,
            "model": self.model,
            "source_run": self.source_run,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "missing_variables": list(self.missing_variables),
            "data_quality": dict(self.data_quality),
            "derived": dict(self.derived),
            "municipal_result": municipal_result,
        }
