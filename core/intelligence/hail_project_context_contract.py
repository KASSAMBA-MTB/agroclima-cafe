"""Contrato canônico do contexto global de avaliação meteorológica de granizo.

O contrato transporta avaliações municipais já calculadas. Não define limiares,
não classifica potencial e não representa ocorrência factual de granizo.
"""
from dataclasses import dataclass
from typing import Any


CONTEXT_SCHEMA = "hail_project_context.v1"
CONTEXT_TYPE_ASSESSMENT = "meteorological_assessment"
FACTUAL_EVENT = False


@dataclass(frozen=True)
class HailProjectContextContract:
    municipio_id: Any
    municipio_nome: str | None
    assessment_status: str
    potential_level: str | None
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
        """Normalize a single existing municipal assessment without recalculation."""
        if not isinstance(hail, dict):
            raise TypeError("hail deve ser um dicionário de avaliação municipal")

        status = hail.get("assessment_status")
        if not isinstance(status, str) or not status.strip():
            status = "INSUFFICIENT_DATA"

        level = hail.get("potential_level")
        # The current experimental evaluator does not classify a potential level.
        if status != "ASSESSED":
            level = None

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
            potential_level=level,
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
        """Return the versioned project-level transport contract."""
        return {
            "schema": CONTEXT_SCHEMA,
            "context_type": CONTEXT_TYPE_ASSESSMENT,
            "is_factual_event": FACTUAL_EVENT,
            "municipio_id": self.municipio_id,
            "municipio_nome": self.municipio_nome,
            "assessment_status": self.assessment_status,
            "potential_level": self.potential_level,
            "method_version": self.method_version,
            "source": self.source,
            "model": self.model,
            "source_run": self.source_run,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "missing_variables": list(self.missing_variables),
            "data_quality": dict(self.data_quality),
            "derived": dict(self.derived),
            "municipal_result": dict(self.municipal_result),
        }
