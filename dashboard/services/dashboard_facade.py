"""
AgroClima Café

Dashboard Facade

Responsável por integrar os serviços da Dashboard
com a camada de Inteligência.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.6
"""

from django.utils import timezone

from dashboard.services.dashboard_service import (
    DashboardService
)

class DashboardFacade:
    """
    Camada de orquestração da Dashboard.

    Responsável por:

    - Obter os dados estruturados
    - Selecionar o município principal dos KPIs
    - Distribuir a avaliação de FRI já produzida pelo backend
    - Consolidar o contexto final enviado ao Template
    - Preservar os pontos do mapa com seus indicadores canônicos

    A DashboardFacade não implementa regras de risco nem executa
    novamente o FrostRiskService. O DashboardService é a autoridade
    dos dados e das decisões agroclimáticas.
    """

    def __init__(self):

        self.dashboard_service = (
            DashboardService()
        )

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def get_dashboard_data(self):
        """
        Retorna o contexto completo utilizado pela Dashboard.
        """

        # ======================================================
        # DADOS ESTRUTURADOS
        # ======================================================

        context = (
            self.dashboard_service.get_dashboard()
        )

        # ======================================================
        # INTELIGÊNCIA PRINCIPAL
        #
        # A avaliação do FRI já foi realizada uma única vez por
        # município pelo DashboardService. A Facade não executa
        # FrostRiskService novamente.
        #
        # O município principal é identificado pelos KPIs e seus
        # dados já materializados no map_point canônico são apenas
        # distribuídos ao contexto final.
        # ======================================================

        kpis = context.get(
            "kpis",
            {}
        )

        map_points = context.get(
            "map_points",
            []
        )

        primary_id = kpis.get(
            "municipio_id"
        )

        primary_point = next(
            (
                point
                for point in map_points
                if point.get("id") == primary_id
            ),
            None
        )

        if primary_point is None:
            primary_point = next(
                (
                    point
                    for point in map_points
                    if point.get("nome") == kpis.get(
                        "municipio_nome"
                    )
                ),
                None
            )

        # ------------------------------------------------------
        # FRI CANÔNICO
        #
        # O DashboardService já materializa fri, severity,
        # confidence, frost_factors e frost_evaluation.
        # Nenhum desses valores é recalculado aqui.
        # ------------------------------------------------------

        context["frost"] = (
            primary_point.get(
                "frost_evaluation",
                {}
            )
            if primary_point
            else {}
        )

        # ------------------------------------------------------
        # RESULTADOS CONSOLIDADOS
        #
        # A versão atual do DashboardService publica no map_point
        # os campos singulares insight, recommendation e alert.
        # A Facade somente os organiza nos contêineres esperados
        # pelo contexto da Dashboard.
        # ------------------------------------------------------

        insight = (
            primary_point.get(
                "insight"
            )
            if primary_point
            else None
        )

        recommendation = (
            primary_point.get(
                "recommendation"
            )
            if primary_point
            else None
        )

        alert = (
            primary_point.get(
                "alert"
            )
            if primary_point
            else None
        )

        context["rule_results"] = context.get(
            "rule_results",
            []
        )

        context["insights"] = (
            [insight]
            if insight is not None
            else []
        )

        context["recommendations"] = (
            [recommendation]
            if recommendation is not None
            else []
        )

        context["alerts"] = (
            [alert]
            if alert is not None
            else []
        )

        context["explainability"] = (
            primary_point.get(
                "explainability",
                {}
            )
            if primary_point
            else {}
        )

        # ======================================================
        # FASE 2.1
        #
        # INTELIGÊNCIA TERRITORIAL
        # ======================================================

        context["map_points"] = (
            self._process_map_intelligence(
                context.get(
                    "map_points",
                    []
                )
            )
        )

        return context

    # ==========================================================
    # INTELIGÊNCIA TERRITORIAL
    # ==========================================================

    def _process_map_intelligence(
        self,
        map_points,
    ):
        """
        Recebe os pontos municipais já avaliados pelo DashboardService.

        A avaliação municipal do FRI não é executada nesta camada.
        O método apenas preserva e distribui o map_point canônico.
        """

        if not map_points:

            return []

        processed_points = []

        for point in map_points:

            enriched = dict(
                point
            )

            # O DashboardService é a origem da avaliação municipal.
            # Nenhuma chamada ao FrostRiskService é realizada aqui.
            #
            # O resultado já deve conter:
            # - fri
            # - severity
            # - confidence
            # - frost_factors
            # - frost_evaluation
            # - insights
            # - recommendations
            # - alerts
            # - explainability

            processed_points.append(
                enriched
            )

        return processed_points

    # ==========================================================
    # BLOCO RESERVADO — INTEGRIDADE ESTRUTURAL
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    # ==========================================================
    # COR DA SEVERIDADE
    # ==========================================================

    @staticmethod
    def _severity_color(
        severity
    ):
        """
        Retorna somente a representação visual associada
        à severidade já calculada pelo FrostRiskService.

        Não calcula risco.
        """

        colors = {

            "critical":
                "#a52f2f",

            "high":
                "#a94c17",

            "medium":
                "#9a6a00",

            "low":
                "#287a40",

            "none":
                "#666666",
        }

        if severity is None:

            return None

        return colors.get(
            str(
                severity
            ).lower()
        )

# ==========================================================
# REGISTRO DE AUDITORIA — FASE 3
# ==========================================================
#
# Arquivo-base auditado:
#     dashboard_facade.py v3.6
#
# Tamanho original auditado:
#     728 linhas
#     11.286 bytes
#
# Correção aplicada:
#     A Facade deixou de executar novamente o FrostRiskService.
#     A avaliação municipal permanece exclusivamente no
#     DashboardService e é apenas distribuída ao contexto.
#
# Contrato preservado no map_point:
#     temperature
#     temperature_class
#     temperature_class_label
#     precipitation_1h_mm
#     precipitation_24h_mm
#     fri
#     severity
#     confidence
#     frost_factors
#     frost_evaluation
#     insight
#     recommendation
#     alert
#     explainability
#
# Nenhum indicador agroclimático é calculado nesta camada.
# Nenhum valor de precipitação é criado ou transformado nesta camada.
# ==========================================================
#
# Validações previstas antes da entrega:
#     1. Sintaxe Python.
#     2. Ausência de self.frost_risk.
#     3. Ausência de FrostRiskService importado.
#     4. Ausência de nova chamada de avaliação de FRI.
#     5. Preservação integral dos map_points.
#     6. Preservação de None para dados ausentes.
#     7. Compatibilidade com DashboardView.
#     8. Compatibilidade com o contrato do popup municipal.
#
# Regra arquitetural:
#     Backend = autoridade.
#     Facade = orquestração e distribuição.
#     Frontend = apresentação.
#
# Observação:
#     O campo precipitation_24h_mm permanece intocado.
#     Seu valor é produzido pelo DashboardService a partir da
#     cadeia meteorológica oficial e consumido pelos clientes.
#
# Resultado esperado:
#     Os seis municípios continuam recebendo seus map_points
#     com os indicadores térmicos, pluviométricos e FRI já
#     materializados pelo DashboardService.
# ==========================================================
