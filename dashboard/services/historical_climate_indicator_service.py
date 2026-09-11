"""
==============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Indicadores Históricos
Arquivo.........: historical_climate_indicator_service.py
Fase............: Fase 5 - Indicadores térmicos
Responsável.....: Walter Junio Pontes Teixeira
Ano.............: 2026

DESCRIÇÃO
---------
Serviço de backend responsável por calcular indicadores derivados da série
histórica diária fornecida pelo HistoryService.

PRINCÍPIO ARQUITETURAL
----------------------
O serviço não consulta banco de dados, não consulta API externa e não conhece
frontend. Recebe somente dados históricos estruturados e devolve indicadores
estruturados para a camada de integração do backend.

ESCOPO DESTA VERSÃO
-------------------
Implementação da amplitude térmica diária, dos agregados de amplitude, da
tendência térmica e da frequência operacional de temperaturas críticas e a distribuição das sete faixas térmicas.

A amplitude diária é calculada somente quando temperatura mínima e temperatura
máxima existem e são valores numéricos válidos:

    amplitude = temperatura_maxima - temperatura_minima

Nenhum valor ausente é convertido em zero.

PREPARAÇÃO PARA A FASE 5
------------------------
A estrutura do serviço foi organizada para receber progressivamente outros
indicadores históricos previstos na especificação oficial, sem implementá-los
antecipadamente nesta etapa.

Não calcula FRI, severidade, confiança, alertas, recomendações ou regras
agronômicas.

A distribuição das faixas térmicas utiliza exclusivamente o
ThermalClassificationService, única origem das sete faixas operacionais.
==============================================================================
"""

from math import isfinite

from dashboard.services.thermal_classification_service import (
    ThermalClassificationService,
)
from dashboard.services.hydric_balance_service import HydricBalanceService
from dashboard.services.hydric_balance_configuration_service import (
    HydricBalanceConfigurationService,
)


