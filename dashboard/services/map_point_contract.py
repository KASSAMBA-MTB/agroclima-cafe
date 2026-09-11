"""
===============================================================================
AgroClima Cafe

Contrato canonico do map_point territorial — FASE 2.

Responsabilidade:
    Definir e normalizar a estrutura unica utilizada para transportar os
    dados municipais desde a camada de consolidacao ate os consumidores da
    Dashboard.

Este modulo NAO calcula FRI, severidade, confianca ou qualquer indicador.
Ele apenas garante o contrato estrutural.
===============================================================================
"""


CANONICAL_MAP_POINT_FIELDS = (
    "id",
    "nome",
    "estado",
    "latitude",
    "longitude",
    "altitude",
    "descricao",
    "color",
    "temperature",
    "humidity",
    "wind_speed",
    "cloud_cover",
    "precipitation",
    "temperature_class",
    "temperature_class_label",
    "precipitation_1h_mm",
    "precipitation_24h_mm",
    "historical_indicators",
    "observation_time",
    "frost",
    "frost_occurrences",
    "frost_last_date",
    "frost_temperature_minimum",
    "historical_frost",
    "historical_total_days",
    "historical_frost_days",
    "historical_frost_frequency",
    "historical_frost_episodes",
    "historical_min_temperature",
    "analysis_date",
    "fri",
    "severity",
    "confidence",
    "frost_factors",
    "frost_evaluation",
    "insights",
    "recommendations",
    "alerts",
    "explainability",
    "insight",
    "recommendation",
    "alert",
    "intelligence_available",
    "intelligence_error",
)


CANONICAL_FRI_FIELDS = (
    "fri",
    "severity",
    "confidence",
    "frost_factors",
    "frost_evaluation",
)


def ensure_map_point_contract(point):
    """
    Garante a presenca das chaves do contrato canonico sem alterar valores
    que ja tenham sido produzidos pelas camadas responsaveis.

    Esta funcao e estrutural: nao calcula, classifica, transforma ou deriva
    nenhum dado de risco.
    """

    normalized = dict(point or {})

    list_fields = {
        "frost_factors",
        "insights",
        "recommendations",
        "alerts",
    }

    dict_fields = {
        "explainability",
        "insight",
        "recommendation",
        "alert",
        "historical_indicators",
    }

    defaults = {
        field: (
            []
            if field in list_fields
            else {}
            if field in dict_fields
            else False
            if field == "intelligence_available"
            else None
        )
        for field in CANONICAL_MAP_POINT_FIELDS
    }


    for field, default in defaults.items():
        if field not in normalized:
            if isinstance(default, (list, dict)):
                normalized[field] = default.copy()
            else:
                normalized[field] = default

    return normalized


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 5.5
# ============================================================================
#
# Objetivo:
#     Consolidar no contrato municipal canônico a estrutura de indicadores
#     históricos produzida pelo HistoricalClimateIndicatorService.
#
# Campo incorporado ao contrato:
#     historical_indicators
#
# Responsabilidade:
#     O map_point_contract somente declara e preserva a estrutura.
#     Nenhum indicador pluviométrico ou térmico é calculado nesta camada.
#
# Indicadores pluviométricos esperados dentro de historical_indicators:
#     precipitação diária;
#     acumulados;
#     frequência de dias chuvosos;
#     período sem chuva;
#     extremos de precipitação.
#
# Regra de qualidade:
#     ausência de dado permanece None;
#     zero representa precipitação efetivamente registrada igual a zero;
#     nenhuma ausência é convertida automaticamente em zero.
#
# Cadeia de distribuição:
#     HistoryService
#         -> HistoricalClimateIndicatorService
#         -> DashboardService
#         -> map_point["historical_indicators"]
#         -> DashboardFacade / consumidores.
#
# Segurança arquitetural:
#     - sem ORM;
#     - sem API;
#     - sem cálculo de indicadores;
#     - sem FRI;
#     - sem severidade;
#     - sem recomendações;
#     - frontend permanece somente apresentação.
#
# Integridade:
#     O campo foi adicionado à lista canônica e ao conjunto de campos
#     estruturados, garantindo default {} quando não houver indicadores
#     disponíveis, sem apagar valores previamente produzidos.
# ============================================================================
