"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: kpi_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
Serviço responsável por consolidar os indicadores (KPIs) exibidos no
Dashboard Principal.

Os dados meteorológicos chegam pelo contexto canônico fornecido pelo
DashboardService. O KPIService consolida a apresentação dos KPIs e
encaminha ao Índice AgroClima a janela pluviométrica correta.

Versão..........: 2.7
===============================================================================
"""

from django.utils import timezone

from core.intelligence.agroclima_index import AgroClimaIndex
from clima.models import HistoricalWeatherDaily
from clima.services.weather_service import WeatherService
from municipios.models import Municipio


class KPIService:
    """
    Serviço responsável pelo carregamento dos indicadores do Dashboard.

    Responsabilidades:

    - consumir exclusivamente o contexto meteorológico canônico;
    - preparar os KPIs visuais;
    - calcular o Índice AgroClima com a precipitação de 7 dias;
    - disponibilizar os dados estruturados para a camada de Inteligência;
    - manter evidência histórica real de geadas;
    - manter um retorno seguro quando não existem municípios.

    Semântica de precipitação:

        chuva_agora
            condição meteorológica atual.

        precipitacao_1h
            janela móvel de 1 hora.

        precipitacao_24h
            janela móvel de 24 horas.

        precipitation
            alias legado do indicador operacional de 24 horas.
            É mantido apenas para compatibilidade.

        precipitation_7d_mm
            janela histórica D-6 ... D, utilizada pelo IAC.
            A fonte e a agregação pertencem ao DashboardService/
            HistoryService; o KPIService não recalcula essa janela.
    """

    def __init__(self):
        self.weather = WeatherService()
        self.iac = AgroClimaIndex()

    # ==========================================================
    # KPIs
    # ==========================================================

    def get_kpis(self, canonical_context=None):
        """
        Obtém e consolida os indicadores climáticos.

        O DashboardService fornece o contexto meteorológico canônico.

        O KPIService não realiza aquisição meteorológica própria e não
        calcula janelas temporais. Para precipitação, preserva a separação
        entre condição atual, 1h, 24h e 7 dias.
        """

        municipios = list(
            Municipio.objects
            .all()
            .order_by("nome")
        )

        if not municipios:
            return self._empty()

        # ======================================================
        # MUNICÍPIO DE REFERÊNCIA
        # ======================================================

        municipio = (
            canonical_context.get("municipio")
            if canonical_context
            else None
        )

        if municipio is None:
            municipio = municipios[0]

        # ======================================================
        # CONTEXTO METEOROLÓGICO CANÔNICO
        # ======================================================

        if canonical_context is None:
            return self._empty()

        observation = canonical_context.get("observation")

        temperature = self._to_float(
            canonical_context.get("temperature")
        )

        humidity = self._to_float(
            canonical_context.get("humidity")
        )

        precipitation_1h = self._to_float(
            canonical_context.get("precipitation_1h_mm")
        )

        precipitation_24h = self._to_float(
            canonical_context.get("precipitation_24h_mm")
        )

        precipitation_7d = self._to_float(
            canonical_context.get("precipitation_7d_mm")
        )

        eto_mm_day = self._to_float(
            canonical_context.get("eto_mm_day")
        )

        precipitation_24h_values = canonical_context.get(
            "precipitation_24h_values",
            [],
        )

        # ======================================================
        # CONTRATO METEOROLÓGICO CANÔNICO
        # ======================================================

        rain_now = canonical_context.get("rain_now")

        wind_speed = self._to_float(
            canonical_context.get("wind_speed")
        )

        cloud_cover = self._to_float(
            canonical_context.get("cloud_cover")
        )

        # Compatibilidade com WeatherObservation legado.
        rain_now = self._weather_value(
            observation,
            "rain_now",
            "chuva_agora",
        )

        precipitation_1h = self._to_float(
            self._weather_value(
                observation,
                "precipitation_1h_mm",
                "precipitacao_1h",
            )
        )

        # ======================================================
        # ÍNDICE AGROCLIMA
        # ======================================================
        #
        # O componente pluviométrico do IAC utiliza a janela
        # canônica de 7 dias (mm/semana).
        #
        # A precipitação de 24h permanece exclusiva dos KPIs
        # operacionais e não é usada como substituto.
        #
        # Nenhuma agregação temporal é executada aqui.
        # ======================================================

        indice = self.iac.calculate(
            temperature=(
                temperature
                if temperature is not None
                else 0
            ),
            humidity=(
                humidity
                if humidity is not None
                else 0
            ),
            precipitation=(
                precipitation_7d
                if precipitation_7d is not None
                else 0
            ),
            frost_level="low",
            hail_level="low",
        )

        # ======================================================
        # DATA/HORA DA ATUALIZAÇÃO
        # ======================================================

        now = timezone.localtime()

        analysis_date = (
            observation.observation_time
            if observation is not None
            and observation.observation_time is not None
            else now
        )

        # ======================================================
        # HISTÓRICO REAL DE GEADAS
        # ======================================================

        historical = self._get_historical_frost_context(
            municipio
        )

        # ======================================================
        # RETORNO CONSOLIDADO
        # ======================================================

        return {
            # ==================================================
            # IDENTIDADE DO MUNICÍPIO DE REFERÊNCIA
            # ==================================================

            "municipio_id": municipio.id,

            "municipio_nome": municipio.nome,

            # ==================================================
            # KPIs VISUAIS
            # ==================================================

            "temperatura_media": (
                round(
                    temperature,
                    1,
                )
                if temperature is not None
                else None
            ),

            # ETo diária regional proveniente exclusivamente do
            # contexto meteorológico canônico.
            "eto_mm_day": (
                round(
                    eto_mm_day,
                    2,
                )
                if eto_mm_day is not None
                else None
            ),

            # Campo legado preservado para compatibilidade.
            # Sua semântica é explicitamente a mesma janela
            # operacional de 24h exposta por precipitacao_24h.
            "precipitacao": (
                round(
                    precipitation_24h,
                    1,
                )
                if precipitation_24h is not None
                else None
            ),

            # Contrato meteorológico canônico.
            "chuva_agora": rain_now,

            "precipitacao_1h": (
                round(
                    precipitation_1h,
                    1,
                )
                if precipitation_1h is not None
                else None
            ),

            "precipitacao_24h": (
                round(
                    precipitation_24h,
                    1,
                )
                if precipitation_24h is not None
                else None
            ),

            # Média municipal utilizada pelo cartão "Chuva (24h)".
            "precipitacao_24h_media": (
                round(
                    precipitation_24h,
                    2,
                )
                if precipitation_24h is not None
                else None
            ),

            "precipitacao_24h_municipios": (
                len(precipitation_24h_values)
                if isinstance(
                    precipitation_24h_values,
                    (list, tuple),
                )
                else 0
            ),

            "precipitacao_24h_total_municipios": (
                len(municipios)
            ),

            # As janelas 7d/30d permanecem no contexto canônico.
            # São expostas também aqui apenas como leitura do mesmo
            # contrato, sem nova consulta ou recálculo.
            "precipitacao_7d": (
                round(
                    precipitation_7d,
                    1,
                )
                if precipitation_7d is not None
                else None
            ),

            "precipitacao_30d": (
                self._to_float(
                    canonical_context.get(
                        "precipitation_30d_mm"
                    )
                )
                if canonical_context.get(
                    "precipitation_30d_mm"
                ) is not None
                else None
            ),

            # ==================================================
            # GEADAS / GRANIZO
            # ==================================================

            "geadas": 0,

            "granizo": 0,

            # ==================================================
            # TERRITÓRIO
            # ==================================================

            "municipios": Municipio.objects.count(),

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "indice_agroclima": indice["index"],

            "classificacao_agroclima": (
                indice["classification"]
            ),

            "cor_agroclima": (
                indice["color"]
            ),

            "icone_agroclima": (
                indice["icon"]
            ),

            # ==================================================
            # ATUALIZAÇÃO
            # ==================================================

            "ultima_atualizacao": now,

            "ultima_atualizacao_str": (
                now.strftime(
                    "%d/%m/%Y %H:%M"
                )
            ),

            # ==================================================
            # STATUS GERAL
            # ==================================================

            "status_dashboard": {
                "status": "normal",
                "mensagem": (
                    f'Condição '
                    f'{indice["classification"]}'
                ),
            },

            # ==================================================
            # DADOS PARA A CAMADA DE INTELIGÊNCIA
            # ==================================================

            "temperature": temperature,

            "humidity": humidity,

            "wind_speed": wind_speed,

            "cloud_cover": cloud_cover,

            "altitude": (
                int(municipio.altitude)
                if municipio.altitude is not None
                else None
            ),

            # Alias legado: preserva a semântica de 24h.
            "precipitation": precipitation_24h,

            # Variáveis canônicas.
            "rain_now": rain_now,

            "precipitation_1h_mm": precipitation_1h,

            "precipitation_24h_mm": precipitation_24h,

            "precipitation_7d_mm": precipitation_7d,

            "precipitation_30d_mm": (
                self._to_float(
                    canonical_context.get(
                        "precipitation_30d_mm"
                    )
                )
                if canonical_context.get(
                    "precipitation_30d_mm"
                ) is not None
                else None
            ),

            "analysis_date": analysis_date,

            # ==================================================
            # EVIDÊNCIA HISTÓRICA REAL DE GEADAS
            # ==================================================

            "historical_frost": (
                historical["historical_frost"]
            ),

            "historical_total_days": (
                historical["historical_total_days"]
            ),

            "historical_frost_days": (
                historical["historical_frost_days"]
            ),

            "historical_frost_frequency": (
                historical["historical_frost_frequency"]
            ),

            "historical_frost_episodes": (
                historical["historical_frost_episodes"]
            ),

            "historical_min_temperature": (
                historical["historical_min_temperature"]
            ),

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "scores": indice["scores"],
        }

    # ==========================================================
    # AUDITORIA ETO — VERSÃO 2.7
    # ==========================================================
    # ETo é somente transportada do contexto canônico.
    # Não há aquisição, cálculo ou nova agregação neste serviço.
    # ==========================================================

    # ==========================================================
    # HISTÓRICO REAL DE GEADAS
    # ==========================================================

    def _get_historical_frost_context(
        self,
        municipio,
    ):
        """
        Consolida a evidência histórica real de geadas para o
        município utilizado pelo contexto principal do KPIService.

        Fonte:
            HistoricalWeatherDaily

        Critério de geada:
            temperatura_minima <= 0 °C

        Regras:
            - considera somente registros persistidos;
            - não utiliza previsão meteorológica;
            - mantém a contagem total de registros;
            - calcula frequência a partir de dias de geada / total;
            - calcula episódios por continuidade diária;
            - preserva a mínima histórica real;
            - ausência de registros não é convertida em ocorrência.
        """

        records = (
            HistoricalWeatherDaily.objects
            .filter(
                station__municipio=municipio
            )
            .order_by(
                "data"
            )
        )

        total_days = 0
        frost_days = 0
        frost_dates = []
        minimum_temperature = None

        for record in records:
            total_days += 1

            minimum = self._to_float(
                record.temperatura_minima
            )

            if minimum is None:
                continue

            if (
                minimum_temperature is None
                or minimum < minimum_temperature
            ):
                minimum_temperature = minimum

            if minimum <= 0:
                frost_days += 1

                if record.data is not None:
                    frost_dates.append(
                        record.data
                    )

        frequency = (
            frost_days / total_days
            if total_days > 0
            else 0.0
        )

        return {
            "historical_frost": (
                frost_days > 0
            ),

            "historical_total_days": (
                total_days
            ),

            "historical_frost_days": (
                frost_days
            ),

            "historical_frost_frequency": (
                frequency
            ),

            "historical_frost_episodes": (
                self._count_frost_episodes(
                    frost_dates
                )
            ),

            "historical_min_temperature": (
                minimum_temperature
            ),
        }

    @staticmethod
    def _count_frost_episodes(
        frost_dates,
    ):
        """
        Conta episódios distintos de geada.

        Datas consecutivas pertencem ao mesmo episódio.
        Uma nova ocorrência após uma lacuna de pelo menos
        um dia inicia novo episódio.
        """

        if not frost_dates:
            return 0

        unique_dates = sorted(
            set(frost_dates)
        )

        episodes = 1

        for previous, current in zip(
            unique_dates,
            unique_dates[1:],
        ):
            if (
                current - previous
            ).days > 1:
                episodes += 1

        return episodes

    # ==========================================================
    # LEITURA COMPATÍVEL DO OBJETO METEOROLÓGICO
    # ==========================================================

    @staticmethod
    def _weather_value(
        observation,
        *attribute_names,
    ):
        """
        Lê um atributo meteorológico preservando o contrato do DTO.

        O contrato principal utiliza os nomes em inglês definidos pelo
        WeatherDTO. Como proteção de compatibilidade, também reconhece
        os nomes persistidos em português do modelo WeatherObservation.

        Esta compatibilidade não cria dados nem altera valores.
        """

        if observation is None:
            return None

        for attribute_name in attribute_names:
            value = getattr(
                observation,
                attribute_name,
                None,
            )

            if value is not None:
                return value

        return None

    # ==========================================================
    # CONVERSÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _to_float(value):
        """
        Converte um valor para float de maneira segura.

        Retorna None quando o valor não existe ou não pode ser
        convertido.
        """

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    # ==========================================================
    # RETORNO PADRÃO
    # ==========================================================

    def _empty(self):
        """
        Retorno padrão quando não existem municípios cadastrados.
        """

        now = timezone.localtime()

        return {
            # ==================================================
            # IDENTIDADE
            # ==================================================

            "municipio_id": None,

            "municipio_nome": None,

            # ==================================================
            # KPIs
            # ==================================================

            "temperatura_media": None,

            "precipitacao": None,

            "chuva_agora": None,

            "precipitacao_1h": None,

            "precipitacao_24h": None,

            "precipitacao_24h_media": None,

            "precipitacao_24h_municipios": 0,

            "precipitacao_24h_total_municipios": 0,

            "precipitacao_7d": None,

            "eto_mm_day": None,

            "precipitacao_30d": None,

            "geadas": 0,

            "granizo": 0,

            "municipios": 0,

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "indice_agroclima": "--",

            "classificacao_agroclima": "--",

            "cor_agroclima": "#999999",

            "icone_agroclima": (
                "bi-dash-circle"
            ),

            # ==================================================
            # ATUALIZAÇÃO
            # ==================================================

            "ultima_atualizacao": now,

            "ultima_atualizacao_str": (
                now.strftime(
                    "%d/%m/%Y %H:%M"
                )
            ),

            # ==================================================
            # STATUS
            # ==================================================

            "status_dashboard": {
                "status": "offline",
                "mensagem": (
                    "Nenhum município cadastrado."
                ),
            },

            # ==================================================
            # INTELIGÊNCIA
            # ==================================================

            "temperature": None,

            "humidity": None,

            "wind_speed": None,

            "cloud_cover": None,

            "altitude": None,

            "precipitation": None,

            "rain_now": None,

            "precipitation_1h_mm": None,

            "precipitation_24h_mm": None,

            "precipitation_7d_mm": None,

            "precipitation_30d_mm": None,

            "analysis_date": now,

            # ==================================================
            # HISTÓRICO REAL DE GEADAS
            # ==================================================

            "historical_frost": False,

            "historical_total_days": 0,

            "historical_frost_days": 0,

            "historical_frost_frequency": 0.0,

            "historical_frost_episodes": 0,

            "historical_min_temperature": None,

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "scores": {},
        }
