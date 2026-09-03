"""
===============================================================================
AgroClima Café
Serviço canônico de classificação térmica operacional

Responsabilidade
----------------
Classificar a temperatura atual recebida pelo backend segundo as sete faixas
operacionais definidas para a apresentação municipal do AgroClima Café.

Regra arquitetural
------------------
Este serviço é a única origem backend da classificação térmica operacional.
O frontend não deve recalcular essas faixas quando o campo canônico já estiver
materializado no map_point.

Importante
----------
A classificação é operacional para representação dos dados meteorológicos
atuais. Ela não substitui nem recalcula FRI, severidade, confiança ou qualquer
outra avaliação oficial de risco.

Ausência de dados
-----------------
Temperatura ausente, nula, não numérica ou não finita resulta em
"unavailable" / "Sem dado". Nenhum valor ausente é convertido para zero.
===============================================================================
"""


class ThermalClassificationService:
    """
    Classifica temperatura atual em sete faixas operacionais canônicas.
    """

    CLASS_FROST = "frost"
    CLASS_VERY_COLD = "veryCold"
    CLASS_COLD = "cold"
    CLASS_COOL = "cool"
    CLASS_FAVORABLE = "favorable"
    CLASS_WARM = "warm"
    CLASS_HOT = "hot"
    CLASS_UNAVAILABLE = "unavailable"

    LABELS = {
        CLASS_FROST: "Geada / extremo frio",
        CLASS_VERY_COLD: "Muito fria",
        CLASS_COLD: "Fria",
        CLASS_COOL: "Fresca",
        CLASS_FAVORABLE: "Faixa favorável",
        CLASS_WARM: "Quente",
        CLASS_HOT: "Muito quente",
        CLASS_UNAVAILABLE: "Sem dado",
    }

    @classmethod
    def classify(cls, value):
        """
        Retorna o identificador canônico da faixa térmica.

        Faixas:
            <= 0 °C       -> frost
            <= 8 °C        -> veryCold
            <= 14 °C       -> cold
            < 18 °C        -> cool
            <= 24 °C       -> favorable
            <= 28 °C       -> warm
            > 28 °C        -> hot
        """

        temperature = cls._to_finite_float(value)

        if temperature is None:
            return cls.CLASS_UNAVAILABLE

        if temperature <= 0:
            return cls.CLASS_FROST

        if temperature <= 8:
            return cls.CLASS_VERY_COLD

        if temperature <= 14:
            return cls.CLASS_COLD

        if temperature < 18:
            return cls.CLASS_COOL

        if temperature <= 24:
            return cls.CLASS_FAVORABLE

        if temperature <= 28:
            return cls.CLASS_WARM

        return cls.CLASS_HOT

    @classmethod
    def label(cls, value):
        """
        Retorna o rótulo humano correspondente à classificação.
        """

        classification = cls.classify(value)
        return cls.LABELS.get(
            classification,
            cls.LABELS[cls.CLASS_UNAVAILABLE],
        )

    @classmethod
    def classify_with_label(cls, value):
        """
        Retorna a classificação e seu rótulo em uma única estrutura.

        Não cria nenhum indicador adicional e não altera o valor original.
        """

        classification = cls.classify(value)

        return {
            "temperature_class": classification,
            "temperature_class_label": cls.LABELS.get(
                classification,
                cls.LABELS[cls.CLASS_UNAVAILABLE],
            ),
        }

    @staticmethod
    def _to_finite_float(value):
        """
        Converte somente valores numéricos válidos para float.

        Valores vazios, inválidos ou não finitos retornam None.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            temperature = float(value)
        except (TypeError, ValueError):
            return None

        if temperature != temperature:
            return None

        if temperature in (float("inf"), float("-inf")):
            return None

        return temperature
