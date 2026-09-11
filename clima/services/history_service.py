"""
==========================================================
AgroClima Café

History Service — Correção do contrato do gráfico
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
    - transportar ETo diária persistida em HistoricalWeatherDaily.

ETo — FASE 6
------------
A ETo diária é transportada a partir do campo persistido
HistoricalWeatherDaily.eto_mm_day. Na consolidação regional, o valor diário
é obtido pela média dos valores disponíveis entre os registros das estações.
Valores ausentes permanecem None e não são convertidos em zero.

IMPORTANTE
----------
Nenhum valor histórico é inventado, replicado ou estimado.

Correção desta versão:
    - padroniza os rótulos da série em DD/MM;
    - mantém todas as séries do contrato do gráfico alinhadas;
    - aproveita umidade e vento reais quando existem em WeatherObservation;
    - mantém índice agroclimático fora deste serviço, sem cálculo artificial.

Uma ocorrência histórica de geada é identificada exclusivamente
quando a temperatura mínima observada registrada em
HistoricalWeatherDaily é menor ou igual a 0 °C.

A camada de inteligência não pertence a este serviço.
==========================================================
"""

from datetime import timedelta

from django.db.models import Avg, Sum, Min, Max
from django.utils import timezone

from clima.models import (
    HistoricalWeatherDaily,
    Provider,
    WeatherObservation,
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
            "vento": [...],
            "indice_agroclima": [...],
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

            # ======================================================
            # EXTENSÃO DO HISTÓRICO COM OBSERVAÇÕES RECENTES
            # ======================================================
            #
            # HistoricalWeatherDaily continua sendo a fonte principal
            # do histórico. Entretanto, quando existem observações reais
            # mais recentes em WeatherObservation, o período "Histórico"
            # deve alcançar também a data mais recente observada.
            #
            # Isso evita que a série histórica termine antes dos dados
            # recentes disponíveis e mantém a mesma integração já usada
            # nos períodos de 7 e 30 dias.
            #
            # Nenhum valor é inventado. Se não existir nenhuma fonte,
            # o retorno permanece vazio.
            # ======================================================

            recent_last_date = (
                WeatherObservation.objects
                .filter(
                    station__provider=provider,
                    station__ativa=True,
                )
                .order_by("-observation_time")
                .values_list(
                    "observation_time",
                    flat=True,
                )
                .first()
            )

            if recent_last_date is not None:
                if timezone.is_aware(recent_last_date):
                    recent_last_date = timezone.localtime(
                        recent_last_date
                    ).date()
                else:
                    recent_last_date = recent_last_date.date()

            if primeiro_registro is None:
                if recent_last_date is None:
                    return self._empty()

                data_inicio = recent_last_date
                data_fim = recent_last_date

            else:
                data_inicio = primeiro_registro
                data_fim = ultimo_registro

                if (
                    recent_last_date is not None
                    and recent_last_date > data_fim
                ):
                    data_fim = recent_last_date

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

                temperatura_maxima_regiao=Max(
                    "temperatura_maxima"
                ),

                eto_media_regiao=Avg(
                    "eto_mm_day"
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

            temperatura_maxima = (
                record.get(
                    "temperatura_maxima_regiao"
                )
            )

            eto_mm_day = (
                record.get(
                    "eto_media_regiao"
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

                "temperatura_maxima": (
                    float(
                        temperatura_maxima
                    )
                    if temperatura_maxima is not None
                    else None
                ),

                "eto_mm_day": (
                    float(eto_mm_day)
                    if eto_mm_day is not None
                    else None
                ),

                "geada": frost,
            }

        # ======================================================
        # INTEGRAÇÃO DE OBSERVAÇÕES RECENTES
        # ======================================================
        #
        # HistoricalWeatherDaily é a fonte histórica principal.
        # Quando uma data do período ainda não possui registro
        # diário consolidado, dados meteorológicos reais persistidos
        # em WeatherObservation podem preencher somente essa lacuna.
        #
        # Registro histórico existente tem prioridade.
        # Ausência real continua None. Nenhum None vira zero.
        # O dia atual será posteriormente alinhado ao KPI pelo
        # ChartService.
        # ======================================================

        if data_inicio <= data_fim:
            recent_filters = self._station_filter(
                municipio=municipio,
                provider=provider,
            )

            recent_observations = (
                WeatherObservation.objects
                .filter(
                    observation_time__date__gte=data_inicio,
                    observation_time__date__lte=data_fim,
                    **recent_filters,
                )
                .values(
                    "observation_time",
                    "temperatura",
                    "precipitacao",
                    "umidade",
                    "velocidade_vento",
                )
                .order_by(
                    "observation_time",
                )
            )

            observation_by_date = {}

            for observation in recent_observations:
                observation_time = observation.get(
                    "observation_time",
                )

                if observation_time is None:
                    continue

                if timezone.is_aware(observation_time):
                    observation_date = timezone.localtime(
                        observation_time
                    ).date()
                else:
                    observation_date = observation_time.date()

                entry = observation_by_date.setdefault(
                    observation_date,
                    {
                        "temperaturas": [],
                        "precipitacoes": [],
                        "umidades": [],
                        "ventos": [],
                    },
                )

                temperatura_observada = observation.get(
                    "temperatura",
                )
                precipitacao_observada = observation.get(
                    "precipitacao",
                )

                if temperatura_observada is not None:
                    entry["temperaturas"].append(
                        float(temperatura_observada)
                    )

                if precipitacao_observada is not None:
                    entry["precipitacoes"].append(
                        float(precipitacao_observada)
                    )

                umidade_observada = observation.get(
                    "umidade",
                )

                if umidade_observada is not None:
                    entry["umidades"].append(
                        float(umidade_observada)
                    )

                vento_observado = observation.get(
                    "velocidade_vento",
                )

                if vento_observado is not None:
                    entry["ventos"].append(
                        float(vento_observado)
                    )

            for observation_date, values in observation_by_date.items():
                existing = daily_data.get(
                    observation_date,
                    {},
                )

                temperatura_historica = existing.get(
                    "temperatura",
                )
                precipitacao_historica = existing.get(
                    "precipitacao",
                )

                temperatura_fallback = None
                if values["temperaturas"]:
                    temperatura_fallback = round(
                        sum(values["temperaturas"])
                        / len(values["temperaturas"]),
                        1,
                    )

                precipitacao_fallback = None
                if values["precipitacoes"]:
                    precipitacao_fallback = round(
                        sum(values["precipitacoes"]),
                        1,
                    )

                umidade_fallback = None
                if values["umidades"]:
                    umidade_fallback = round(
                        sum(values["umidades"])
                        / len(values["umidades"]),
                        1,
                    )

                vento_fallback = None
                if values["ventos"]:
                    vento_fallback = round(
                        sum(values["ventos"])
                        / len(values["ventos"]),
                        1,
                    )

                daily_data[observation_date] = {
                    "temperatura": (
                        temperatura_historica
                        if temperatura_historica is not None
                        else temperatura_fallback
                    ),
                    "precipitacao": (
                        precipitacao_historica
                        if precipitacao_historica is not None
                        else precipitacao_fallback
                    ),
                    "umidade": umidade_fallback,
                    "vento": vento_fallback,
                    "temperatura_minima": existing.get(
                        "temperatura_minima",
                    ),
                    "temperatura_maxima": existing.get(
                        "temperatura_maxima",
                    ),
                    "eto_mm_day": existing.get(
                        "eto_mm_day",
                    ),
                    "geada": existing.get(
                        "geada",
                        False,
                    ),
                }

        # ======================================================
        # CONSTRUÇÃO DA SÉRIE
        # ======================================================

        dias = []

        temperatura = []

        precipitacao = []

        umidade = []

        vento = []

        temperatura_minima = []

        temperatura_maxima = []

        eto_mm_day = []

        indice_agroclima = []

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
                    vento,
                    temperatura_minima,
                    temperatura_maxima,
                    eto_mm_day,
                    indice_agroclima,
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
                    vento,
                    temperatura_minima,
                    temperatura_maxima,
                    eto_mm_day,
                    indice_agroclima,
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

            "vento": vento,

            "temperatura_minima": temperatura_minima,

            "temperatura_maxima": temperatura_maxima,

            "eto_mm_day": eto_mm_day,

            "indice_agroclima": indice_agroclima,

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
        vento,
        temperatura_minima,
        temperatura_maxima,
        eto_mm_day,
        indice_agroclima,
    ):
        """
        Adiciona um dia à série mantendo lacunas como None.

        Retorna:
            True  -> ocorrência de geada;
            False -> sem ocorrência de geada.
        """

        # O ChartService integra o dia atual usando o mesmo formato
        # visual da série: DD/MM. Manter ISO aqui quebra essa integração.
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

            vento.append(
                None
            )

            temperatura_minima.append(
                None
            )

            temperatura_maxima.append(
                None
            )

            eto_mm_day.append(
                None
            )

            indice_agroclima.append(
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
            record.get(
                "umidade",
            )
        )

        vento.append(
            record.get(
                "vento",
            )
        )

        temperatura_minima.append(
            record.get(
                "temperatura_minima",
            )
        )

        temperatura_maxima.append(
            record.get(
                "temperatura_maxima",
            )
        )

        eto_mm_day.append(
            record.get(
                "eto_mm_day",
            )
        )

        # O índice agroclimático pertence à camada de inteligência.
        # O HistoryService não calcula nem inventa esse indicador.
        indice_agroclima.append(
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

            "vento": [],

            "temperatura_minima": [],

            "temperatura_maxima": [],

            "eto_mm_day": [],

            "indice_agroclima": [],

            "geadas": 0,
        }

# ============================================================================
# REGISTRO DE AUDITORIA - FASE 6.1 ETo
# ============================================================================
#
# Objetivo:
#     Transportar a ETo diária persistida para a série histórica consumida
#     pelos serviços especializados de indicadores.
#
# Fonte:
#     HistoricalWeatherDaily.eto_mm_day.
#
# Consolidação regional:
#     média dos valores de ETo disponíveis para a mesma data.
#
# Tratamento de ausência:
#     None permanece None; ausência não é convertida em zero.
#
# Observações recentes:
#     WeatherObservation não é utilizado como fallback para ETo, pois o
#     campo pertence atualmente ao histórico diário persistido. Quando uma
#     observação recente completa uma lacuna de outras variáveis, a ETo
#     histórica existente é preservada.
#
# Segurança arquitetural:
#     - sem cálculo de ETo;
#     - sem fórmula meteorológica neste serviço;
#     - sem ORM adicional além da leitura histórica já existente;
#     - sem frontend;
#     - sem FRI;
#     - sem recomendações agronômicas.
# ============================================================================