class HistoricalClimateIndicatorService:
    """
    Calcula indicadores derivados a partir de séries históricas estruturadas.

    O serviço permanece desacoplado de ORM, API, Dashboard e frontend.
    """

    INDICATOR_VERSION = "6.1"

    # Unidade canônica da ETo: milímetros por dia (mm/dia).
    # O valor é fornecido pelo provider e persistido pelo histórico.
    # Este serviço apenas consolida a série e calcula agregados derivados.
    ETO_UNIT = "mm/dia"

    def __init__(self):
        self.hydric_configuration_service = (
            HydricBalanceConfigurationService()
        )

    def calculate(
        self,
        historical_data,
        cad_mm=None,
        initial_arm_mm=None,
        cad_provenance=None,
        initial_arm_method="EXPLICIT",
        municipality_key=None,
    ):
        """
        Calcula os indicadores históricos autorizados para esta etapa.

        Parâmetro
        ---------
        historical_data : dict
            Contrato produzido pelo HistoryService. Nesta etapa são utilizados
            principalmente:
                - dias
                - temperatura_minima
                - temperatura_maxima

        Retorno
        -------
        dict
            Indicadores históricos estruturados.
        """

        data = historical_data or {}

        days = self._as_list(
            data.get("dias")
        )

        minimums = self._as_list(
            data.get("temperatura_minima")
        )

        maximums = self._as_list(
            data.get("temperatura_maxima")
        )

        daily_amplitude = self._calculate_daily_amplitude(
            minimums,
            maximums,
        )

        valid_amplitudes = [
            value
            for value in daily_amplitude
            if value is not None
        ]

        temperature_series = self._as_list(
            data.get("temperatura")
        )

        valid_temperatures = self._valid_series(
            temperature_series
        )

        temperature_trend = self._calculate_temperature_trend(
            valid_temperatures
        )

        critical_temperature_frequency = (
            self._calculate_critical_temperature_frequency(
                valid_temperatures
            )
        )

        temperature_band_distribution = (
            self._calculate_temperature_band_distribution(
                valid_temperatures
            )
        )

        temperature_band_counts = (
            self._calculate_temperature_band_counts(
                temperature_band_distribution
            )
        )

        precipitation_series = self._as_list(
            data.get("precipitacao")
        )

        precipitation_indicators = (
            self._calculate_precipitation_indicators(
                precipitation_series
            )
        )

        eto_series = self._as_list(
            data.get("eto_mm_day")
        )

        eto_indicators = (
            self._calculate_eto_indicators(
                eto_series
            )
        )

        # ==============================================================
        # CONFIGURAÇÃO MUNICIPAL DO BALANÇO HÍDRICO — FASE 6.2
        #
        # Quando os parâmetros hídricos não são explicitamente fornecidos
        # pelo chamador, a configuração municipal é consultada pela
        # camada especializada de configuração.
        #
        # Não existe valor padrão de CAD ou ARM.
        # Sem configuração válida, o HydricBalanceService permanece
        # responsável por retornar NOT_CONFIGURED.
        #
        # A compatibilidade com chamadas anteriores é preservada:
        # parâmetros explicitamente fornecidos pelo chamador têm prioridade.
        # ==============================================================
        configured_cad = cad_mm
        configured_initial_arm = initial_arm_mm
        configured_provenance = cad_provenance
        configured_arm_method = initial_arm_method

        configuration = None

        configuration_requested = (
            cad_mm is None
            and initial_arm_mm is None
            and cad_provenance is None
            and initial_arm_method == "EXPLICIT"
            and municipality_key is not None
        )

        if configuration_requested:
            configuration = (
                self.hydric_configuration_service.get_configuration(
                    municipality_key
                )
            )

            if (
                configuration["status"]
                == self.hydric_configuration_service.STATUS_CONFIGURED
            ):
                configured_cad = configuration["cad_mm"]
                configured_initial_arm = configuration[
                    "initial_arm_mm"
                ]
                configured_provenance = configuration[
                    "cad_provenance"
                ]
                configured_arm_method = configuration[
                    "initial_arm_method"
                ]

        hydric_balance = HydricBalanceService().calculate(
            precipitation_series=precipitation_series,
            eto_series=eto_series,
            cad_mm=configured_cad,
            initial_arm_mm=configured_initial_arm,
            scope="MUNICIPAL",
            cad_provenance=configured_provenance,
            initial_arm_method=configured_arm_method,
            dates=days,
        )

        # A configuração é exposta somente como metadado estruturado.
        # Nenhuma decisão agronômica é criada neste serviço.
        if configuration is not None:
            hydric_balance["hydric_configuration_version"] = (
                configuration["version"]
            )
            hydric_balance["hydric_configuration_status"] = (
                configuration["status"]
            )
            hydric_balance["hydric_configuration_municipality_key"] = (
                configuration["municipality_key"]
            )
            hydric_balance["hydric_configuration_validation_error"] = (
                configuration["validation_error"]
            )
        else:
            hydric_balance["hydric_configuration_version"] = None
            hydric_balance["hydric_configuration_status"] = (
                "EXPLICIT_PARAMETERS"
            )
            hydric_balance["hydric_configuration_municipality_key"] = (
                municipality_key
            )
            hydric_balance["hydric_configuration_validation_error"] = None

        # O contrato canônico usa a série de dias como referência.
        # Quando as séries térmicas estiverem incompletas, não são criados
        # dias artificiais; a quantidade disponível permanece limitada aos
        # dias efetivamente recebidos pelo HistoryService.
        days_available = len(days)

        return {
            "indicator_version": self.INDICATOR_VERSION,

            "tendencia_termica": temperature_trend,

            "tendencia_termica_diferenca": (
                self._temperature_difference(valid_temperatures)
            ),

            "tendencia_termica_dias_validos": len(
                valid_temperatures
            ),

            "frequencia_temperaturas_criticas": (
                critical_temperature_frequency
            ),

            "frequencia_faixas_termicas": (
                temperature_band_distribution
            ),

            "dias_frios": (
                temperature_band_counts["dias_frios"]
                if temperature_band_counts is not None
                else None
            ),

            "dias_muito_quentes": (
                temperature_band_counts["dias_muito_quentes"]
                if temperature_band_counts is not None
                else None
            ),

            "dias_temperatura_ate_zero": (
                temperature_band_counts["dias_temperatura_ate_zero"]
                if temperature_band_counts is not None
                else None
            ),

            "amplitude_termica_diaria": daily_amplitude,

            "amplitude_termica_media": (
                self._mean(
                    valid_amplitudes
                )
                if valid_amplitudes
                else None
            ),

            "amplitude_termica_minima": (
                min(
                    valid_amplitudes
                )
                if valid_amplitudes
                else None
            ),

            "amplitude_termica_maxima": (
                max(
                    valid_amplitudes
                )
                if valid_amplitudes
                else None
            ),

            "amplitude_termica_dias_validos": len(
                valid_amplitudes
            ),

            "amplitude_termica_dias_disponiveis": days_available,

            "precipitacao_acumulada": (
                precipitation_indicators["precipitacao_acumulada"]
                if precipitation_indicators is not None
                else None
            ),

            "precipitacao_media_diaria": (
                precipitation_indicators["precipitacao_media_diaria"]
                if precipitation_indicators is not None
                else None
            ),

            "dias_chuvosos": (
                precipitation_indicators["dias_chuvosos"]
                if precipitation_indicators is not None
                else None
            ),

            "frequencia_dias_chuvosos": (
                precipitation_indicators["frequencia_dias_chuvosos"]
                if precipitation_indicators is not None
                else None
            ),

            "periodo_sem_chuva_atual": (
                precipitation_indicators["periodo_sem_chuva_atual"]
                if precipitation_indicators is not None
                else None
            ),

            "maior_periodo_sem_chuva": (
                precipitation_indicators["maior_periodo_sem_chuva"]
                if precipitation_indicators is not None
                else None
            ),

            "precipitacao_minima": (
                precipitation_indicators["precipitacao_minima"]
                if precipitation_indicators is not None
                else None
            ),

            "precipitacao_maxima": (
                precipitation_indicators["precipitacao_maxima"]
                if precipitation_indicators is not None
                else None
            ),

            "precipitacao_dias_validos": (
                precipitation_indicators["dias_validos"]
                if precipitation_indicators is not None
                else 0
            ),

            "eto_mm_day": eto_series,

            "eto_acumulada": (
                eto_indicators["eto_acumulada"]
                if eto_indicators is not None
                else None
            ),

            "eto_media_diaria": (
                eto_indicators["eto_media_diaria"]
                if eto_indicators is not None
                else None
            ),

            "eto_minima": (
                eto_indicators["eto_minima"]
                if eto_indicators is not None
                else None
            ),

            "eto_maxima": (
                eto_indicators["eto_maxima"]
                if eto_indicators is not None
                else None
            ),

            "eto_dias_validos": (
                eto_indicators["dias_validos"]
                if eto_indicators is not None
                else 0
            ),

            "hydric_balance_version": hydric_balance["hydric_balance_version"],
            "hydric_balance_method": hydric_balance["hydric_balance_method"],
            "hydric_balance_status": hydric_balance["hydric_balance_status"],
            "hydric_balance_scope": hydric_balance["hydric_balance_scope"],
            "cad_mm": hydric_balance["cad_mm"],
            "cad_provenance": hydric_balance["cad_provenance"],
            "initial_arm_mm": hydric_balance["initial_arm_mm"],
            "initial_arm_method": hydric_balance["initial_arm_method"],
            "saldo_hidrico_diario_mm": hydric_balance["saldo_hidrico_diario_mm"],
            "arm_diario_mm": hydric_balance["arm_diario_mm"],
            "arm_percentual_diario": hydric_balance["arm_percentual_diario"],
            "deficit_hidrico_diario_mm": hydric_balance["deficit_hidrico_diario_mm"],
            "excedente_hidrico_diario_mm": hydric_balance["excedente_hidrico_diario_mm"],
            "arm_final_mm": hydric_balance["arm_final_mm"],
            "arm_final_percentual": hydric_balance["arm_final_percentual"],
            "deficit_hidrico_mm": hydric_balance["deficit_hidrico_mm"],
            "excedente_hidrico_mm": hydric_balance["excedente_hidrico_mm"],
            "deficit_hidrico_acumulado": hydric_balance["deficit_hidrico_acumulado"],
            "excedente_hidrico_acumulado": hydric_balance["excedente_hidrico_acumulado"],
            "condition_hidrica": hydric_balance["condition_hidrica"],
            "hydric_balance_validation_error": hydric_balance["validation_error"],

            # Metadados da configuração municipal utilizada na resolução
            # dos parâmetros hídricos. A ausência permanece explicitamente
            # representada quando não houve configuração consultada.
            "hydric_configuration_version": (
                configuration["version"]
                if configuration is not None
                else None
            ),
            "hydric_configuration_status": (
                configuration["status"]
                if configuration is not None
                else None
            ),
            "hydric_configuration_municipality_key": (
                configuration["municipality_key"]
                if configuration is not None
                else None
            ),
            "hydric_configuration_validation_error": (
                configuration["validation_error"]
                if configuration is not None
                else None
            ),
        }

    # ======================================================================
    # INDICADORES DE EVAPOTRANSPIRAÇÃO DE REFERÊNCIA — FASE 6
    # ======================================================================

    @classmethod
    def _calculate_eto_indicators(
        cls,
        values,
    ):
        """
        Calcula agregados históricos da evapotranspiração de referência.

        A ETo é recebida como dado diário da série histórica, em mm/dia.
        Este serviço não recalcula a ETo meteorológica; somente consolida
        valores finitos e não negativos já fornecidos pela camada anterior.

        None e valores inválidos não são convertidos em zero.
        """

        valid_values = []

        for value in values:
            number = cls._finite_number(
                value
            )

            if number is not None and number >= 0:
                valid_values.append(
                    number
                )

        if not valid_values:
            return None

        return {
            "eto_acumulada": round(
                sum(valid_values),
                1,
            ),
            "eto_media_diaria": round(
                sum(valid_values) / len(valid_values),
                1,
            ),
            "eto_minima": round(
                min(valid_values),
                1,
            ),
            "eto_maxima": round(
                max(valid_values),
                1,
            ),
            "dias_validos": len(valid_values),
        }


    # ======================================================================
    # INDICADORES PLUVIOMÉTRICOS
    # ======================================================================

    @classmethod
    def _calculate_precipitation_indicators(
        cls,
        values,
    ):
        """Calcula indicadores históricos de precipitação diária."""

        valid_values = []

        for value in values:
            number = cls._finite_number(
                value
            )

            if number is not None and number >= 0:
                valid_values.append(
                    number
                )

        if not valid_values:
            return None

        rainy_days = sum(
            1
            for value in valid_values
            if value > 0
        )

        total = len(valid_values)

        current_dry = 0
        longest_dry = 0

        # A série recebida é diária. Zeros consecutivos representam dias
        # efetivamente registrados sem precipitação. Valores ausentes ou
        # inválidos não são convertidos em zero e interrompem a sequência.
        for value in values:
            number = cls._finite_number(
                value
            )

            if number is None or number < 0:
                current_dry = 0
                continue

            if number == 0:
                current_dry += 1
                longest_dry = max(
                    longest_dry,
                    current_dry,
                )
            else:
                current_dry = 0

        return {
            "precipitacao_acumulada": round(
                sum(valid_values),
                1,
            ),
            "precipitacao_media_diaria": round(
                sum(valid_values) / total,
                1,
            ),
            "dias_chuvosos": rainy_days,
            "frequencia_dias_chuvosos": round(
                (rainy_days / total) * 100,
                1,
            ),
            "periodo_sem_chuva_atual": current_dry,
            "maior_periodo_sem_chuva": longest_dry,
            "precipitacao_minima": round(
                min(valid_values),
                1,
            ),
            "precipitacao_maxima": round(
                max(valid_values),
                1,
            ),
            "dias_validos": total,
        }

    # ======================================================================
    # TENDÊNCIA TÉRMICA
    # ======================================================================

    @classmethod
    def _calculate_temperature_trend(
        cls,
        values,
    ):
        """
        Classifica descritivamente a tendência da série térmica.

        A regra preserva o comportamento histórico já utilizado pelo
        ChartService: a diferença é calculada entre o primeiro e o último
        valor válido da série.

        Retorno:
            "Alta"
            "Queda"
            "Estável"
            None
        """

        if not values:
            return None

        if len(values) < 2:
            return "Estável"

        difference = values[-1] - values[0]

        if abs(difference) < 0.5:
            return "Estável"

        if difference > 0:
            return "Alta"

        return "Queda"

    @staticmethod
    def _calculate_temperature_band_counts(
        distribution,
    ):
        """
        Extrai contagens dos indicadores térmicos explicitamente nomeados
        na especificação operacional.

        ``dias_frios`` corresponde exclusivamente à classe canônica ``cold``;
        ``dias_muito_quentes`` corresponde exclusivamente à classe ``hot``;
        ``dias_temperatura_ate_zero`` corresponde exclusivamente à classe
        ``frost``. Assim, nenhuma faixa adicional ou agrupamento não definido
        pela classificação é inventado.
        """

        if distribution is None:
            return None

        return {
            "dias_frios": distribution[
                ThermalClassificationService.CLASS_COLD
            ]["quantidade"],
            "dias_muito_quentes": distribution[
                ThermalClassificationService.CLASS_HOT
            ]["quantidade"],
            "dias_temperatura_ate_zero": distribution[
                ThermalClassificationService.CLASS_FROST
            ]["quantidade"],
        }


    @staticmethod
    def _calculate_temperature_band_distribution(
        values,
    ):
        """
        Calcula a quantidade e a frequência das sete faixas térmicas
        operacionais sobre a série de temperaturas válidas.

        A classificação é delegada ao ThermalClassificationService, que
        permanece como única origem das sete faixas. Valores ausentes ou
        inválidos são excluídos e não são convertidos em zero.

        Retorna None quando não existe temperatura válida. Caso exista
        série válida, todas as sete faixas são retornadas, inclusive aquelas
        sem ocorrência, com quantidade zero e frequência 0,0.
        """

        valid_values = HistoricalClimateIndicatorService._valid_series(
            values
        )

        if not valid_values:
            return None

        classes = (
            ThermalClassificationService.CLASS_FROST,
            ThermalClassificationService.CLASS_VERY_COLD,
            ThermalClassificationService.CLASS_COLD,
            ThermalClassificationService.CLASS_COOL,
            ThermalClassificationService.CLASS_FAVORABLE,
            ThermalClassificationService.CLASS_WARM,
            ThermalClassificationService.CLASS_HOT,
        )

        counts = {classification: 0 for classification in classes}

        for value in valid_values:
            classification = ThermalClassificationService.classify(
                value
            )
            if classification in counts:
                counts[classification] += 1

        total = len(valid_values)
        return {
            classification: {
                "quantidade": counts[classification],
                "frequencia_percentual": round(
                    (counts[classification] / total) * 100,
                    1,
                ),
                "label": ThermalClassificationService.LABELS[
                    classification
                ],
            }
            for classification in classes
        }


    @staticmethod
    def _calculate_critical_temperature_frequency(
        values,
    ):
        """
        Calcula a frequência operacional de temperaturas críticas.

        Nesta etapa, são consideradas críticas somente as duas extremidades
        já documentadas pela classificação térmica operacional do projeto:

            <= 0 °C  -> geada / extremo frio
            > 28 °C  -> muito quente

        A frequência é a proporção de dias válidos da série de temperatura
        que pertencem a uma dessas duas extremidades, expressa em percentual.

        Retorna None quando não existe temperatura válida.
        """

        valid_values = HistoricalClimateIndicatorService._valid_series(
            values
        )

        if not valid_values:
            return None

        critical_days = sum(
            1
            for value in valid_values
            if (
                value <= 0
                or value > 28
            )
        )

        return round(
            (
                critical_days
                / len(valid_values)
            )
            * 100,
            1,
        )


    def _temperature_difference(
        cls,
        values,
    ):
        """
        Retorna a diferença entre o último e o primeiro valor válido.

        A diferença é descritiva e não constitui classificação agronômica.
        """

        if len(values) < 2:
            return None

        difference = values[-1] - values[0]

        if not isfinite(difference):
            return None

        return round(difference, 1)

    @classmethod
    def _valid_series(
        cls,
        values,
    ):
        """
        Retorna somente valores térmicos finitos e numericamente válidos.
        """

        valid = []

        for value in values:
            number = cls._finite_number(value)

            if number is not None:
                valid.append(number)

        return valid


    # ======================================================================
    # AMPLITUDE TÉRMICA
    # ======================================================================

    @classmethod
    def _calculate_daily_amplitude(
        cls,
        minimums,
        maximums,
    ):
        """
        Calcula a amplitude térmica para cada posição das séries.

        A posição representa o mesmo dia nas séries de mínima e máxima.
        Quando uma das temperaturas estiver ausente ou inválida, a amplitude
        daquele dia permanece None.

        A função aceita séries de comprimentos diferentes de forma defensiva:
        posições sem os dois valores necessários permanecem None.
        """

        length = max(
            len(minimums),
            len(maximums),
        )

        amplitudes = []

        for index in range(length):
            minimum = (
                minimums[index]
                if index < len(minimums)
                else None
            )

            maximum = (
                maximums[index]
                if index < len(maximums)
                else None
            )

            minimum_value = cls._finite_number(
                minimum
            )

            maximum_value = cls._finite_number(
                maximum
            )

            if (
                minimum_value is None
                or maximum_value is None
            ):
                amplitudes.append(
                    None
                )
                continue

            amplitude = (
                maximum_value
                - minimum_value
            )

            if not isfinite(
                amplitude
            ):
                amplitudes.append(
                    None
                )
                continue

            amplitudes.append(
                round(
                    amplitude,
                    1,
                )
            )

        return amplitudes

    # ======================================================================
    # NORMALIZAÇÃO SEGURA
    # ======================================================================

    @staticmethod
    def _as_list(value):
        """
        Normaliza uma entrada de série sem criar dados.
        """

        if value is None:
            return []

        if isinstance(
            value,
            (list, tuple),
        ):
            return list(
                value
            )

        return []

    @staticmethod
    def _finite_number(value):
        """
        Retorna número finito ou None.

        bool é rejeitado porque é subtipo de int em Python e não representa
        temperatura meteorológica válida.
        """

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        try:
            number = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        if not isfinite(
            number
        ):
            return None

        return number

    @classmethod
    def _mean(cls, values):
        """
        Calcula média somente sobre valores finitos já validados.
        """

        if not values:
            return None

        valid = []

        for value in values:
            number = cls._finite_number(
                value
            )

            if number is not None:
                valid.append(
                    number
                )

        if not valid:
            return None

        return round(
            sum(valid)
            / len(valid),
            1,
        )


