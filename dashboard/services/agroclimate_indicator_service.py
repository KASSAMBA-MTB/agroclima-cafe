"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo destino.: dashboard/services/agroclimate_indicator_service.py
Versão..........: FASE 2 — primeira implementação

DESCRIÇÃO
---------
Serviço especializado responsável pelos primeiros indicadores agroclimáticos
derivados a partir dos dados meteorológicos já estruturados pelo backend.

RESPONSABILIDADES
-----------------
- receber WeatherDTO ou dicionário compatível com o contrato meteorológico;
- normalizar os campos utilizados pelos indicadores;
- produzir a classificação térmica operacional;
- preservar explicitamente a ausência de dados;
- preparar uma única camada de cálculo para os próximos indicadores.

REGRA ARQUITETURAL
------------------
A camada climática (clima.services) permanece responsável por aquisição,
normalização de origem e atualização dos dados meteorológicos.

A camada dashboard.services recebe os dados já estruturados e consolida
indicadores destinados ao contrato municipal.

Este serviço NÃO acessa API, banco de dados ou frontend.

Este serviço NÃO calcula:
- FRI;
- severidade;
- confiança de risco;
- regras de geada;
- alertas;
- recomendações.

Essas responsabilidades permanecem nas cadeias canônicas já estabilizadas.

IMPORTANTE
----------
A classificação térmica não é reproduzida neste arquivo. Ela é delegada ao
ThermalClassificationService existente em dashboard.services, mantendo uma
única origem para as sete faixas térmicas.

A ausência de dado permanece como None / unavailable / Sem dado.
Nenhum valor ausente é convertido para zero.

