"""
AgroClima Café

Alert Engine

Responsável pela geração e priorização dos alertas
utilizados na Dashboard.

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.9 — Fase 3
Status..........: IMPLEMENTADO / ALERTA METEOROLÓGICO
"""

from datetime import datetime


class AlertEngine:
    """
    Converte recomendações e resultados de regras de alerta
    em alertas estruturados.

    Recomendações com severity="none" permanecem como
    recomendações, mas não são tratadas como alertas.

    Somente low, medium, high e critical geram alertas ativos.

    IMPORTANTE:
    - O campo ``score`` é preservado somente quando fornecido
      pela origem.
    - Métricas meteorológicas não são convertidas em score/FRI.
    - Campos específicos da origem são preservados para garantir
      rastreabilidade e permitir a apresentação correta do alerta.
    """

    PRIORITY = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
        "none": 5,
    }

    ICONS = {
        "critical": "bi-exclamation-octagon-fill",
        "high": "bi-exclamation-triangle-fill",
        "medium": "bi-exclamation-circle-fill",
        "low": "bi-info-circle-fill",
        "none": "bi-check-circle-fill",
    }

    COLORS = {
        "critical": "danger",
        "high": "warning",
        "medium": "primary",
        "low": "info",
        "none": "success",
    }

    LABELS = {
        "critical": "Crítico",
        "high": "Alto",
        "medium": "Moderado",
        "low": "Baixo",
        "none": "Normal",
    }

    ACTIVE_SEVERITIES = {
        "low",
        "medium",
        "high",
        "critical",
    }

    # ==========================================================
    # GERAÇÃO DE ALERTAS
    # ==========================================================

    def generate(self, recommendations):
        """
        Gera somente alertas ativos, ordenados por prioridade.

        A coleção recebida pode conter tanto recomendações
        provenientes de engines de recomendação quanto resultados
        de regras explicitamente marcadas com ``channel="alert"``.

        Cada alerta mantém os campos específicos existentes na
        origem, sem reinterpretar a métrica de origem.
        """

        alerts = []

        for sequence, recommendation in enumerate(recommendations):

            severity = str(
                recommendation.get(
                    "severity",
                    "none"
                )
            ).lower()

            # --------------------------------------------------
            # SITUAÇÃO NORMAL NÃO É ALERTA
            # --------------------------------------------------

            if severity not in self.ACTIVE_SEVERITIES:
                continue

            # --------------------------------------------------
            # CONTRATO BASE DO ALERTA
            # --------------------------------------------------

            alert = {
                "id": recommendation.get(
                    "id"
                ),

                "engine": recommendation.get(
                    "engine"
                ),

                "title": recommendation.get(
                    "title"
                ),

                "message": recommendation.get(
                    "recommendation"
                ),

                "severity": severity,

                "severity_label": self.LABELS.get(
                    severity,
                    "Desconhecido"
                ),

                "priority": self.PRIORITY.get(
                    severity,
                    99
                ),

                # --------------------------------------------------
                # SCORE / FRI
                # --------------------------------------------------
                # Preserva somente o score efetivamente fornecido
                # pela origem. A ausência permanece None.
                # Uma métrica meteorológica como precipitation_24h_mm
                # NÃO é transformada em score ou FRI.
                "score": recommendation.get(
                    "score"
                ),

                "confidence": recommendation.get(
                    "confidence",
                    0
                ),

                "icon": self.ICONS.get(
                    severity,
                    "bi-info-circle-fill"
                ),

                "color": self.COLORS.get(
                    severity,
                    "secondary"
                ),

                "factors": recommendation.get(
                    "factors",
                    []
                ),

                "active": True,

                "created_at": datetime.now(),
            }

            # --------------------------------------------------
            # RASTREABILIDADE DA ORIGEM
            # --------------------------------------------------
            # Os campos abaixo são transportados somente quando
            # presentes na origem. Nenhum deles é reinterpretado.

            source_fields = (
                "channel",
                "metric",
                "metric_value",
                "precipitation_24h_mm",
                "precipitation_24h_class",
                "precipitation_24h_class_label",
                "municipio_id",
                "municipio_nome",
                "analysis_date",
            )

            for field in source_fields:
                if field in recommendation:
                    alert[field] = recommendation.get(field)

            # --------------------------------------------------
            # ALIASES DE RASTREABILIDADE — SOMENTE ORIGEM
            # --------------------------------------------------
            # Mantém campos adicionais de identificação que possam
            # existir em uma regra sem alterar sua semântica.

            if "rule_id" in recommendation:
                alert["rule_id"] = recommendation.get("rule_id")

            if "rule_name" in recommendation:
                alert["rule_name"] = recommendation.get("rule_name")

            # Guarda a posição original para uma ordenação estável.
            # Não utiliza score porque diferentes tipos de alerta
            # podem possuir métricas incomparáveis.
            alert["_sequence"] = sequence

            alerts.append(alert)

        # ------------------------------------------------------
        # ORDENAÇÃO
        # ------------------------------------------------------
        # A prioridade de severidade é comparável entre os alertas.
        # O segundo critério é apenas a ordem original, preservando
        # estabilidade e evitando comparar métricas heterogêneas.

        alerts.sort(
            key=lambda alert: (
                alert["priority"],
                alert["_sequence"],
            )
        )

        for alert in alerts:
            alert.pop("_sequence", None)

        return alerts
