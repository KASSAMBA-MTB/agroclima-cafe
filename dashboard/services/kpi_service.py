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

Versão..........: 2.3
===============================================================================
"""

from django.utils import timezone

from core.intelligence.agroclima_index import AgroClimaIndex
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
            #
            # Os módulos históricos correspondentes ainda não
            # estão integrados ao KPIService.
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

            # Histórico observado de geadas ainda não está
            # disponível no modelo atual.

            "historical_frost": None,

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "scores": indice["scores"],
        }

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

            "historical_frost": None,

            # ==================================================
            # ÍNDICE AGROCLIMA
            # ==================================================

            "scores": {},
        }