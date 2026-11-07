"""
MP-01.14 - ServiÃ§o de classificaÃ§Ã£o experimental de potencial de granizo.

GovernanÃ§a:
- utiliza exclusivamente limiares persistidos em HailThresholdSet;
- nÃ£o incorpora limiares meteorolÃ³gicos fixos;
- nÃ£o homologa conjuntos;
- nÃ£o autoriza utilizaÃ§Ã£o operacional;
- nÃ£o gera ocorrÃªncias factuais;
- nÃ£o altera HailPotentialService ou seu avaliador congelado.
"""

from core.intelligence.hail_potential_classifier import (
    HailPotentialClassifier,
)


class HailThresholdClassificationService:
    VERSION = "1.0"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    def __init__(self, threshold_set_model=None, classifier_class=None):
        if threshold_set_model is None:
            from core.intelligence.models import HailThresholdSet
            threshold_set_model = HailThresholdSet

        self.threshold_set_model = threshold_set_model
        self.classifier_class = (
            classifier_class or HailPotentialClassifier
        )

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return None
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        return result if result == result and abs(result) != float("inf") else None

    @staticmethod
    def _first_number(mapping, keys):
        if not isinstance(mapping, dict):
            return None
        for key in keys:
            value = HailThresholdClassificationService._number(
                mapping.get(key)
            )
            if value is not None:
                return value
        return None

    @classmethod
    def _extract_inputs(cls, hail_result):
        if not isinstance(hail_result, dict):
            return None, None

        derived = hail_result.get("derived")
        if not isinstance(derived, dict):
            derived = {}

        complementary = hail_result.get("complementary_values")
        if not isinstance(complementary, dict):
            complementary = {}

        cape = cls._first_number(
            derived,
            ("cape_j_kg", "cape", "CAPE", "cape_jkg"),
        )
        shear = cls._first_number(
            derived,
            (
                "shear_925_500",
                "shear_925_500_hpa",
                "shear_925_500_ms",
            ),
        )

        if cape is None:
            cape = cls._first_number(
                complementary, ("cape_j_kg", "cape", "CAPE")
            )
        if shear is None:
            shear = cls._first_number(
                complementary,
                ("shear_925_500", "shear_925_500_hpa"),
            )

        return cape, shear

    @staticmethod
    def _levels(threshold_set):
        bands = getattr(threshold_set, "threshold_bands", None)

        if isinstance(bands, dict):
            bands = bands.get("levels")

        if not isinstance(bands, list) or not bands:
            return None

        levels = []
        for band in bands:
            if not isinstance(band, dict):
                return None

            name = band.get("name") or band.get("level")
            cape_min = HailThresholdClassificationService._number(
                band.get("cape_min")
            )
            shear_min = HailThresholdClassificationService._number(
                band.get("shear_min")
            )

            if not name or cape_min is None or shear_min is None:
                return None

            levels.append({
                "name": str(name),
                "cape_min": cape_min,
                "shear_min": shear_min,
            })

        return levels

    def get_latest_provisional(self):
        """Consulta explÃ­cita; o chamador decide quando acessar o banco."""
        manager = self.threshold_set_model.objects.filter(
            status="PROVISIONAL"
        )
        return manager.order_by("-created_at").first()

    def evaluate(self, hail_result, threshold_set=None):
        base = {
            "service": self.__class__.__name__,
            "service_version": self.VERSION,
            "classification_status": self.NOT_CONFIGURED,
            "potential_level": None,
            "threshold_set_id": None,
            "threshold_set_identifier": None,
            "threshold_set_version": None,
            "threshold_set_status": None,
            "thresholds_source": None,
            "homologated": False,
            "operational": False,
            "is_factual_event": False,
            "limitations": [
                "classificacao exclusivamente experimental",
                "nenhuma homologacao concedida",
                "nenhuma autorizacao operacional",
                "resultado nao representa ocorrencia factual",
            ],
        }

        # 1) ConfiguraÃ§Ã£o tem precedÃªncia: ausÃªncia/invalidez dos limiares
        # nÃ£o pode ser mascarada por ausÃªncia de dados meteorolÃ³gicos.
        # MantÃ©m fallback ORM para chamadas antigas sem threshold_set explÃ­cito.
        if threshold_set is None:
            threshold_set = self.get_latest_provisional()

        if threshold_set is None:
            return base

        levels = self._levels(threshold_set)
        if not levels:
            return base

        base.update({
            "threshold_set_id": str(getattr(threshold_set, "pk", None)),
            "threshold_set_identifier": getattr(threshold_set, "identifier", None),
            "threshold_set_version": getattr(threshold_set, "version", None),
            "threshold_set_status": getattr(threshold_set, "status", None),
            "thresholds_source": getattr(threshold_set, "source", None),
        })

        # 2) SÃ³ com configuraÃ§Ã£o vÃ¡lida, verificar os insumos meteorolÃ³gicos.
        cape, shear = self._extract_inputs(hail_result)
        if cape is None or shear is None:
            base["classification_status"] = self.INSUFFICIENT_DATA
            return base

        classifier = self.classifier_class(configuration={
            "version": threshold_set.version,
            "source": threshold_set.source,
            "levels": levels,
        })
        result = classifier.classify(cape=cape, shear_925_500=shear)

        if hasattr(result, "as_dict"):
            result = result.as_dict()
        elif not isinstance(result, dict):
            result = vars(result)

        base["classification_status"] = result.get(
            "classification_status",
            result.get("status", self.INSUFFICIENT_DATA)
        )
        base["potential_level"] = result.get("potential_level")
        base["cape"] = cape
        base["shear_925_500"] = shear
        base["reason"] = result.get("reason")
        # GovernanÃ§a: nunca homologado, operacional ou factual.
        base["homologated"] = False
        base["operational"] = False
        base["is_factual_event"] = False
        return base