# ============================================================================
# REGISTRO DE AUDITORIA - FASE 5.4
# ============================================================================
#
# Objetivo:
#     Evoluir a camada especializada para indicadores históricos, mantendo
#     amplitude térmica e tendência térmica validadas e incorporando a
#     frequência operacional de temperaturas críticas.
#     sem transferir inteligência para o HistoryService e sem alterar o
#     frontend.
#
# Fonte dos dados:
#     HistoryService.
#
# Entrada principal:
#     temperatura_minima
#     temperatura_maxima
#     dias
#
# Regras implementadas:
#     amplitude_termica = temperatura_maxima - temperatura_minima
#     tendencia_termica = classificação descritiva pela diferença entre o
#     primeiro e o último valor válido da série de temperatura
#     frequencia_temperaturas_criticas = percentual de valores válidos nas
#     extremidades <= 0 °C ou > 28 °C da classificação operacional
#     diferença absoluta < 0,5 °C = Estável
#     diferença positiva = Alta
#     diferença negativa = Queda
#
# Tratamento de ausência:
#     None permanece None.
#
# Tratamento de valores inválidos:
#     None, bool, texto não numérico, NaN e infinito são rejeitados.
#
# Segurança arquitetural:
#     - sem ORM;
#     - sem API;
#     - sem acesso ao frontend;
#     - sem FRI;
#     - sem severidade;
#     - sem confiança;
#     - sem recomendações;
#     - sem limiares agronômicos arbitrários;
#     - sem duplicação das sete faixas térmicas.
#
# Indicadores incorporados nesta versão:
#     frequência das sete faixas térmicas;
#     quantidade por faixa;
#     frequência percentual por faixa;
#     rótulo canônico de cada faixa;
#     dias_frios (classe cold);
#     dias_muito_quentes (classe hot);
#     dias_temperatura_ate_zero (classe frost).
#
# Próximas etapas previstas, ainda não implementadas neste arquivo:
#     contagens específicas de dias frios;
#     contagens específicas de dias muito quentes;
#     quantidade de dias <= 0 °C;
#     extremos térmicos.
#
# A integração com DashboardService e o contrato municipal será feita somente
# após a validação desta camada especializada.
# ============================================================================

