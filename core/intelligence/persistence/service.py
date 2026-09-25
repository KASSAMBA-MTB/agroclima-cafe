
"""
AgroClima Café

Serviço de persistência das interpretações produzidas pela camada de
Inteligência.

MP..............: MP-01.4.7
Responsabilidade: persistir o resultado já produzido pelo
                  IntelligenceEngine/InterpretationCoordinator.

Regra fundamental:
    este serviço NÃO executa regras, NÃO recalcula FRI, score, severity
    ou confidence e NÃO altera a interpretação recebida.
"""

import hashlib
import json
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from core.intelligence.models import IntelligenceInterpretation
from municipios.models import Municipio


class IntelligencePersistenceService:
    """
    Persiste interpretações coordenadas mantendo histórico e idempotência.

    A entrada esperada é uma interpretação já produzida pelo pipeline de
    Inteligência. O serviço apenas extrai os campos de persistência e grava
    o resultado original em JSON.
    """

    VERSION = "1.0"

    @staticmethod
    def _resolve_municipio(context, interpretation):
        """
        Resolve o município a partir do resultado coordenado ou do contexto.

        Não cria município. Se a identidade não existir, a persistência é
        rejeitada pelo contrato.
        """
        municipio_id = (
            interpretation.get("municipio_id")
            or context.get("municipio_id")
        )

        if not municipio_id:
            municipio = context.get("municipio")
            if isinstance(municipio, Municipio):
                return municipio

            municipio_id = getattr(municipio, "id", None)

        if not municipio_id:
            raise ValueError(
                "A interpretação não possui municipio_id válido."
            )

        return Municipio.objects.get(pk=municipio_id)

    @staticmethod
    def _resolve_timestamp(context, interpretation, analysis_timestamp):
        """
        Resolve o instante da análise sem alterar o resultado produzido.
        """
        timestamp = (
            analysis_timestamp
            or interpretation.get("analysis_timestamp")
            or context.get("analysis_timestamp")
        )

        if timestamp is None:
            timestamp = timezone.now()

        return timestamp

    @staticmethod
    def _build_idempotency_key(
        municipio_id,
        rule_id,
        rule_version,
        analysis_timestamp,
    ):
        """
        Gera uma chave determinística para a mesma interpretação/ciclo.
        """
        payload = {
            "municipio_id": str(municipio_id),
            "rule_id": rule_id,
            "rule_version": rule_version,
            "analysis_timestamp": analysis_timestamp.isoformat(),
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        digest = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        return f"INTEL-{digest}"

    @transaction.atomic
    def persist(
        self,
        context,
        interpretation,
        explainability=None,
        analysis_timestamp=None,
        idempotency_key=None,
    ):
        """
        Persiste uma interpretação coordenada.

        Retorno:
            (objeto, created)

        created=True:
            novo registro criado.

        created=False:
            interpretação já existente; nenhum novo registro é criado.
        """
        if not isinstance(context, dict):
            context = {}

        if not isinstance(interpretation, dict):
            raise ValueError(
                "A interpretação deve ser um dicionário."
            )

        rule_id = interpretation.get("rule_id") or interpretation.get("id")

        if not rule_id:
            raise ValueError(
                "A interpretação deve possuir rule_id."
            )

        municipio = self._resolve_municipio(
            context,
            interpretation,
        )

        timestamp = self._resolve_timestamp(
            context,
            interpretation,
            analysis_timestamp,
        )

        rule_version = interpretation.get("rule_version")

        if idempotency_key is None:
            idempotency_key = self._build_idempotency_key(
                municipio.id,
                rule_id,
                rule_version,
                timestamp,
            )

        result = deepcopy(interpretation)

        explainability_value = (
            deepcopy(explainability)
            if explainability is not None
            else None
        )

        defaults = {
            "municipio": municipio,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "result": result,
            "channel": interpretation.get("channel"),
            "severity": interpretation.get("severity"),
            "score": interpretation.get("score"),
            "confidence": interpretation.get("confidence"),
            "factors": deepcopy(interpretation.get("factors")),
            "analysis_timestamp": timestamp,
            "provenance": interpretation.get("provenance"),
            "coordinator_version": interpretation.get(
                "coordinator_version"
            ),
            "policy_version": interpretation.get(
                "policy_version"
            ),
            "explainability": explainability_value,
        }

        instance, created = (
            IntelligenceInterpretation.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults=defaults,
            )
        )

        return instance, created

    def persist_many(
        self,
        context,
        interpretations,
        explainability=None,
        analysis_timestamp=None,
    ):
        """
        Persiste todas as interpretações válidas de uma execução.

        A ordem de entrada é preservada. Resultados que não sejam
        dicionários são ignorados; interpretações sem rule_id são
        rejeitadas pelo método persist().
        """
        if not isinstance(interpretations, list):
            return []

        persisted = []

        for interpretation in interpretations:
            if not isinstance(interpretation, dict):
                continue

            persisted.append(
                self.persist(
                    context=context,
                    interpretation=interpretation,
                    explainability=explainability,
                    analysis_timestamp=analysis_timestamp,
                )
            )

        return persisted
