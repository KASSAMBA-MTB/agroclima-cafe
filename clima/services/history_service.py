"""
==========================================================
AgroClima Café

History Service
==========================================================

Responsável pelo fornecimento de dados históricos
persistidos para os componentes analíticos do Dashboard.

Fonte principal:
    HistoricalWeatherDaily

Responsabilidades:
    - fornecer clima atual através do WeatherService;
    - fornecer estação meteorológica;
    - fornecer séries históricas diárias;
    - suportar períodos de 7 dias;
    - suportar períodos de 30 dias;
    - suportar histórico completo disponível;
    - identificar ocorrências históricas de geada;
    - preservar lacunas quando não existirem dados.

IMPORTANTE
----------
Nenhum valor histórico é inventado, replicado ou estimado.

Uma ocorrência histórica de geada é identificada exclusivamente
quando a temperatura mínima observada registrada em
HistoricalWeatherDaily é menor ou igual a 0 °C.

A camada de inteligência não pertence a este serviço.
==========================================================
"""

from datetime import timedelta

from django.db.models import Avg, Sum, Min
from django.utils import timezone

from clima.models import (
    HistoricalWeatherDaily,
    Provider,
    WeatherStation,
)

from .weather_service import WeatherService


class HistoryService:
    """
    Serviço responsável pelo acesso aos dados históricos
    meteorológicos persistidos.
    """

    FROST_THRESHOLD = 0.0

    def __init__(self):

        self.weather = WeatherService()

    # ==========================================================
    # ÚLTIMA OBSERVAÇÃO
    # ==========================================================

    def latest(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        """
        Retorna a condição meteorológica mais recente.
        """

        return self.weather.latest(
            municipio,
            provider,
        )

    # ==========================================================
    # CLIMA ATUAL
    # ==========================================================

    def current(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        """
        Atualiza e retorna o clima atual.
        """

        return self.weather.update_current_weather(
            municipio,
            provider,
        )

    # ==========================================================
    # ESTAÇÃO METEOROLÓGICA
    # ==========================================================

    def station(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):
        """
        Obtém ou cria a estação meteorológica associada
        ao município.
        """

        municipio_field = (
            WeatherStation._meta.get_field(
                "municipio"
            )
        )

        field_is_relation = (
            getattr(
                municipio_field,
                "is_relation",
                False,
            )
            and getattr(
                municipio_field,
                "many_to_one",
                False,
            )
        )

        if field_is_relation:

            station, _ = (
                WeatherStation.objects
                .get_or_create(
                    municipio=municipio,
                    provider=provider,
                    defaults={
                        "ativa": True,
                    },
                )
            )

        else:

            municipio_nome = getattr(
                municipio,
                "nome",
                municipio,
            )

            station, _ = (
                WeatherStation.objects
                .get_or_create(
                    municipio=municipio_nome,
                    provider=provider,
                    defaults={
                        "ativa": True,
                    },
                )
            )

        return station

    # ==========================================================
    # FILTRO DAS ESTAÇÕES
    # ==========================================================

    def _station_filter(
        self,
        municipio=None,
        provider=Provider.OPEN_METEO,
    ):
        """
        Monta o filtro utilizado para localizar os dados
        históricos.
        """

        filters = {
            "station__provider": provider,
            "station__ativa": True,
        }

        if municipio is None:

            return filters

        municipio_field = (
            WeatherStation._meta.get_field(
                "municipio"
            )
        )

        field_is_relation = (
            getattr(
                municipio_field,
                "is_relation",
                False,
            )
            and getattr(
                municipio_field,
                "many_to_one",
                False,
            )
        )

        if field_is_relation:

            filters[
                "station__municipio"
            ] = municipio

        else:

            municipio_nome = getattr(
                municipio,
                "nome",
                municipio,
            )

            filters[
                "station__municipio"
            ] = municipio_nome

        return filters

    # ==========================================================
    # DADOS HISTÓRICOS DO GRÁFICO
    # ==========================================================

    def chart_data(
        self,
        municipio=None,
        days=7,
        provider=Provider.OPEN_METEO,
    ):
        """
        Retorna dados históricos diários persistidos.

        Parâmetros
        ----------
        municipio:
            Município monitorado.

            Quando informado:
                retorna somente seus dados.

            Quando None:
                consolida a região monitorada.

        days:
            Quantidade de dias.

            1:
                dia atual.

            7:
                últimos 7 dias.

            30:
                últimos 30 dias.

            None:
                todo o histórico disponível.

        provider:
            Provedor meteorológico.

        Retorno
        -------
        dict

        {
            "dias": [...],
            "temperatura": [...],
            "precipitacao": [...],
            "umidade": [...],
            "geadas": 0
        }

        GEADAS
        ------
        Uma ocorrência histórica é contabilizada quando a menor
        temperatura observada no dia é <= 0 °C.

        Na consolidação regional, cada data é contabilizada
        apenas uma vez.
        """

        # ======================================================
        # NORMALIZAÇÃO DO PERÍODO
        # ======================================================

        if days is not None:

            try:

                days = int(days)

            except (
                TypeError,
                ValueError,
            ):

                days = 7

            days = max(
                1,
                min(
                    days,
                    3650,
                ),
            )

        # ======================================================
        # FILTROS
        # ======================================================

        filters = self._station_filter(
            municipio=municipio,
            provider=provider,
        )

        queryset = (
            HistoricalWeatherDaily.objects
            .filter(
                **filters
            )
        )

        # ======================================================
        # DEFINIÇÃO DO INTERVALO
        # ======================================================

        hoje = timezone.localdate()

        if days is None:

            primeiro_registro = (
                queryset
                .order_by("data")
                .values_list(
                    "data",
                    flat=True,
                )
                .first()
            )

            ultimo_registro = (
                queryset
                .order_by("-data")
                .values_list(
                    "data",
                    flat=True,
                )
                .first()
            )

            if (
                primeiro_registro is None
                or ultimo_registro is None
            ):

                return self._empty()

            data_inicio = primeiro_registro

            data_fim = ultimo_registro

        else:

            data_inicio = (
                hoje
                - timedelta(
                    days=days - 1
                )
            )

            data_fim = hoje

        # ======================================================
        # CONSULTA DOS DADOS HISTÓRICOS
        # ======================================================

        historical = (
            queryset
            .filter(
                data__gte=data_inicio,
                data__lte=data_fim,
            )
            .values("data")
            .annotate(

                temperatura_media_regiao=Avg(
                    "temperatura_media"
                ),

                precipitacao_total_regiao=Sum(
                    "precipitacao"
                ),

                temperatura_minima_regiao=Min(
                    "temperatura_minima"
                ),
            )
            .order_by("data")
        )

        # ======================================================
        # ÍNDICE POR DATA
        # ======================================================

        daily_data = {}

        for record in historical:

            data = record.get(
                "data"
            )

            if data is None:

                continue

            temperatura = (
                record.get(
                    "temperatura_media_regiao"
                )
            )

            precipitacao = (
                record.get(
                    "precipitacao_total_regiao"
                )
            )

            temperatura_minima = (
                record.get(
                    "temperatura_minima_regiao"
                )
            )

            frost = False

            if temperatura_minima is not None:

                frost = (
                    float(
                        temperatura_minima
                    )
                    <= self.FROST_THRESHOLD
                )

            daily_data[data] = {

                "temperatura": (
                    float(temperatura)
                    if temperatura is not None
                    else None
                ),

                "precipitacao": (
                    float(precipitacao)
                    if precipitacao is not None
                    else None
                ),

                "temperatura_minima": (
                    float(
                        temperatura_minima
                    )
                    if temperatura_minima is not None
                    else None
                ),

                "geada": frost,
            }

        # ======================================================
        # CONSTRUÇÃO DA SÉRIE
        # ======================================================

        dias = []

        temperatura = []

        precipitacao = []

        umidade = []

        geadas = 0

        if days is None:

            data_atual = data_inicio

            while data_atual <= data_fim:

                frost = self._append_day(
                    data_atual,
                    daily_data,
                    dias,
                    temperatura,
                    precipitacao,
                    umidade,
                )

                if frost:

                    geadas += 1

                data_atual += timedelta(
                    days=1
                )

        else:

            for offset in range(days):

                data = (
                    data_inicio
                    + timedelta(
                        days=offset
                    )
                )

                frost = self._append_day(
                    data,
                    daily_data,
                    dias,
                    temperatura,
                    precipitacao,
                    umidade,
                )

                if frost:

                    geadas += 1

        # ======================================================
        # RETORNO
        # ======================================================

        return {

            "dias": dias,

            "temperatura": temperatura,

            "precipitacao": precipitacao,

            "umidade": umidade,

            "geadas": geadas,
        }

    # ==========================================================
    # ADICIONAR DIA À SÉRIE
    # ==========================================================

    @staticmethod
    def _append_day(
        data,
        daily_data,
        dias,
        temperatura,
        precipitacao,
        umidade,
    ):
        """
        Adiciona um dia à série mantendo lacunas como None.

        Retorna:
            True  -> ocorrência de geada;
            False -> sem ocorrência de geada.
        """

        dias.append(
            data.strftime(
                "%d/%m"
            )
        )

        record = daily_data.get(
            data
        )

        if record is None:

            temperatura.append(
                None
            )

            precipitacao.append(
                None
            )

            umidade.append(
                None
            )

            return False

        temperatura.append(
            record.get(
                "temperatura"
            )
        )

        precipitacao.append(
            record.get(
                "precipitacao"
            )
        )

        # HistoricalWeatherDaily ainda não fornece
        # umidade diária consolidada.

        umidade.append(
            None
        )

        return bool(
            record.get(
                "geada",
                False,
            )
        )

    # ==========================================================
    # RETORNO VAZIO
    # ==========================================================

    @staticmethod
    def _empty():

        return {

            "dias": [],

            "temperatura": [],

            "precipitacao": [],

            "umidade": [],

            "geadas": 0,
        }