# ============================================================================
# NOTA DE ESCOPO — FREQUÊNCIA CRÍTICA
# ============================================================================
#
# A especificação oficial estabelece sete faixas térmicas operacionais e
# relaciona explicitamente a implementação da frequência de temperaturas
# críticas, dias frios, dias muito quentes e dias <= 0 °C como indicadores
# progressivos. A definição utilizada nesta versão é deliberadamente restrita
# às duas extremidades da classificação: <= 0 °C e > 28 °C.
#
# Esta escolha não constitui recomendação agronômica nem substitui futuras
# métricas específicas de contagem. Ela fornece uma frequência percentual
# única e rastreável, sem introduzir limiares externos à especificação.
#
# A frequência usa somente temperaturas válidas da série fornecida. Portanto:
#     - None não entra no denominador;
#     - bool não é aceito como temperatura;
#     - NaN e infinito são rejeitados;
#     - ausência de série retorna None;
#     - nenhum valor ausente é convertido em zero.
#
# O cálculo permanece no backend especializado e não é executado pelo
# HistoryService, DashboardService, DashboardFacade ou frontend.
# ============================================================================


# ============================================================================
# NOTA DE ESCOPO — DISTRIBUIÇÃO DAS FAIXAS TÉRMICAS
# ============================================================================
#
# A distribuição histórica utiliza as mesmas sete classes canônicas do
# ThermalClassificationService, evitando qualquer reprodução de limites neste
# serviço especializado.
#
# Para cada classe são disponibilizados: quantidade de dias válidos, frequência
# percentual e rótulo canônico. A soma das quantidades corresponde ao número de
# temperaturas válidas da série. As frequências são arredondadas a uma casa
# decimal, portanto sua soma exibida pode variar em 0,1 ponto percentual por
# efeito exclusivo do arredondamento.
#
# Ausência de série válida retorna None. Em uma série válida, uma faixa sem
# ocorrência permanece explicitamente representada com quantidade 0 e frequência
# 0,0%, sem confundir ausência de série com ausência de ocorrência.
#
# ============================================================================

