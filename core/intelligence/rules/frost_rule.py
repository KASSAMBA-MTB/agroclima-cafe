"""
AgroClima Café

Frost Rule

Regra especialista para avaliação do Frost Risk Index (FRI).

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.8
"""

from datetime import datetime

from core.intelligence.base_rule import BaseRule


class FrostRule(BaseRule):
    """
    Motor especialista de avaliação do Frost Risk Index (FRI).

    Responsabilidades:

    - Calcular o Frost Risk Index (0-100)
    - Classificar o nível de risco
    - Calcular a confiança da avaliação
    - Informar os fatores que influenciaram o cálculo
    """

    id = "FROST_001"

    name = "Frost Rule"

    description = (
        "Avaliação multicritério do risco de geadas."
    )

    WEIGHTS = {
        "temperature": 40,
        "humidity": 15,
        "wind": 10,
        "cloud": 10,
        "altitude": 10,
        "season": 10,
        "history": 5,
    }

    # ==========================================================
    # AVALIAÇÃO PRINCIPAL
    # ==========================================================

    def evaluate(self, context):
        """
        Avalia o risco de geada a partir do contexto climático.
        """

        score = 0

        factors = []

        available = 0

        # ------------------------------------------------------
        # Dados climáticos
        # ------------------------------------------------------

        temperature = context.get(
            "temperature"
        )

        humidity = context.get(
            "humidity"
        )

        wind = context.get(
            "wind_speed"
        )

        cloud = context.get(
            "cloud_cover"
        )

        altitude = context.get(
            "altitude"
        )

        historical = context.get(
            "historical_frost"
        )

        # ------------------------------------------------------
        # Data de análise
        #
        # A camada de orquestração normalmente fornece
        # analysis_date.
        #
        # Entretanto, a regra permanece defensiva:
        # caso o contexto não forneça a data ou forneça None,
        # utiliza a data/hora atual.
        # ------------------------------------------------------

        analysis_date = (
            context.get(
                "analysis_date"
            )
            or datetime.now()
        )

        # ======================================================
        # TEMPERATURA
        # ======================================================

        value, factor = (
            self._temperature_score(
                temperature
            )
        )

        score += value

        if temperature is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # UMIDADE
        # ======================================================

        value, factor = (
            self._humidity_score(
                humidity
            )
        )

        score += value

        if humidity is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # VENTO
        # ======================================================

        value, factor = (
            self._wind_score(
                wind
            )
        )

        score += value

        if wind is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # NEBULOSIDADE
        # ======================================================

        value, factor = (
            self._cloud_score(
                cloud
            )
        )

        score += value

        if cloud is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # ALTITUDE
        # ======================================================

        value, factor = (
            self._altitude_score(
                altitude
            )
        )

        score += value

        if altitude is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # ESTAÇÃO DO ANO
        # ======================================================

        value, factor = (
            self._season_score(
                analysis_date.month
            )
        )

        score += value

        # A data de análise sempre fornece o mês.
        available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # HISTÓRICO DE GEADAS
        # ======================================================

        value, factor = (
            self._history_score(
                historical
            )
        )

        score += value

        # O histórico só contribui para a confiança
        # quando existe informação histórica real.

        if historical is not None:

            available += 1

        if factor:

            factors.append(
                factor
            )

        # ======================================================
        # NORMALIZAÇÃO
        # ======================================================

        score = min(
            score,
            100
        )

        # ======================================================
        # RESULTADO
        # ======================================================

        return {

            "id": self.id,

            "engine": self.name,

            "score": score,

            "severity": self._classify(
                score
            ),

            "confidence": round(
                available / 7,
                2
            ),

            "factors": factors,

            "created_at": analysis_date,
        }

    # ==========================================================
    # SCORES
    # ==========================================================

    def _temperature_score(
        self,
        temperature
    ):
        """
        Calcula a contribuição da temperatura para o FRI.
        """

        if temperature is None:

            return 0, None

        if temperature <= 0:

            return (
                40,
                "Temperatura ≤ 0°C"
            )

        if temperature <= 2:

            return (
                30,
                "Temperatura entre 0°C e 2°C"
            )

        if temperature <= 5:

            return (
                20,
                "Temperatura entre 2°C e 5°C"
            )

        if temperature <= 8:

            return (
                10,
                "Temperatura entre 5°C e 8°C"
            )

        return 0, None

    def _humidity_score(
        self,
        humidity
    ):
        """
        Calcula a contribuição da umidade para o FRI.
        """

        if humidity is None:

            return 0, None

        if humidity >= 90:

            return (
                15,
                "Umidade elevada"
            )

        if humidity >= 80:

            return (
                10,
                "Umidade alta"
            )

        if humidity >= 70:

            return (
                5,
                "Umidade moderada"
            )

        return 0, None

    def _wind_score(
        self,
        wind
    ):
        """
        Calcula a contribuição do vento para o FRI.
        """

        if wind is None:

            return 0, None

        if wind <= 5:

            return (
                10,
                "Ventos fracos"
            )

        if wind <= 10:

            return (
                5,
                "Ventos moderados"
            )

        return 0, None

    def _cloud_score(
        self,
        cloud
    ):
        """
        Calcula a contribuição da nebulosidade para o FRI.
        """

        if cloud is None:

            return 0, None

        if cloud <= 20:

            return (
                10,
                "Céu limpo"
            )

        if cloud <= 50:

            return (
                5,
                "Pouca nebulosidade"
            )

        return 0, None

    def _altitude_score(
        self,
        altitude
    ):
        """
        Calcula a contribuição da altitude para o FRI.
        """

        if altitude is None:

            return 0, None

        if altitude >= 1200:

            return (
                10,
                "Altitude muito elevada"
            )

        if altitude >= 900:

            return (
                7,
                "Altitude elevada"
            )

        if altitude >= 700:

            return (
                4,
                "Altitude intermediária"
            )

        return 0, None

    def _season_score(
        self,
        month
    ):
        """
        Calcula a contribuição sazonal para o FRI.
        """

        if month in (
            6,
            7,
            8
        ):

            return (
                10,
                "Inverno"
            )

        if month in (
            5,
            9
        ):

            return (
                5,
                "Transição sazonal"
            )

        return 0, None

    def _history_score(
        self,
        historical
    ):
        """
        Calcula a contribuição do histórico de geadas.

        Quando o histórico não está disponível, nenhum ponto
        é atribuído e o fator não é considerado disponível.
        """

        if historical is True:

            return (
                5,
                "Histórico de geadas"
            )

        return 0, None

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    def _classify(
        self,
        score
    ):
        """
        Classifica o nível de risco a partir do FRI.
        """

        if score >= 81:

            return "critical"

        if score >= 61:

            return "high"

        if score >= 41:

            return "medium"

        if score >= 21:

            return "low"

        return "none"