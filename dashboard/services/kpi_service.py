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

Versão..........: 2.4
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

        Os atributos utilizados abaixo correspondem ao contrato
        atual do WeatherDTO:

            temperature
            humidity
            precipitation
            wind_speed
            cloud_cover
            observation_time
        """

        municipio = Municipio.objects.first()

        if municipio is None:

            return self._empty()

        # ======================================================
        # OBSERVAÇÃO METEOROLÓGICA ATUAL
        # ======================================================

        observation = (
            self.weather.update_current_weather(
                municipio
            )
        )

        # ======================================================
        # DADOS DO WEATHERDTO
        #
        # IMPORTANTE:
        # O objeto retornado pelo WeatherService é WeatherDTO.
        #
        # Portanto, os atributos devem utilizar os nomes definidos
        # pelo DTO, e não os nomes dos campos do modelo
        # WeatherObservation.
        # ======================================================

        temperature = self._to_float(
            observation.temperature
        )

        humidity = self._to_float(
            observation.humidity
        )

        precipitation = self._to_float(
            observation.precipitation
        )

        wind_speed = self._to_float(
            observation.wind_speed
        )

        cloud_cover = self._to_float(
            observation.cloud_cover
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

            "precipitacao": (
                round(
                    precipitation,
                    1
                )
                if precipitation is not None
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

            "precipitation": precipitation,

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