# ============================================================================
# NOTA DE ESCOPO — CONTAGENS TÉRMICAS
# ============================================================================
#
# A especificação oficial determina os indicadores "dias frios", "dias muito
# quentes" e "dias com temperatura <= 0 °C", mas não define um agrupamento
# adicional de faixas para "dias frios". Para evitar inferência não documentada,
# esta versão usa a classe canônica cujo identificador corresponde diretamente
# ao indicador: cold, hot e frost, respectivamente.
#
# Caso a especificação seja posteriormente refinada para que "dias frios"
# represente mais de uma faixa, a regra deverá ser alterada mediante nova
# definição formal e auditoria específica.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA - FASE 5.5
# ============================================================================
#
# Objetivo:
#     Incorporar os indicadores pluviométricos históricos previstos na
#     especificação oficial, mantendo os indicadores térmicos já validados.
#
# Fonte dos dados:
#     HistoryService -> série histórica diária ``precipitacao``.
#
# Indicadores incorporados:
#     precipitacao_acumulada;
#     precipitacao_media_diaria;
#     dias_chuvosos;
#     frequencia_dias_chuvosos;
#     periodo_sem_chuva_atual;
#     maior_periodo_sem_chuva;
#     precipitacao_minima;
#     precipitacao_maxima;
#     precipitacao_dias_validos.
#
# Regras de qualidade:
#     - zero representa precipitação diária efetivamente registrada como zero;
#     - None e valores inválidos não são convertidos em zero;
#     - valores negativos de precipitação são rejeitados;
#     - ausência de dado não entra no denominador;
#     - ausência de dado interrompe a sequência de período sem chuva;
#     - dia chuvoso é definido operacionalmente como precipitação > 0;
#     - nenhum limiar agronômico externo foi introduzido.
#
# Segurança arquitetural:
#     - cálculo permanece no serviço especializado;
#     - sem ORM;
#     - sem API externa;
#     - sem frontend;
#     - sem FRI;
#     - sem severidade;
#     - sem recomendações agronômicas.
# ============================================================================

