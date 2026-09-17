"""
AgroClima Café

Regra de Alertas Meteorológicos
Fase 3 — Inteligência

Responsabilidade
----------------
Avaliar exclusivamente dados meteorológicos canônicos já normalizados
pelo DashboardService e produzir um resultado destinado ao canal de
ALERTAS.

Esta regra NÃO:
    - calcula FRI;
    - altera o FRI;
    - gera Insights;
    - gera recomendações climáticas;
    - consulta HistoricalWeatherDaily;
    - consulta o frontend;
    - cria dados quando o valor é ausente.

Fonte canônica
--------------
    precipitation_24h_mm

Semântica
---------
A classificação operacional de precipitação já existente no projeto
define:

    <= 20 mm      -> moderada
    > 20 a <=50   -> alta
    > 50 a <=80   -> muito alta
    > 80 mm       -> extrema

Para a camada de ALERTAS, somente as classes alta, muito alta e extrema
geram uma condição de alerta.

Mapeamento de severidade:
    alta       -> low
    muito alta -> medium
    extrema   -> critical

O limiar e o mapeamento são regras OPERACIONAIS do AgroClima Café.
Não representam, por si só, um alerta oficial de INMET ou outro órgão.

Contrato de saída
-----------------
O resultado contém "channel": "alert". O IntelligenceEngine utilizará
esse marcador para impedir que esta regra seja enviada ao InsightEngine.
Assim, a introdução desta regra não altera os Insights climáticos
existentes.

Versão: 1.0
"""


class MeteorologicalAlertRule:
    """
    Regra canônica de alerta meteorológico por precipitação acumulada
    em 24 horas.

    A regra opera somente sobre o dado normalizado recebido no contexto.
    """

    ID = "METEO_ALERT_001"
    ENGINE = "Meteorological Alert Rule"

    # Limiares alinhados à classificação operacional de precipitação
    # já existente no AgroClima Café.
    MODERATE_MAX_MM = 20.0
    HIGH_MAX_MM = 50.0
    VERY_HIGH_MAX_MM = 80.0

    def evaluate(self, context):
        """
        Avalia a precipitação acumulada em 24h.

        Retorna:
            dict  -> somente quando existe condição de alerta;
            None  -> quando não há condição ou não existe dado válido.

        A ausência de dado nunca é convertida em zero.
        """

        if not isinstance(context, dict):
            return None

        precipitation = self._to_float(
            context.get(
                "precipitation_24h_mm"
            )
        )

        if precipitation is None:
            return None

        if precipitation < 0:
            return None

        if precipitation <= self.MODERATE_MAX_MM:
            return None

        if precipitation <= self.HIGH_MAX_MM:
            severity = "low"
            severity_label = "Baixo"
            precipitation_class = "high"
            precipitation_label = "Chuva alta"

        elif precipitation <= self.VERY_HIGH_MAX_MM:
            severity = "medium"
            severity_label = "Moderado"
            precipitation_class = "veryHigh"
            precipitation_label = "Chuva muito alta"

        else:
            severity = "critical"
            severity_label = "Crítico"
            precipitation_class = "extreme"
            precipitation_label = "Chuva extrema"

        analysis_date = context.get(
            "analysis_date"
        )

        return {
            "id": self.ID,
            "engine": self.ENGINE,
            "channel": "alert",
            "title": (
                "Alerta de precipitação "
                f"{precipitation_label.lower()}"
            ),
            "recommendation": (
                "A precipitação acumulada em 24 horas "
                f"atingiu {precipitation:.1f} mm, "
                "exigindo atenção às condições meteorológicas."
            ),
            "severity": severity,
            "severity_label": severity_label,
            "metric": "precipitation_24h_mm",
            "metric_value": precipitation,
            "confidence": 1.0,
            "factors": [
                (
                    "Precipitação acumulada em 24h: "
                    f"{precipitation:.1f} mm"
                ),
                (
                    "Classificação operacional: "
                    f"{precipitation_label}"
                ),
            ],
            "precipitation_24h_mm": precipitation,
            "precipitation_24h_class": precipitation_class,
            "precipitation_24h_class_label": precipitation_label,
            "analysis_date": analysis_date,
            "municipio_id": context.get("municipio_id"),
            "municipio_nome": context.get("municipio_nome"),
            "active": True,
        }

    @staticmethod
    def _to_float(value):
        """
        Converte somente valores numéricos válidos.

        None e valores inválidos permanecem ausentes.
        """

        if value is None:
            return None

        try:
            value = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

        if value != value:
            return None

        if value in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return value


# ==========================================================
# REGISTRO DE AUDITORIA — FASE 3
# ==========================================================
#
# Regra criada:
#     METEO_ALERT_001
#
# Fonte:
#     precipitation_24h_mm
#
# Canal:
#     alert
#
# Garantias:
#     - não calcula FRI;
#     - não altera FrostRule;
#     - não gera Insight;
#     - não consulta frontend;
#     - não consulta histórico;
#     - não converte ausência em zero;
#     - utiliza exclusivamente o dado meteorológico canônico.
#
# Cadeia:
#
# Fonte meteorológica
#       ↓
# Aquisição / Provider
#       ↓
# DTO / Persistência
#       ↓
# AgroClimateIndicatorService
#       ↓
# precipitation_24h_mm
#       ↓
# MeteorologicalAlertRule
#       ↓
# severity
#       ↓
# AlertEngine
#       ↓
# context["alerts"]
#       ↓
# Painel Alertas Meteorológicos
#
# A regra é separada do canal de Insights para preservar integralmente
# o comportamento atual dos Insights climáticos.
# ==========================================================