INTEGRAÇÃO
----------
Este arquivo é criado isoladamente na FASE 2. A integração ao map_point,
MapService e DashboardFacade ocorrerá somente na FASE 3, após validação deste
serviço.
===============================================================================
"""

from math import isfinite

from dashboard.services.thermal_classification_service import (
    ThermalClassificationService,
)


class AgroClimateIndicatorService:
    """
    Serviço especializado de indicadores agroclimáticos derivados.

    O serviço é deliberadamente independente de banco de dados, API e
    apresentação. Recebe dados já estruturados e devolve um contrato simples
    para a camada de integração.
    """

    INDICATOR_TEMPERATURE_CLASS = "temperature_class"
    INDICATOR_TEMPERATURE_CLASS_LABEL = "temperature_class_label"
    INDICATOR_PRECIPITATION_24H_CLASS = "precipitation_24h_class"
    INDICATOR_PRECIPITATION_24H_CLASS_LABEL = "precipitation_24h_class_label"

    # ==========================================================
    # CLASSIFICAÇÃO OPERACIONAL DE PRECIPITAÇÃO 24H
    # ==========================================================
    # Critérios operacionais adotados pelo AgroClima Café.
    # Não representam uma classificação oficial do INMET ou da Embrapa.
    PRECIPITATION_CLASS_NONE = "none"
    PRECIPITATION_CLASS_LOW = "low"
    PRECIPITATION_CLASS_MODERATE = "moderate"
    PRECIPITATION_CLASS_HIGH = "high"
    PRECIPITATION_CLASS_VERY_HIGH = "veryHigh"
    PRECIPITATION_CLASS_EXTREME = "extreme"

    PRECIPITATION_LABELS = {
        PRECIPITATION_CLASS_NONE: "Sem chuva",
        PRECIPITATION_CLASS_LOW: "Chuva baixa",
        PRECIPITATION_CLASS_MODERATE: "Chuva moderada",
        PRECIPITATION_CLASS_HIGH: "Chuva alta",
        PRECIPITATION_CLASS_VERY_HIGH: "Chuva muito alta",
        PRECIPITATION_CLASS_EXTREME: "Chuva extrema",
    }

    PRECIPITATION_LIMIT_LOW = 5.0
    PRECIPITATION_LIMIT_MODERATE = 20.0
    PRECIPITATION_LIMIT_HIGH = 50.0
    PRECIPITATION_LIMIT_VERY_HIGH = 80.0

    # ==========================================================
    # CONSOLIDAÇÃO DOS INDICADORES
    # ==========================================================

    @classmethod
    def calculate(cls, weather_data):
        """
        Calcula os primeiros indicadores autorizados da FASE 2.

        A entrada pode ser:
        - um WeatherDTO;
        - um objeto compatível com o contrato meteorológico;
        - um dicionário com os mesmos nomes de campos.

        O método não consulta banco de dados e não executa regras de risco.
        """
        if weather_data is None:
            return cls.empty_result()

        temperature = cls._get(
            weather_data,
            "temperature",
        )

        precipitation_1h = cls._get_first(
            weather_data,
            "precipitation_1h_mm",
            "precipitacao_1h",
        )

        precipitation_24h = cls._get_first(
            weather_data,
            "precipitation_24h_mm",
            "precipitacao_24h",
        )

        return {
            "temperature": cls._finite_number(
                temperature
            ),
            "temperature_class": cls.classify_temperature(
                temperature
            ),
            "temperature_class_label": cls.classify_temperature_label(
                temperature
            ),
            "precipitation_1h_mm": cls._finite_number(
                precipitation_1h
            ),
            "precipitation_24h_mm": cls._finite_number(
                precipitation_24h
            ),
            "precipitation_24h_class": cls.classify_precipitation_24h(
                precipitation_24h
            ),
            "precipitation_24h_class_label": cls.classify_precipitation_24h_label(
                precipitation_24h
            ),
        }

    @classmethod
    def calculate_from_dto(cls, weather_dto):
        """
        Ponto de entrada semântico para integração explícita com WeatherDTO.

        Não cria uma segunda lógica de cálculo; delega ao método canônico
        calculate().
        """
        return cls.calculate(
            weather_dto
        )

    # ==========================================================
    # CLASSIFICAÇÃO TÉRMICA
    # ==========================================================

    @classmethod
    def classify_temperature(cls, temperature):
        """
        Delega a classificação térmica ao serviço canônico do dashboard.

        Não existem limites de temperatura duplicados neste serviço.
        """
        return ThermalClassificationService.classify(
            temperature
        )

    @classmethod
    def classify_temperature_label(cls, temperature):
        """
        Delega o rótulo da classificação térmica ao serviço canônico.
        """
        return ThermalClassificationService.label(
            temperature
        )

    # ==========================================================
    # CLASSIFICAÇÃO OPERACIONAL DE PRECIPITAÇÃO 24H
    # ==========================================================

    @classmethod
    def classify_precipitation_24h(cls, precipitation):
        """Classifica o acumulado de precipitação das últimas 24 horas."""
        value = cls._finite_number(precipitation)

        if value is None:
            return cls.PRECIPITATION_CLASS_NONE

        if value <= 0:
            return cls.PRECIPITATION_CLASS_NONE

        if value <= cls.PRECIPITATION_LIMIT_LOW:
            return cls.PRECIPITATION_CLASS_LOW

        if value <= cls.PRECIPITATION_LIMIT_MODERATE:
            return cls.PRECIPITATION_CLASS_MODERATE

        if value <= cls.PRECIPITATION_LIMIT_HIGH:
            return cls.PRECIPITATION_CLASS_HIGH

        if value <= cls.PRECIPITATION_LIMIT_VERY_HIGH:
            return cls.PRECIPITATION_CLASS_VERY_HIGH

        return cls.PRECIPITATION_CLASS_EXTREME

    @classmethod
    def classify_precipitation_24h_label(cls, precipitation):
        """Retorna o rótulo da classificação operacional de precipitação 24h."""
        if cls._finite_number(precipitation) is None:
            return "Sem dado"

        classification = cls.classify_precipitation_24h(
            precipitation
        )

        return cls.PRECIPITATION_LABELS.get(
            classification,
            "Sem dado",
        )


    # ==========================================================
    # NORMALIZAÇÃO
    # ==========================================================

    @classmethod
    def normalize_weather_data(cls, weather_data):
        """
        Normaliza os campos meteorológicos utilizados pela FASE 2.

        Campos ausentes permanecem como None.
        """
        if weather_data is None:
            return cls.empty_weather_data()

        return {
            "temperature": cls._finite_number(
                cls._get(
                    weather_data,
                    "temperature",
                )
            ),
            "precipitation_1h_mm": cls._finite_number(
                cls._get_first(
                    weather_data,
                    "precipitation_1h_mm",
                    "precipitacao_1h",
                )
            ),
            "precipitation_24h_mm": cls._finite_number(
                cls._get_first(
                    weather_data,
                    "precipitation_24h_mm",
                    "precipitacao_24h",
                )
            ),
            "precipitation_24h_class": cls.classify_precipitation_24h(
                cls._get_first(
                    weather_data,
                    "precipitation_24h_mm",
                    "precipitacao_24h",
                )
            ),
            "precipitation_24h_class_label": cls.classify_precipitation_24h_label(
                cls._get_first(
                    weather_data,
                    "precipitation_24h_mm",
                    "precipitacao_24h",
                )
            ),
        }

    # ==========================================================
    # ESTADO SEM DADOS
    # ==========================================================

    @classmethod
    def empty_result(cls):
        """
        Retorna o contrato explícito para ausência total de dados.

        Nenhum indicador ausente é convertido para zero.
        """
        return {
            "temperature": None,
            "temperature_class": (
                ThermalClassificationService.CLASS_UNAVAILABLE
            ),
            "temperature_class_label": (
                ThermalClassificationService.LABELS[
                    ThermalClassificationService.CLASS_UNAVAILABLE
                ]
            ),
            "precipitation_1h_mm": None,
            "precipitation_24h_mm": None,
            "precipitation_24h_class": cls.PRECIPITATION_CLASS_NONE,
            "precipitation_24h_class_label": "Sem dado",
        }

    @staticmethod
    def empty_weather_data():
        """
        Retorna a estrutura normalizada para ausência de dados.
        """
        return {
            "temperature": None,
            "precipitation_1h_mm": None,
            "precipitation_24h_mm": None,
        }

    # ==========================================================
    # LEITURA DE CAMPOS
    # ==========================================================

    @staticmethod
    def _get(data, field):
        """
        Lê um campo de objeto/DTO ou de dicionário.
        """
        if isinstance(
            data,
            dict,
        ):
            return data.get(
                field
            )

        return getattr(
            data,
            field,
            None,
        )

    @classmethod
    def _get_first(cls, data, *fields):
        """
        Retorna o primeiro valor efetivamente disponível.

        None não é transformado em zero.
        """
        for field in fields:
            value = cls._get(
                data,
                field,
            )

            if value is not None:
                return value

        return None

    # ==========================================================
    # CONVERSÃO NUMÉRICA SEGURA
    # ==========================================================

    @staticmethod
    def _finite_number(value):
        """
        Converte somente valores numéricos finitos para float.

        Retorna None para:
        - None;
        - booleanos;
        - valores não numéricos;
        - NaN;
        - infinito.
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


# Ponto de entrada funcional para futura integração.
indicator_service = AgroClimateIndicatorService
