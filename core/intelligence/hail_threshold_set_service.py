"""
MP-01.14 B.7 — Transições controladas do HailThresholdSet.

Homologação e autorização operacional permanecem bloqueadas
até integração formal com o Gate científico do Pacote D.
"""

from django.db import transaction

from core.intelligence.models import HailThresholdSet


class HailThresholdSetTransitionError(ValueError):
    pass


@transaction.atomic
def transition_threshold_set(
    threshold_set_id,
    target_status,
    validation_reference=None,
    operational_authorization=None,
):
    item = HailThresholdSet.objects.select_for_update().get(
        pk=threshold_set_id
    )

    if item.status == HailThresholdSet.Status.HOMOLOGATED:
        raise HailThresholdSetTransitionError(
            "Conjunto homologado não admite nova transição."
        )

    if target_status == HailThresholdSet.Status.HOMOLOGATED:
        raise HailThresholdSetTransitionError(
            "Homologação bloqueada: integração verificável do Gate D "
            "ainda não implementada."
        )

    if target_status not in {
        HailThresholdSet.Status.DRAFT,
        HailThresholdSet.Status.PROVISIONAL,
    }:
        raise HailThresholdSetTransitionError(
            f"Estado inválido: {target_status}"
        )

    if operational_authorization is True:
        raise HailThresholdSetTransitionError(
            "Autorização operacional bloqueada até integração do Gate D."
        )

    item.status = target_status
    item.operational_authorization = False
    item.save()

    return item


@transaction.atomic
def authorize_operational_use(threshold_set_id, gate_reference):
    raise HailThresholdSetTransitionError(
        "Autorização operacional bloqueada: Gate D ainda não integrado."
    )
