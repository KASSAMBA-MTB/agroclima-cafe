"""
G7.5 / G6 — Orquestração controlada do contexto de indicadores Single Run.

Destino:
    dashboard/services/single_run_indicator_integration_service.py

Responsabilidade:
    Orquestrar somente:
        SingleRunDomainService -> SingleRunIndicatorAdapter

Este componente estabelece a fronteira de integração sem alterar os serviços
históricos existentes.

IMPORTANTE:
    O Single Run homologado é horário (48 timestamps / RUN), enquanto
    HistoricalClimateIndicatorService trabalha com séries históricas diárias.
    Portanto esta camada NÃO converte dados horários em dados diários e NÃO
    chama o serviço histórico para evitar uma interpretação sem contrato.

Não realiza:
    - aquisição;
    - persistência;
    - cálculos derivados;
    - agregação temporal;
    - inteligência;
    - alteração do DashboardService.
"""

from clima.services.single_run_domain_service import SingleRunDomainService
from dashboard.services.single_run_indicator_adapter import (
    SingleRunIndicatorAdapter,
)


class SingleRunIndicatorIntegrationService:
    """Orquestra a passagem do contexto canônico até a fronteira de indicadores."""

    def __init__(self, *, domain_service=None, adapter=None):
        self.domain_service = domain_service or SingleRunDomainService()
        self.adapter = adapter or SingleRunIndicatorAdapter()

    def get_indicator_context(
        self,
        *,
        source,
        model,
        run_datetime,
        lat,
        lon,
        cell_selection,
    ):
        """Resolve o RUN canônico e devolve a entrada estruturada."""
        context = self.domain_service.get_context(
            source=source,
            model=model,
            run_datetime=run_datetime,
            lat=lat,
            lon=lon,
            cell_selection=cell_selection,
        )
        return self.adapter.build_indicator_input(context)

    def get_indicator_context_for_run(self, *, model_run):
        """Adapta diretamente um ModelRun já resolvido."""
        context = self.domain_service.get_context_for_run(
            model_run=model_run
        )
        return self.adapter.build_indicator_input(context)
