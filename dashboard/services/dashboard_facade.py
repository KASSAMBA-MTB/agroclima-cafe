"""
AgroClima Café

Dashboard Facade

Responsável por integrar os serviços da Dashboard
com a camada de Inteligência.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.5
"""

from django.utils import timezone

from dashboard.services.dashboard_service import (
    DashboardService
)

from core.intelligence.engine import (
    IntelligenceEngine
)


class DashboardFacade:
    """
    Camada de orquestração da Dashboard.

    Responsável por:

    - Obter os dados estruturados
    - Preparar o contexto da Inteligência
    - Executar a Inteligência
    - Consolidar o contexto final enviado ao Template
    - Enriquecer os pontos do mapa com inteligência territorial

    A DashboardFacade não implementa regras de risco.
    As regras permanecem centralizadas na camada
    core.intelligence.
    """

    def __init__(self):

        self.dashboard_service = (
            DashboardService()
        )

        self.intelligence = (
            IntelligenceEngine()
        )

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def get_dashboard_data(self):
        """
        Retorna o contexto completo utilizado pela Dashboard.
        """

        # ======================================================
        # DATA DE ANÁLISE
        # ======================================================

        analysis_date = (
            timezone.localdate()
        )

        # ======================================================
        # DADOS ESTRUTURADOS
        # ======================================================

        context = (
            self.dashboard_service.get_dashboard()
        )

        # ======================================================
        # KPIs
        # ======================================================

        kpis = context.get(
            "kpis",
            {}
        )

        # ======================================================
        # CONTEXTO DA INTELIGÊNCIA PRINCIPAL
        # ======================================================

        intelligence_context = {

            "temperature": kpis.get(
                "temperature"
            ),

            "humidity": kpis.get(
                "humidity"
            ),

            "wind_speed": kpis.get(
                "wind_speed"
            ),

            "cloud_cover": kpis.get(
                "cloud_cover"
            ),

            "altitude": kpis.get(
                "altitude"
            ),

            "historical_frost": kpis.get(
                "historical_frost"
            ),

            # --------------------------------------------------
            # A data do KPI tem prioridade somente quando
            # realmente existe.
            #
            # Quando vier None, utiliza a data atual.
            # --------------------------------------------------

            "analysis_date": (
                kpis.get(
                    "analysis_date"
                )
                or analysis_date
            ),
        }

        # ======================================================
        # INTELIGÊNCIA PRINCIPAL
        # ======================================================

        intelligence = (
            self.intelligence.process(
                intelligence_context
            )
        )

        # ======================================================
        # FROST RISK INDEX PRINCIPAL
        # ======================================================

        context["frost"] = intelligence.get(
            "frost",
            {
                "score": 0,
                "severity": "none",
                "confidence": 0,
                "factors": [],
            },
        )

        # ======================================================
        # RESULTADOS DAS REGRAS
        # ======================================================

        context["rule_results"] = (
            intelligence.get(
                "rule_results",
                [],
            )
        )

        # ======================================================
        # INSIGHTS
        # ======================================================

        context["insights"] = (
            intelligence.get(
                "insights",
                [],
            )
        )

        # ======================================================
        # RECOMENDAÇÕES
        # ======================================================

        context["recommendations"] = (
            intelligence.get(
                "recommendations",
                [],
            )
        )

        # ======================================================
        # ALERTAS
        # ======================================================

        context["alerts"] = (
            intelligence.get(
                "alerts",
                [],
            )
        )

        # ======================================================
        # EXPLICABILIDADE
        # ======================================================

        context["explainability"] = (
            intelligence.get(
                "explainability",
                {},
            )
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
        Executa o mesmo mecanismo de Inteligência já utilizado
        pela Dashboard, individualmente para cada município.

        O método não implementa regras de risco.

        Apenas prepara o contexto municipal, chama o
        IntelligenceEngine e incorpora o resultado ao
        respectivo ponto geográfico.
        """

        if not map_points:

            return []

        processed_points = []

        # ======================================================
        # DATA PADRÃO DA ANÁLISE
        # ======================================================

        analysis_date = (
            timezone.localdate()
        )

        # ======================================================
        # PROCESSAMENTO DOS MUNICÍPIOS
        # ======================================================

        for point in map_points:

            enriched = dict(point)

            # ==================================================
            # DATA DE ANÁLISE DO MUNICÍPIO
            #
            # Se o ponto possuir uma data válida, ela será
            # utilizada.
            #
            # Caso esteja ausente ou seja None, utiliza a
            # data atual.
            # ==================================================

            point_analysis_date = (
                point.get(
                    "analysis_date"
                )
                or analysis_date
            )

            # ==================================================
            # CONTEXTO MUNICIPAL
            # ==================================================

            municipality_context = {

                "temperature": point.get(
                    "temperature"
                ),

                "humidity": point.get(
                    "humidity"
                ),

                "wind_speed": point.get(
                    "wind_speed"
                ),

                "cloud_cover": point.get(
                    "cloud_cover"
                ),

                "altitude": point.get(
                    "altitude"
                ),

                "historical_frost": point.get(
                    "historical_frost"
                ),

                "analysis_date": (
                    point_analysis_date
                ),
            }

            # ==================================================
            # EXECUÇÃO DA INTELIGÊNCIA
            # ==================================================

            try:

                result = (
                    self.intelligence.process(
                        municipality_context
                    )
                )

            except Exception as error:

                # --------------------------------------------------
                # O mapa não deve impedir a Dashboard
                # de funcionar caso um município não
                # possua dados climáticos suficientes.
                # --------------------------------------------------

                enriched["fri"] = None

                enriched["severity"] = None

                enriched["confidence"] = None

                enriched["color"] = None

                enriched["frost_factors"] = []

                # Mantém o contrato territorial estável mesmo
                # quando a Inteligência não puder processar
                # determinado município.
                enriched["insights"] = []
                enriched["recommendations"] = []
                enriched["alerts"] = []
                enriched["explainability"] = {}
                enriched["insight"] = {}
                enriched["insight_title"] = None
                enriched["insight_description"] = None
                enriched["recommendation"] = {}
                enriched["recommendation_title"] = None
                enriched["recommendation_message"] = None
                enriched["alert"] = {}
                enriched["alert_active"] = False
                enriched["alert_title"] = None
                enriched["alert_message"] = None
                enriched["alert_severity"] = None
                enriched["alert_severity_label"] = None

                enriched["intelligence_available"] = False

                enriched["intelligence_error"] = (
                    str(error)
                )

                processed_points.append(
                    enriched
                )

                continue

            # ==================================================
            # FRI
            # ==================================================

            frost = result.get(
                "frost",
                {}
            )

            enriched["fri"] = (
                frost.get(
                    "score"
                )
            )

            # ==================================================
            # SEVERIDADE
            # ==================================================

            enriched["severity"] = (
                frost.get(
                    "severity"
                )
            )

            # ==================================================
            # CONFIANÇA
            # ==================================================

            enriched["confidence"] = (
                frost.get(
                    "confidence"
                )
            )

            # ==================================================
            # FATORES
            # ==================================================

            enriched["frost_factors"] = (
                frost.get(
                    "factors",
                    []
                )
            )

            # ==================================================
            # INTELIGÊNCIA MUNICIPAL COMPLETA
            #
            # O IntelligenceEngine já produz:
            # - insights;
            # - recomendações;
            # - alertas;
            # - explicabilidade.
            #
            # Estes resultados são apenas transportados para
            # o respectivo ponto geográfico. Nenhuma regra de
            # risco é implementada nesta camada.
            # ==================================================

            municipal_insights = result.get(
                "insights",
                []
            )

            municipal_recommendations = result.get(
                "recommendations",
                []
            )

            municipal_alerts = result.get(
                "alerts",
                []
            )

            municipal_explainability = result.get(
                "explainability",
                {}
            )

            enriched["insights"] = (
                municipal_insights
            )

            enriched["recommendations"] = (
                municipal_recommendations
            )

            enriched["alerts"] = (
                municipal_alerts
            )

            enriched["explainability"] = (
                municipal_explainability
            )

            # ==================================================
            # INSIGHT PRINCIPAL
            #
            # O primeiro Insight corresponde ao resultado da
            # regra municipal registrada atualmente.
            # ==================================================

            primary_insight = (
                municipal_insights[0]
                if municipal_insights
                else {}
            )

            enriched["insight"] = (
                primary_insight
            )

            enriched["insight_title"] = (
                primary_insight.get(
                    "title"
                )
            )

            enriched["insight_description"] = (
                primary_insight.get(
                    "description"
                )
            )

            # ==================================================
            # RECOMENDAÇÃO PRINCIPAL
            # ==================================================

            primary_recommendation = (
                municipal_recommendations[0]
                if municipal_recommendations
                else {}
            )

            enriched["recommendation"] = (
                primary_recommendation
            )

            enriched["recommendation_title"] = (
                primary_recommendation.get(
                    "title"
                )
            )

            enriched["recommendation_message"] = (
                primary_recommendation.get(
                    "recommendation"
                )
            )

            # ==================================================
            # ALERTA ATIVO PRINCIPAL
            #
            # AlertEngine não cria alerta para severity="none".
            # Portanto, quando não houver alerta ativo, o campo
            # permanece como dicionário vazio.
            # ==================================================

            primary_alert = (
                municipal_alerts[0]
                if municipal_alerts
                else {}
            )

            enriched["alert"] = (
                primary_alert
            )

            enriched["alert_active"] = bool(
                primary_alert
            )

            enriched["alert_title"] = (
                primary_alert.get(
                    "title"
                )
            )

            enriched["alert_message"] = (
                primary_alert.get(
                    "message"
                )
            )

            enriched["alert_severity"] = (
                primary_alert.get(
                    "severity"
                )
            )

            enriched["alert_severity_label"] = (
                primary_alert.get(
                    "severity_label"
                )
            )

            # ==================================================
            # COR
            #
            # A cor é apenas uma representação
            # visual da severidade calculada
            # pela Inteligência.
            # ==================================================

            enriched["color"] = (
                self._severity_color(
                    frost.get(
                        "severity"
                    )
                )
            )

            # ==================================================
            # DISPONIBILIDADE DA INTELIGÊNCIA
            # ==================================================

            enriched["intelligence_available"] = True

            # ==================================================
            # ERRO DE INTELIGÊNCIA
            #
            # Quando o processamento foi concluído
            # corretamente, não há erro.
            # ==================================================

            enriched["intelligence_error"] = None

            # ==================================================
            # DATA DE ANÁLISE UTILIZADA
            # ==================================================

            enriched["analysis_date"] = (
                point_analysis_date
            )

            # ==================================================
            # DADOS DE TEMPERATURA / PRECIPITAÇÃO
            #
            # Permanecem disponíveis para as próximas
            # camadas do mapa.
            # ==================================================

            processed_points.append(
                enriched
            )

        return processed_points

    # ==========================================================
    # COR DA SEVERIDADE
    # ==========================================================

    @staticmethod
    def _severity_color(
        severity
    ):
        """
        Retorna somente a representação visual associada
        à severidade já calculada pelo IntelligenceEngine.

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