"""
AgroClima Café

Frost Rule

Regra especialista para avaliação do Frost Risk Index (FRI).

Curso...........: Bacharelado em Ciência de Dados
Instituição.....: UNIVESP
Projeto.........: AgroClima Café

Versão..........: 3.9
"""

from datetime import datetime
import math

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

        historical_total_days = context.get(
            "historical_total_days"
        )

        historical_frost_days = context.get(
            "historical_frost_days"
        )

        historical_frost_frequency = context.get(
            "historical_frost_frequency"
        )

        historical_frost_episodes = context.get(
            "historical_frost_episodes"
        )

        historical_min_temperature = context.get(
            "historical_min_temperature"
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
                historical=historical,
                total_days=historical_total_days,
                frost_days=historical_frost_days,
                frequency=historical_frost_frequency,
                episodes=historical_frost_episodes,
                minimum_temperature=historical_min_temperature,
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
        historical,
        total_days=None,
        frost_days=None,
        frequency=None,
        episodes=None,
        minimum_temperature=None,
    ):
        """
        Calcula a contribuição histórica para o FRI.

        A fonte é exclusivamente a evidência histórica persistida
        pelo DashboardService a partir de HistoricalWeatherDaily.

        Compatibilidade:
            - quando os campos quantitativos não estiverem
              disponíveis, utiliza historical_frost;
            - quando estiverem disponíveis, a frequência histórica
              é a evidência principal.

        O histórico não inventa risco: ausência de ocorrência
        produz contribuição zero.
        """

        if (
            total_days is None
            and frost_days is None
            and frequency is None
        ):
            if historical is True:
                return (
                    self.WEIGHTS["history"],
                    "Histórico de geadas",
                )

            return 0, None

        try:
            total = float(total_days or 0)
        except (TypeError, ValueError):
            total = 0.0

        try:
            frost_count = float(frost_days or 0)
        except (TypeError, ValueError):
            frost_count = 0.0

        try:
            freq = float(frequency) if frequency is not None else None
        except (TypeError, ValueError):
            freq = None

        if freq is None:
            freq = (
                frost_count / total
                if total > 0
                else 0.0
            )

        freq = max(0.0, min(freq, 1.0))

        # ==========================================================
        # PONTUAÇÃO HISTÓRICA QUANTITATIVA
        # ==========================================================
        #
        # O histórico permanece limitado ao peso máximo definido
        # pela regra: 5 pontos.
        #
        # Critérios:
        #   - nenhuma ocorrência real -> 0 pontos;
        #   - qualquer ocorrência real -> pelo menos 1 ponto;
        #   - maior frequência -> nunca menor pontuação;
        #   - frequência de 100% -> 5 pontos.
        #
        # A frequência é a variável principal da contribuição
        # histórica. Episódios e mínima histórica permanecem como
        # evidências de explicabilidade e não são somados novamente,
        # evitando dupla contagem.
        # ==========================================================

        history_weight = self.WEIGHTS["history"]

        if frost_count <= 0 and historical is not True:
            return 0, None

        # A frequência já foi normalizada no intervalo [0, 1].
        history_score = math.ceil(
            freq * history_weight
        )

        # Uma ocorrência histórica real não pode resultar em
        # contribuição zero.
        history_score = max(
            1,
            min(
                history_score,
                history_weight
            )
        )

        details = [
            "Histórico de geadas",
        ]

        if total > 0:
            details.append(
                f"{int(frost_count)} ocorrência(s) em "
                f"{int(total)} dia(s)"
            )

        details.append(
            f"frequência histórica {freq * 100:.1f}%"
        )

        if episodes is not None:
            try:
                details.append(
                    f"{int(float(episodes))} episódio(s)"
                )
            except (TypeError, ValueError):
                pass

        if minimum_temperature is not None:
            try:
                details.append(
                    f"mínima histórica "
                    f"{float(minimum_temperature):.1f} °C"
                )
            except (TypeError, ValueError):
                pass

        return (
            history_score,
            " — ".join(details),
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