# ============================================================================
# REGISTRO DE AUDITORIA - FASE 6.0 — ETo
# ============================================================================
#
# Objetivo:
#     Incorporar o transporte e a consolidação histórica da ETo diária,
#     mantendo integralmente os indicadores térmicos e pluviométricos da
#     Fase 5.
#
# Fonte:
#     HistoryService -> série histórica diária ``eto_mm_day``.
#
# Unidade:
#     milímetros por dia (mm/dia).
#
# Indicadores incorporados:
#     eto_mm_day; eto_acumulada; eto_media_diaria; eto_minima;
#     eto_maxima; eto_dias_validos.
#
# Regras:
#     - a ETo meteorológica não é recalculada neste serviço;
#     - somente valores finitos e >= 0 são considerados válidos;
#     - None, NaN, infinito, texto inválido e valores negativos não entram
#       nos agregados;
#     - dado ausente não é convertido em zero;
#     - ausência de valores válidos retorna None para os agregados;
#     - o cálculo permanece no backend especializado.
#
# Segurança arquitetural:
#     - sem ORM; sem API externa; sem frontend; sem FRI;
#     - sem severidade; sem recomendações agronômicas;
#     - indicadores da Fase 5 preservados.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA - FASE 6.2 — INTEGRAÇÃO
# ============================================================================
# HydricBalanceService é a única origem das regras do balanço hídrico.
# CAD e ARM inicial permanecem parâmetros explícitos; sem configuração, o
# balanço retorna NOT_CONFIGURED sem interferir nos demais indicadores.
# Os indicadores térmicos, pluviométricos e ETo da versão anterior são
# preservados. Não há ORM, API, frontend, FRI ou regra agronômica nova aqui.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 6.2 — CONFIGURAÇÃO MUNICIPAL
# ============================================================================
#
# Evolução desta versão:
#
#     HydricBalanceConfigurationService
#         ->
#     HistoricalClimateIndicatorService
#         ->
#     HydricBalanceService
#
# A configuração municipal passou a ser consultável pelo serviço especializado
# quando os parâmetros CAD/ARM não são explicitamente fornecidos.
#
# Regras preservadas:
#     - nenhuma CAD é inventada;
#     - nenhum ARM inicial é inventado;
#     - ausência de configuração permanece NOT_CONFIGURED;
#     - configuração inválida não é silenciosamente corrigida;
#     - parâmetros explicitamente fornecidos continuam tendo prioridade;
#     - o cálculo continua exclusivamente no HydricBalanceService;
#     - ETo continua sendo referência atmosférica;
#     - precipitação e ETo ausentes não são convertidas em zero;
#     - nenhum cálculo de FRI/geada foi alterado;
#     - nenhum cálculo é transferido para o frontend.
#
# A chave municipal é fornecida pela camada de integração. Esta versão não
# escolhe arbitrariamente identificador municipal nem cria valores de CAD.
#
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 6.2 — CORREÇÃO DA EXPOSIÇÃO DO METADADO
# ============================================================================
#
# Diagnóstico funcional:
#     A consulta à configuração municipal já ocorria corretamente no fluxo
#     calculate(), porém os metadados de configuração documentados pela etapa
#     anterior não estavam sendo materializados no dicionário retornado.
#
# Correção:
#     Foram adicionados ao contrato de saída:
#         - hydric_configuration_version;
#         - hydric_configuration_status;
#         - hydric_configuration_municipality_key;
#         - hydric_configuration_validation_error.
#
# Garantias:
#     - não altera as equações do balanço hídrico;
#     - não altera ETo;
#     - não altera indicadores térmicos ou pluviométricos;
#     - não altera FRI;
#     - não cria regra agronômica;
#     - mantém None quando nenhuma configuração municipal foi consultada.
#
# Regra obrigatória do projeto:
#     quantidade de linhas final >= quantidade de linhas do arquivo original.
#
# ============================================================================
