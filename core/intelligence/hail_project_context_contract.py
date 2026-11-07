"""Contrato canÃ´nico do contexto global de avaliaÃ§Ã£o meteorolÃ³gica de granizo.

Transporta avaliaÃ§Ãµes municipais jÃ¡ calculadas. NÃ£o define limiares, nÃ£o
classifica potencial e nÃ£o representa ocorrÃªncia factual de granizo.
"""
from dataclasses import dataclass
from typing import Any

from core.intelligence.hail_potential_experimental_evaluator import (
    CLASSIFICATION_STATUS as EXPERIMENTAL_CLASSIFICATION_STATUS,
    INSUFFICIENT_STATUS as EXPERIMENTAL_INSUFFICIENT_STATUS,
)


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
            raise TypeError("hail deve ser um dicionÃ¡rio de avaliaÃ§Ã£o municipal")

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
        municipal_result["potential_level"] = None
        self._sanitize_unclassified_fields(municipal_result)

        # These are the two structured children the contract currently
        # exposes: the experimental diagnostic and the canonical municipal
        # meteorological payload. Keep their scientific values intact while
        # enforcing the contract's non-classification boundary.
        experimental = municipal_result.get("experimental_evaluation")
        if isinstance(experimental, dict):
            experimental = dict(experimental)
            experimental["potential_level"] = None
            experimental["operational"] = False
            experimental["homologated"] = False
            if (
                "classification_status" in experimental
                and experimental["classification_status"] not in {
                    EXPERIMENTAL_CLASSIFICATION_STATUS,
                    EXPERIMENTAL_INSUFFICIENT_STATUS,
                }
            ):
                experimental["classification_status"] = (
                    EXPERIMENTAL_INSUFFICIENT_STATUS
                    if experimental.get("assessment_status")
                    == EXPERIMENTAL_INSUFFICIENT_STATUS
                    else EXPERIMENTAL_CLASSIFICATION_STATUS
                )
            self._sanitize_factual_flag(experimental)
            municipal_result["experimental_evaluation"] = experimental

        # MP-01.14.2 / Pacote C1: projeção municipal aditiva do potencial
        # experimental. Não homologa thresholds nem cria ocorrência factual.
        experimental = municipal_result.get("experimental_evaluation")
        if isinstance(experimental, dict):
            axes = experimental.get("axes")
            if not isinstance(axes, dict):
                axes = {}
            determining_indicators = []
            for axis_name, axis in axes.items():
                if not isinstance(axis, dict) or axis.get("status") != "AVAILABLE":
                    continue
                evidence = axis.get("evidence")
                if isinstance(evidence, dict) and evidence.get("value") is not None:
                    determining_indicators.append(axis_name)

            municipal_result.update({
                "potential_level": None,
                "classification_status": (
                    EXPERIMENTAL_INSUFFICIENT_STATUS
                    if experimental.get("evaluation_status")
                    == EXPERIMENTAL_INSUFFICIENT_STATUS
                    else EXPERIMENTAL_CLASSIFICATION_STATUS
                ),
                "rule_version": (
                    experimental.get("experimental_diagnostic_version")
                    or experimental.get("method_version")
                ),
                "rule_applied": "HAIL_POTENTIAL_EXPERIMENTAL_EVALUATOR",
                "determining_indicators": determining_indicators,
                "threshold_set_version": None,
                "threshold_set_status": "NOT_CONFIGURED",
                "validation_reference": None,
                "limitations": [
                    "Classificação experimental não homologada.",
                    "Conjunto de limiares não associado ao município.",
                    "Resultado não representa ocorrência factual.",
                ],
                "operational": False,
                "is_factual_event": False,
            })
        else:
            municipal_result.update({
                "potential_level": None,
                "classification_status": CLASSIFICATION_NOT_PERFORMED,
                "rule_version": self.method_version,
                "rule_applied": "HAIL_POTENTIAL_EXPERIMENTAL_EVALUATOR",
                "determining_indicators": [],
                "threshold_set_version": None,
                "threshold_set_status": "NOT_CONFIGURED",
                "validation_reference": None,
                "limitations": [
                    "Avaliação experimental indisponível ou insuficiente.",
                ],
                "operational": False,
                "is_factual_event": False,
            })

        nested_municipal_result = municipal_result.get("municipal_result")
        if isinstance(nested_municipal_result, dict):
            nested_municipal_result = dict(nested_municipal_result)
            nested_municipal_result["potential_level"] = None
            self._sanitize_unclassified_fields(nested_municipal_result)
            municipal_result["municipal_result"] = nested_municipal_result

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
            "canonical_method_version": (
                self.municipal_result.get("canonical_method_version")
                or self.method_version
            ),
            "experimental_diagnostic_version": (
                self.municipal_result.get("experimental_diagnostic_version")
                or (self.municipal_result.get("experimental_evaluation") or {}).get("experimental_diagnostic_version")
                or (self.municipal_result.get("experimental_evaluation") or {}).get("method_version")

            ),
            "rule_implementation_version": self.municipal_result.get("rule_implementation_version"),
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

    @staticmethod
    def _sanitize_unclassified_fields(payload: dict) -> None:
        """Sanitize classification fields on a known municipal payload."""
        if "classification_status" in payload:
            payload["classification_status"] = CLASSIFICATION_NOT_PERFORMED
        HailProjectContextContract._sanitize_factual_flag(payload)

    @staticmethod
    def _sanitize_factual_flag(payload: dict) -> None:
        if "is_factual_event" in payload:
            payload["is_factual_event"] = FACTUAL_EVENT
