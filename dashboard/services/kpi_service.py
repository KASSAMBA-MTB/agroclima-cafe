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

Os dados meteorológicos são obtidos pelo WeatherService através de
WeatherDTO. O KPIService utiliza os nomes de atributos definidos pelo DTO
e disponibiliza também os campos estruturados utilizados pela camada
de Inteligência.

Versão..........: 2.5
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

    - obter a observação meteorológica atual;
    - calcular o Índice AgroClima;
    - preparar os KPIs visuais;
    - disponibilizar os dados estruturados para a camada de Inteligência;
    - manter um retorno seguro quando não existem municípios.
    """

    def __init__(self):

        self.weather = WeatherService()

        self.iac = AgroClimaIndex()

    # ==========================================================
    # KPIs
    # ==========================================================

    def get_kpis(self):
        """
        Obtém e consolida os indicadores climáticos.

        O WeatherService retorna um WeatherDTO.

        Os atributos meteorológicos básicos são obtidos do
        WeatherDTO. Para precipitação, o contrato canônico
        distingue explicitamente:

            rain_now
            precipitation_1h_mm
            precipitation_24h_mm

        O atributo legado precipitation permanece apenas para
        compatibilidade com a cadeia existente.
        """

        municipios = list(
            Municipio.objects
            .all()
            .order_by("nome")
        )

        if not municipios:

            return self._empty()

        # ======================================================
        # OBSERVAÇÃO METEOROLÓGICA DO MUNICÍPIO DE REFERÊNCIA
        # ======================================================
        #
        # Temperatura, umidade, vento, nuvens e Índice AgroClima
        # permanecem associados ao primeiro município da cadeia
        # histórica desta classe.
        #
        # A precipitação de 24h, porém, é consolidada separadamente
        # para TODOS os municípios monitorados.
        # ======================================================

        municipio = municipios[0]

        observation = (
            self.weather.update_current_weather(
                municipio
            )
        )

        # ======================================================
        # MÉDIA MUNICIPAL DE PRECIPITAÇÃO — 24 HORAS
        # ======================================================
        #
        # Regra canônica:
        #
        #     soma das precipitações_24h válidas
        #     ---------------------------------
        #          quantidade de municípios
        #
        # O cálculo utiliza exclusivamente precipitation_24h_mm
        # fornecido pelo WeatherDTO.
        #
        # Nenhum município sem dado válido é convertido para zero.
        # Portanto, a média somente é publicada quando existe dado
        # válido para todos os municípios monitorados.
        # ======================================================

        precipitation_24h_values = []

        for municipio_precipitacao in municipios:

            if municipio_precipitacao == municipio:

                precipitation_observation = observation

            else:

                precipitation_observation = (
                    self.weather.update_current_weather(
                        municipio_precipitacao
                    )
                )

            value = self._to_float(
                self._weather_value(
                    precipitation_observation,
                    "precipitation_24h_mm",
                    "precipitacao_24h",
                )
            )

            if value is not None:

                precipitation_24h_values.append(
                    value
                )

        if (
            len(precipitation_24h_values)
            == len(municipios)
        ):

            precipitation_24h_average = (
                sum(precipitation_24h_values)
                / len(precipitation_24h_values)
            )

        else:

            precipitation_24h_average = None

        # ======================================================
        # DADOS DO WEATHERDTO DO MUNICÍPIO DE REFERÊNCIA
        # ======================================================

        temperature = self._to_float(
            self._weather_value(
                observation,
                "temperature",
                "temperatura",
            )
        )

        humidity = self._to_float(
            self._weather_value(
                observation,
                "humidity",
                "umidade",
            )
        )

        # ======================================================
        # CONTRATO METEOROLÓGICO CANÔNICO — FASE 1
        # ======================================================
        #
        # Chuva ocorrendo agora e volumes de precipitação são
        # variáveis semanticamente distintas.
        #
        # rain_now:
        #     condição meteorológica atual.
        #
        # precipitation_1h_mm:
        #     precipitação da última hora disponibilizada pelo
        #     provider.
        #
        # precipitation_24h_mm:
        #     acumulado de 24 horas. Não é inferido a partir
        #     de precipitation_1h_mm.
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

        # O valor de 24h do KPI é a MÉDIA MUNICIPAL.
        precipitation_24h = precipitation_24h_average

        # Campo legado preservado para consumidores ainda não
        # migrados. Para o KPI visual "Chuva (24h)", o contrato
        # consolidado agora representa a média dos municípios.
        precipitation = precipitation_24h

        wind_speed = self._to_float(
            self._weather_value(
                observation,
                "wind_speed",
                "velocidade_vento",
            )
        )

        cloud_cover = self._to_float(
            self._weather_value(
                observation,
                "cloud_cover",
                "cobertura_nuvens",
            )
        )

        # ======================================================
        # ÍNDICE AGROCLIMA
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
                precipitation
                if precipitation is not None
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
            if observation.observation_time is not None
            else now
        )

        # ======================================================
        # HISTÓRICO REAL DE GEADAS
        #
        # Fonte exclusiva:
        #     HistoricalWeatherDaily
        #
        # Critério objetivo:
        #     temperatura_minima <= 0 °C
        #
        # O histórico é calculado para o mesmo município utilizado
        # pelo KPIService como contexto principal. Nenhum dado
        # fictício, previsão ou valor decorativo é introduzido.
        # ======================================================

        historical = (
            self._get_historical_frost_context(
                municipio
            )
        )

        # ======================================================
        # CONTEXTO CONSOLIDADO
        # ======================================================

        return {

            # ==================================================
            # KPIs VISUAIS
            # ==================================================

            "temperatura_media": (
                round(
                    temperature,
                    1
                )
                if temperature is not None
                else None
            ),

            # Campo legado: mantido temporariamente para
            # compatibilidade. Seu significado agora é explícito:
            # precipitação da última hora.
            "precipitacao": (
                round(
                    precipitation,
                    1
                )
                if precipitation is not None
                else None
            ),

            # Contrato meteorológico canônico.
            "chuva_agora": rain_now,

            "precipitacao_1h": (
                round(
                    precipitation_1h,
                    1
                )
                if precipitation_1h is not None
                else None
            ),

            "precipitacao_24h": (
                round(
                    precipitation_24h,
                    1
                )
                if precipitation_24h is not None
                else None
            ),

            # Média municipal utilizada pelo cartão "Chuva (24h)".
            "precipitacao_24h_media": (
                round(
                    precipitation_24h_average,
                    2
                )
                if precipitation_24h_average is not None
                else None
            ),

            "precipitacao_24h_municipios": (
                len(precipitation_24h_values)
            ),

            "precipitacao_24h_total_municipios": (
                len(municipios)
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

            # Compatibilidade com a camada de Inteligência:
            # precipitation representa explicitamente a janela
            # de 1 hora nesta etapa.
            "precipitation": precipitation,

            # Variáveis canônicas disponíveis aos consumidores.
            "rain_now": rain_now,

            "precipitation_1h_mm": precipitation_1h,

            "precipitation_24h_mm": precipitation_24h,

            "analysis_date": analysis_date,

            # ==================================================
            # EVIDÊNCIA HISTÓRICA REAL DE GEADAS
            # ==================================================

            "historical_frost": historical["historical_frost"],

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

            # Critério real e único de geada.
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

        O contrato principal desta camada utiliza os nomes em inglês
        definidos por WeatherDTO. Como proteção de compatibilidade,
        também reconhece os nomes persistidos em português do modelo
        WeatherObservation.

        Esta compatibilidade não cria dados nem altera valores.
        Apenas evita que uma diferença de representação entre camadas
        interrompa a consolidação dos KPIs.
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

# ==========================================================
# AUDITORIA — FASE 3 / MAP PANEL
# ==========================================================
#
# Este arquivo foi auditado para verificar o contrato utilizado
# pelo painel geoespacial para o indicador "Chuva (24h)".
#
# Resultado:
# - KPIService disponibiliza "precipitacao_24h" como campo oficial.
# - "precipitacao_24h_media" registra explicitamente a média
#   municipal de precipitação em 24 horas.
# - O campo "precipitacao" permanece como alias/compatibilidade
#   dentro desta versão do serviço.
# - Portanto, a correção necessária está no template map_panel.html:
#       kpis.precipitacao
#   deve ser substituído por:
#       kpis.precipitacao_24h
#
# Nenhuma alteração funcional foi aplicada ao KPIService nesta etapa.
# ==========================================================
