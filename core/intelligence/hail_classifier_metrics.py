"""MP-01.14 — Métricas objetivas para avaliação binária de granizo.

Calcula métricas somente a partir de previsões já produzidas e referências
independentes. Não treina modelo, não escolhe limiar e não homologa o classificador.
"""

from math import isfinite


class HailClassifierMetrics:
    """Calcula matriz de confusão e métricas padrão de detecção."""

    METHOD_VERSION = "MP-01.14.0"
    POSITIVE_REFERENCE = "HAIL_CONFIRMED"
    NEGATIVE_REFERENCE = "CONTROL"
    POSITIVE_PREDICTION = "HAIL"
    NEGATIVE_PREDICTION = "NO_HAIL"

    def evaluate(self, records):
        """Avalia pares com reference_label e predicted_label.

        UNCERTAIN é excluído da matriz. Registros inválidos são contabilizados
        como rejeitados e não entram no denominador das métricas.
        """
        if not isinstance(records, (list, tuple)):
            records = []

        tp = tn = fp = fn = 0
        uncertain = 0
        rejected = []

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                rejected.append({"record_index": index, "reason": "RECORD_NOT_OBJECT"})
                continue

            reference = record.get("reference_label")
            prediction = record.get("predicted_label")

            if reference == "UNCERTAIN":
                uncertain += 1
                continue
            if reference not in {self.POSITIVE_REFERENCE, self.NEGATIVE_REFERENCE}:
                rejected.append({"record_index": index, "reason": "INVALID_REFERENCE_LABEL"})
                continue
            if prediction not in {self.POSITIVE_PREDICTION, self.NEGATIVE_PREDICTION}:
                rejected.append({"record_index": index, "reason": "INVALID_PREDICTED_LABEL"})
                continue

            actual_positive = reference == self.POSITIVE_REFERENCE
            predicted_positive = prediction == self.POSITIVE_PREDICTION

            if actual_positive and predicted_positive:
                tp += 1
            elif actual_positive and not predicted_positive:
                fn += 1
            elif not actual_positive and predicted_positive:
                fp += 1
            else:
                tn += 1

        total = tp + tn + fp + fn
        pod = self._ratio(tp, tp + fn)
        far = self._ratio(fp, tp + fp)
        csi = self._ratio(tp, tp + fp + fn)
        hss_denominator = (
            (tp + fn) * (fn + tn)
            + (tp + fp) * (fp + tn)
        )
        hss = (
            self._ratio(2 * (tp * tn - fn * fp), hss_denominator)
            if hss_denominator
            else None
        )

        return {
            "schema": "hail_classifier_metrics.v1",
            "method_version": self.METHOD_VERSION,
            "status": (
                "METRICS_COMPUTED"
                if total and not rejected
                else "DATA_QUALITY_REVIEW_REQUIRED"
                if rejected
                else "INSUFFICIENT_EVALUABLE_CASES"
            ),
            "classification_performed_by_this_component": False,
            "homologation_decision": "NOT_EVALUATED_BY_THIS_COMPONENT",
            "confusion_matrix": {
                "true_positive": tp,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
            },
            "metrics": {
                "pod": pod,
                "far": far,
                "csi": csi,
                "hss": hss,
                "accuracy": self._ratio(tp + tn, total),
            },
            "sample_counts": {
                "received": len(records),
                "evaluated": total,
                "uncertain_excluded": uncertain,
                "rejected": len(rejected),
            },
            "errors": rejected,
            "limitations": [
                "Métricas dependem de referências independentes e representativas.",
                "Resultados agregados não substituem validação temporal e regional.",
                "Este componente não treina, calibra ou homologa o classificador.",
            ],
        }

    @staticmethod
    def _ratio(numerator, denominator):
        if not denominator:
            return None
        value = numerator / denominator
        return value if isfinite(value) else None
