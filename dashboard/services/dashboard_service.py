"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃƒO PAULO - UNIVESP

Curso...........: Bacharelado em CiÃªncia de Dados
Disciplina......: Trabalho de ConclusÃ£o de Curso (TCC)
Projeto.........: AgroClima CafÃ©
MÃ³dulo..........: Dashboard
Arquivo.........: dashboard_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: SÃ£o JoÃ£o da Boa Vista - SP
Ano.............: 2026

DescriÃ§Ã£o.......:
ServiÃ§o responsÃ¡vel por consolidar todos os dados estruturados
da Dashboard Principal.

Responsabilidades:
    â€¢ Consolidar KPIs, grÃ¡ficos, ranking, eventos e mapa.
    â€¢ Enriquecer os pontos geogrÃ¡ficos com dados meteorolÃ³gicos.
    â€¢ Disponibilizar ocorrÃªncias histÃ³ricas reais de geada.
    â€¢ Disponibilizar indicadores histÃ³ricos estruturados para a
      camada de InteligÃªncia.
    â€¢ NÃ£o executar regras de InteligÃªncia.

VersÃ£o..........: 3.8
===============================================================================
"""

from datetime import timedelta

from clima.models import (
    HistoricalWeatherDaily,
    Provider,
    WeatherObservation,
)
from clima.services.weather_service import WeatherService
from clima.services.history_service import HistoryService
from municipios.models import Municipio

from dashboard.services.kpi_service import KPIService
from dashboard.services.chart_service import ChartService
from dashboard.services.ranking_service import RankingService
from dashboard.services.events_service import EventsService
from dashboard.services.map_service import MapService
from dashboard.services.frost_risk_service import FrostRiskService
from dashboard.services.thermal_classification_service import (
    ThermalClassificationService,
)
from dashboard.services.agroclimate_indicator_service import (
    AgroClimateIndicatorService,
)
from dashboard.services.historical_climate_indicator_service import (
    HistoricalClimateIndicatorService,
)


class DashboardService:
    """
    Consolida todos os dados estruturados utilizados pela
    Dashboard.

    NÃ£o executa regras de negÃ³cio inteligentes.

    A camada de InteligÃªncia permanece responsabilidade da
    DashboardFacade.
    """

    def __init__(self):

        self.kpi_service = KPIService()

        self.chart_service = ChartService()

        self.ranking_service = RankingService()

        self.events_service = EventsService()

        self.map_service = MapService()

        # Serviço meteorológico responsável por atualizar a observação
        # atual antes da montagem dos KPIs e dos pontos do mapa.
        self.weather_service = WeatherService()

        # AvaliaÃ§Ã£o oficial e Ãºnica do FRI por municÃpio.
        # O resultado Ã© incorporado ao map_point e passa a ser a
        # fonte autoritativa consumida por mapa, popup, ranking,
        # alerta e insight.
        self.frost_risk_service = FrostRiskService()

        # Serviço responsável pela classificação operacional da temperatura.
        # A classificação é derivada exclusivamente da temperatura observada
        # e materializada no map_point para consumo uniforme pelos componentes.
        # O serviço não acessa banco de dados, API, FRI ou regras de geada.
        self.thermal_classification_service = ThermalClassificationService()

        self.agroclimate_indicator_service = AgroClimateIndicatorService()

        # Histórico canônico utilizado como fonte dos indicadores derivados.
        # O HistoryService fornece a série; o serviço especializado calcula
        # somente os indicadores autorizados da Fase 5.
        self.history_service = HistoryService()
        self.historical_climate_indicator_service = (
            HistoricalClimateIndicatorService()
        )

        # Mantém os DTOs da atualização meteorológica corrente disponíveis
        # para o enriquecimento do map_point. Isso evita perder campos que
        # já existem no WeatherDTO, mas ainda não possuem persistência própria
        # em WeatherObservation, como UV e dados de nascer/pôr do sol.
        self._current_weather_dtos = {}

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def get_dashboard(self):
        """
        Consolida os dados estruturados da Dashboard.
        """

        context = {}

        # ======================================================
        # ATUALIZAÇÃO METEOROLÓGICA
        # ======================================================
        # WeatherObservation é atualizada antes dos KPIs e do mapa.
        # Uma falha isolada não interrompe os demais municípios.
        # ======================================================

        weather_refresh = self._refresh_current_weather()
        context["weather_refresh"] = weather_refresh

        # ======================================================
        # CONTEXTO CANÔNICO ÚNICO — KPIs
        # ======================================================
        #
        # O KPIService não realiza nova aquisição meteorológica.
        # Ele recebe exclusivamente o contexto já produzido pelo
        # ciclo corrente de atualização do DashboardService.
        #
        # Assim, KPI, mapa e demais consumidores partem da mesma
        # cadeia de dados, sem segunda consulta ou interpretação.
        # ======================================================

        canonical_context = self._build_canonical_weather_context()

        # ======================================================
        # KPIs
        # ======================================================

        kpis = self.kpi_service.get_kpis(
            canonical_context=canonical_context
        )

        # Compatibilidade com templates legados
        context.update(kpis)

        # Dashboard V3
        context["kpis"] = kpis

        # ======================================================
        # GRÃFICOS
        # ======================================================

        context["chart"] = (
            self.chart_service.get_chart()
        )

        # ======================================================
        # PERÃODOS DO GRÃFICO
        #
        # Disponibiliza separadamente:
        #
        #   Hoje
        #   7 dias
        #   30 dias
        #   HistÃ³rico
        #
        # O frontend apenas alterna entre os dados
        # jÃ¡ consolidados pelo ChartService.
        # ======================================================

        context["chart_periods"] = (
            self.chart_service.get_chart_periods(
                current_kpis=kpis
            )
        )

        # ======================================================
        # EVENTOS
        # ======================================================

        context["eventos"] = (
    self.events_service.get_events()
        )

        # ======================================================
        # MAPA
        # ======================================================

        map_points = (
            self.map_service.get_points()
        )

        # ======================================================
        # DADOS CLIMÃTICOS DOS MUNICÃPIOS
        #
        # Somente dados estruturados.
        #
        # Nenhuma regra de inteligÃªncia Ã© executada aqui.
        # ======================================================

        map_points = self._attach_climate_data(
            map_points
        )

        # ======================================================
        # AVALIAÃ‡ÃƒO MUNICIPAL ÃšNICA DO FRI
        #
        # Cada municÃpio Ã© avaliado exatamente uma vez depois
        # que os dados climÃ¡ticos e histÃ³ricos jÃ¡ foram anexados.
        # O resultado completo passa a integrar o map_point.
        # Nenhum consumidor posterior deve recalcular o FRI.
        # ======================================================

        map_points = self._attach_frost_intelligence(
            map_points
        )

        # ======================================================
        # ALERTAS CANÔNICOS DA DASHBOARD — ESCOPO TERRITORIAL
        #
        # O DashboardService é a autoridade de consolidação do ciclo.
        # Cada map_point mantém sua inteligência municipal em
        # ``municipal_alerts``. Paralelamente, os alertas efetivamente
        # produzidos pelos municípios são reunidos em uma coleção
        # canônica para o painel global.
        #
        # Esta consolidação NÃO recalcula regras, NÃO altera severidade
        # e NÃO transforma score meteorológico em FRI.
        #
        # O município principal continua sendo o ponto de transporte
        # utilizado pela DashboardFacade. Para que a Facade apenas
        # distribua o resultado já materializado, o campo ``alerts`` do
        # ponto principal recebe a coleção canônica territorial.
        #
        # Os demais pontos preservam exclusivamente seus alertas
        # municipais em ``municipal_alerts`` e ``alerts``.
        # ======================================================

        primary_municipio_id = kpis.get("municipio_id")
        primary_point = next(
            (
                point
                for point in map_points
                if point.get("id") == primary_municipio_id
            ),
            None,
        )

        if primary_point is None:
            primary_point = next(
                (
                    point
                    for point in map_points
                    if point.get("nome") == kpis.get("municipio_nome")
                ),
                None,
            )

        territorial_alerts = []
        seen_alerts = set()

        for point in map_points:
            municipal_alerts = point.get("alerts", [])
            if not isinstance(municipal_alerts, list):
                municipal_alerts = []

            # Preserva a coleção original produzida pela Intelligence
            # para rastreabilidade municipal.
            point["municipal_alerts"] = list(municipal_alerts)

            # Consolidação somente de resultados já produzidos.
            # Nenhuma regra é executada nesta etapa.
            for alert in municipal_alerts:
                if not isinstance(alert, dict):
                    continue

                identity = (
                    alert.get("municipio_id", point.get("municipio_id")),
                    alert.get("id"),
                    alert.get("engine"),
                    alert.get("title"),
                    alert.get("message"),
                    alert.get("severity"),
                    alert.get("metric"),
                    alert.get("metric_value"),
                    alert.get("score"),
                )

                if identity in seen_alerts:
                    continue

                seen_alerts.add(identity)
                territorial_alerts.append(dict(alert))

            # Cada ponto continua disponibilizando seus próprios alertas
            # para consumidores territoriais, sem substituir a origem.
            point["alerts"] = list(municipal_alerts)
            point["alert"] = (
                municipal_alerts[0]
                if municipal_alerts
                else None
            )

        # A coleção territorial é o contrato global já consolidado.
        # A Facade deve apenas distribuí-la, sem reconstruí-la.
        context["alerts"] = territorial_alerts

        # O ponto principal funciona como portador do contrato global
        # para compatibilidade com consumidores que recebem a inteligência
        # a partir do município principal.
        if primary_point is not None:
            primary_point["alerts"] = list(territorial_alerts)

        context["map_points"] = map_points

        # ======================================================
        # RANKING
        #
        # O Ranking recebe exatamente os mesmos map_points que
        # foram disponibilizados ao mapa. O FRI jÃ¡ estÃ¡ calculado
        # nesses objetos e nÃ£o pode ser recalculado pelo Ranking.
        # ======================================================

        context["ranking"] = (
            self.ranking_service.get_ranking(
                map_points
            )
        )

        # ======================================================
        # CAMPOS PREENCHIDOS PELA DASHBOARDFACADE
        # ======================================================

        context["insights"] = []

        context["recommendations"] = []

        # ``alerts`` já foi publicado acima como coleção canônica
        # de cardinalidade máxima 1. A Facade deve apenas consumir
        # esse resultado, sem reconstruí-lo a partir de municípios.

        return context

    # ==========================================================
    # DADOS CLIMÃTICOS DO MAPA
    # ==========================================================


    # ==========================================================
    # ATUALIZAÇÃO METEOROLÓGICA PARA A DASHBOARD
    # ==========================================================

    def _refresh_current_weather(self):
        """
        Atualiza o clima atual de todos os municípios antes da
        consolidação dos KPIs e dos pontos consumidos pelo mapa.

        Não calcula FRI nem executa regras de Inteligência.
        Cada município é processado independentemente.
        """

        atualizados = 0
        erros = 0
        resultados = []

        # Cada execução representa um novo ciclo de atualização.
        # Remove DTOs de municípios que eventualmente falhem neste ciclo.
        self._current_weather_dtos = {}

        municipios = (
            Municipio.objects
            .all()
            .order_by("nome")
        )

        for municipio in municipios:

            try:

                dto = self.weather_service.update_current_weather(
                    municipio,
                    Provider.OPEN_METEO,
                )

                # O DTO é a fonte corrente dos campos meteorológicos
                # complementares. O map_point recebe esses valores sem
                # recalcular, inferir ou substituir dados ausentes.
                self._current_weather_dtos[municipio.nome] = dto

                atualizados += 1

                resultados.append(
                    {
                        "municipio": municipio.nome,
                        "status": "ATUALIZADO",
                    }
                )

            except Exception as exc:

                erros += 1

                resultados.append(
                    {
                        "municipio": municipio.nome,
                        "status": "ERRO",
                        "erro": str(exc),
                    }
                )

        return {
            "total": len(resultados),
            "atualizados": atualizados,
            "erros": erros,
            "municipios": resultados,
        }


    def _attach_climate_data(
        self,
        map_points,
    ):
        """
        Adiciona aos pontos geogrÃ¡ficos os dados estruturados
        disponÃveis para cada municÃpio.

        Dados meteorolÃ³gicos:
            â€¢ temperatura;
            â€¢ umidade;
            â€¢ vento;
            â€¢ cobertura de nuvens;
            â€¢ chuva ocorrendo agora;
            â€¢ precipitaÃ§Ã£o da Ãºltima hora;
            â€¢ precipitaÃ§Ã£o acumulada em 24 horas;
            â€¢ horÃ¡rio da observaÃ§Ã£o.

        Contrato canÃ´nico:
            â€¢ chuva_agora;
            â€¢ precipitacao_1h;
            â€¢ precipitacao_24h.

        O campo legado ``precipitation`` Ã© preservado no map_point
        para compatibilidade, mas seu valor corresponde Ã 
        precipitaÃ§Ã£o da Ãºltima hora nesta etapa da migraÃ§Ã£o.

        Dados histÃ³ricos de geada:
            â€¢ ocorrÃªncia;
            â€¢ quantidade de ocorrÃªncias;
            â€¢ quantidade total de registros histÃ³ricos;
            â€¢ frequÃªncia histÃ³rica de geada;
            â€¢ quantidade de episÃ³dios de geada;
            â€¢ Ãºltima data de ocorrÃªncia;
            â€¢ temperatura mÃnima da Ãºltima ocorrÃªncia;
            â€¢ menor temperatura registrada em ocorrÃªncia de geada.

        CritÃ©rio objetivo para ocorrÃªncia histÃ³rica de geada:

            temperatura_minima <= 0 Â°C

        Este mÃ©todo NÃƒO:
            â€¢ calcula FRI;
            â€¢ classifica risco;
            â€¢ calcula confianÃ§a;
            â€¢ gera alertas;
            â€¢ gera recomendaÃ§Ãµes;
            â€¢ executa regras de InteligÃªncia.

        Os indicadores histÃ³ricos adicionados aqui constituem
        Os indicadores históricos adicionados aqui constituem
        evidência estruturada para a etapa posterior da FrostRule.
        O cálculo é delegado ao HistoricalClimateIndicatorService.
        """

        if not map_points:

            return []

        municipality_names = [
            point.get("nome")
            for point in map_points
            if point.get("nome")
        ]

        if not municipality_names:

            return map_points

        # ======================================================
        # ÃšLTIMA OBSERVAÃ‡ÃƒO METEOROLÃ“GICA
        # ======================================================

        observations = (
            WeatherObservation.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                station__municipio__nome__in=(
                    municipality_names
                )
            )
            .order_by(
                "station__municipio__nome",
                "-observation_time",
            )
        )

        latest_by_municipality = {}

        for observation in observations:

            municipality = (
                observation.station
                .municipio
                .nome
            )

            if municipality in (
                latest_by_municipality
            ):

                continue

            latest_by_municipality[
                municipality
            ] = observation

        # ======================================================
        # HISTÃ“RICO REAL DE GEADAS
        #
        # Fonte:
        # HistoricalWeatherDaily
        #
        # Somente registros persistidos sÃ£o considerados.
        # NÃ£o utiliza previsÃ£o.
        # ======================================================

        historical_records = (
            HistoricalWeatherDaily.objects
            .select_related(
                "station",
                "station__municipio",
            )
            .filter(
                station__municipio__nome__in=(
                    municipality_names
                ),
                temperatura_minima__isnull=False,
            )
            .order_by(
                "station__municipio__nome",
                "data",
            )
        )

        historical_by_municipality = {}

        for record in historical_records:

            municipality = (
                record.station
                .municipio
                .nome
            )

            summary = historical_by_municipality.setdefault(
                municipality,
                {
                    "total_records": 0,
                    "frost_records": 0,
                    "frost_dates": [],
                    "last_date": None,
                    "last_minimum": None,
                    "minimum_temperature": None,
                },
            )

            summary["total_records"] += 1

            minimum = self._to_float(
                record.temperatura_minima
            )

            if minimum is None:
                continue

            if (
                summary["minimum_temperature"] is None
                or minimum < summary["minimum_temperature"]
            ):
                summary["minimum_temperature"] = minimum

            # CritÃ©rio real de geada.
            if minimum <= 0:

                summary["frost_records"] += 1

                if record.data:
                    summary["frost_dates"].append(
                        record.data
                    )

                # O queryset estÃ¡ em ordem crescente; portanto,
                # o Ãºltimo registro de geada Ã© o mais recente.
                summary["last_date"] = (
                    record.data.isoformat()
                    if record.data
                    else None
                )

                summary["last_minimum"] = minimum

        # ======================================================
        # ENRIQUECIMENTO DOS PONTOS
        # ======================================================

        # ======================================================
        # INDICADORES HISTÓRICOS — FASE 5
        # ======================================================
        # A série diária é obtida pelo HistoryService. O cálculo da
        # amplitude térmica permanece exclusivamente no serviço
        # especializado HistoricalClimateIndicatorService.
        #
        # O resultado é estruturado por município e será anexado ao
        # map_point sem alterar a avaliação oficial do FRI.
        # ======================================================

        historical_indicators_by_municipality = {}

        municipios = (
            Municipio.objects
            .filter(
                nome__in=municipality_names
            )
        )

        municipality_objects = {
            municipio.nome: municipio
            for municipio in municipios
        }

        for municipality in municipality_names:
            municipio = municipality_objects.get(
                municipality
            )

            if municipio is None:
                historical_indicator_service = getattr(
                    self,
                    "historical_climate_indicator_service",
                    None,
                )

                if historical_indicator_service is None:
                    historical_indicator_service = (
                        HistoricalClimateIndicatorService()
                    )
                    self.historical_climate_indicator_service = (
                        historical_indicator_service
                    )

                historical_indicators_by_municipality[
                    municipality
                ] = historical_indicator_service.calculate(
                    {}
                )
                continue

            try:
                historical_data = self.history_service.chart_data(
                    municipio=municipio,
                    days=None,
                )
            except Exception:
                historical_data = {}

            # Compatibilidade defensiva com testes e instanciações controladas
            # que utilizam __new__ e, portanto, não executam __init__.
            # Em produção, o atributo é sempre criado no __init__.
            historical_indicator_service = getattr(
                self,
                "historical_climate_indicator_service",
                None,
            )

            if historical_indicator_service is None:
                historical_indicator_service = (
                    HistoricalClimateIndicatorService()
                )
                self.historical_climate_indicator_service = (
                    historical_indicator_service
                )

            historical_indicators_by_municipality[
                municipality
            ] = historical_indicator_service.calculate(
                historical_data
            )


        enriched_points = []

        for point in map_points:

            enriched = dict(point)

            municipality = point.get(
                "nome"
            )

            observation = (
                latest_by_municipality.get(
                    municipality
                )
            )

            # ==================================================
            # PADRÃƒO SEM DADO
            # ==================================================

            enriched["temperature"] = None

            # Classificação térmica canônica.
            # O valor permanece ``unavailable`` até que uma temperatura
            # válida seja efetivamente disponibilizada pela observação.
            enriched["temperature_class"] = (
                ThermalClassificationService.CLASS_UNAVAILABLE
            )
            enriched["temperature_class_label"] = (
                ThermalClassificationService.LABELS[
                    ThermalClassificationService.CLASS_UNAVAILABLE
                ]
            )

            enriched["humidity"] = None

            enriched["wind_speed"] = None

            enriched["cloud_cover"] = None

            # ==================================================
            # CONTRATO METEOROLÃ“GICO CANÃ”NICO â€” FASE 1
            # ==================================================

            # Chuva ocorrendo agora.
            enriched["rain_now"] = None
            enriched["chuva_agora"] = None

            # PrecipitaÃ§Ã£o da Ãºltima hora.
            enriched["precipitation_1h_mm"] = None
            enriched["precipitacao_1h"] = None

            # PrecipitaÃ§Ã£o acumulada em 24 horas.
            enriched["precipitation_24h_mm"] = None
            enriched["precipitacao_24h"] = None

            # Campo legado: mantido por compatibilidade.
            enriched["precipitation"] = None

            enriched["observation_time"] = None

            # Indicadores históricos derivados. A ausência permanece
            # explicitamente representada pelo contrato do serviço.
            enriched["historical_indicators"] = (
                historical_indicators_by_municipality.get(
                    municipality,
                    {},
                )
            )


            # ==================================================
            # DADOS DA OBSERVAÃ‡ÃƒO
            # ==================================================

            if observation:

                enriched["temperature"] = (
                    self._to_float(
                        observation.temperatura
                    )
                )

                enriched["humidity"] = (
                    self._to_float(
                        observation.umidade
                    )
                )

                enriched["wind_speed"] = (
                    self._to_float(
                        observation.velocidade_vento
                    )
                )

                enriched["cloud_cover"] = (
                    self._to_float(
                        observation.cobertura_nuvens
                    )
                )

                # --------------------------------------------------
                # CONTRATO METEOROLÃ“GICO CANÃ”NICO
                # --------------------------------------------------

                rain_now = getattr(
                    observation,
                    "chuva_agora",
                    None,
                )

                precipitation_1h = self._to_float(
                    getattr(
                        observation,
                        "precipitacao_1h",
                        None,
                    )
                )

                precipitation_24h = self._to_float(
                    getattr(
                        observation,
                        "precipitacao_24h",
                        None,
                    )
                )

                # VariÃ¡veis canÃ´nicas.
                enriched["rain_now"] = rain_now
                enriched["chuva_agora"] = rain_now

                enriched["precipitation_1h_mm"] = precipitation_1h
                enriched["precipitacao_1h"] = precipitation_1h

                enriched["precipitation_24h_mm"] = precipitation_24h
                enriched["precipitacao_24h"] = precipitation_24h

                # Compatibilidade com consumidores legados.
                # O campo genÃ©rico passa a representar explicitamente
                # a precipitaÃ§Ã£o da Ãºltima hora.
                enriched["precipitation"] = precipitation_1h

                # CondiÃ§Ã£o meteorolÃ³gica canÃ´nica, quando disponÃvel.
                enriched["weather_condition"] = getattr(
                    observation,
                    "condicao_tempo",
                    None,
                )

                if observation.observation_time:

                    enriched[
                        "observation_time"
                    ] = (
                        observation
                        .observation_time
                        .isoformat()
                    )

            # ==================================================
            # DADOS COMPLEMENTARES DO WEATHERDTO
            # ==================================================
            # Estes campos podem estar disponíveis na coleta atual mesmo
            # quando ainda não existem como colunas em WeatherObservation.
            # O serviço apenas transporta o valor recebido do Provider.

            current_dto = self._current_weather_dtos.get(municipality)

            if current_dto is not None:

                enriched["pressure"] = self._to_float(
                    getattr(current_dto, "pressure", None)
                )

                enriched["wind_direction"] = self._to_float(
                    getattr(current_dto, "wind_direction", None)
                )

                enriched["apparent_temperature"] = self._to_float(
                    getattr(current_dto, "apparent_temperature", None)
                )

                enriched["dew_point"] = self._to_float(
                    getattr(current_dto, "dew_point", None)
                )

                enriched["solar_radiation"] = self._to_float(
                    getattr(current_dto, "solar_radiation", None)
                )

                enriched["uv_index"] = self._to_float(
                    getattr(current_dto, "uv_index", None)
                )

                enriched["uv_index_max"] = self._to_float(
                    getattr(current_dto, "uv_index_max", None)
                )

                enriched["visibility"] = self._to_float(
                    getattr(current_dto, "visibility", None)
                )

                enriched["weather_condition"] = getattr(
                    current_dto,
                    "weather_condition",
                    None,
                ) or enriched["weather_condition"]

                enriched["sunrise"] = self._serialize_datetime(
                    getattr(current_dto, "sunrise", None)
                )

                enriched["sunset"] = self._serialize_datetime(
                    getattr(current_dto, "sunset", None)
                )

                enriched["daylight_duration_seconds"] = self._to_float(
                    getattr(current_dto, "daylight_duration_seconds", None)
                )

                enriched["observed_at"] = self._serialize_datetime(
                    getattr(current_dto, "observed_at", None)
                )

                enriched["retrieved_at"] = self._serialize_datetime(
                    getattr(current_dto, "retrieved_at", None)
                )

                enriched["quality_status"] = getattr(
                    current_dto,
                    "quality_status",
                    None,
                )

                enriched["confidence"] = self._to_float(
                    getattr(current_dto, "confidence", None)
                )

                enriched["source"] = getattr(
                    current_dto,
                    "source",
                    None,
                )

                enriched["source_type"] = getattr(
                    current_dto,
                    "source_type",
                    None,
                )

            # ==================================================
            # INDICADORES AGROCLIMÁTICOS — FASE 2
            # ==================================================
            agroclimate_indicators = (
                self.agroclimate_indicator_service.calculate(
                    enriched
                )
            )

            enriched["temperature"] = agroclimate_indicators["temperature"]
            enriched["temperature_class"] = agroclimate_indicators["temperature_class"]
            enriched["temperature_class_label"] = agroclimate_indicators["temperature_class_label"]
            enriched["precipitation_1h_mm"] = agroclimate_indicators["precipitation_1h_mm"]
            enriched["precipitation_24h_mm"] = agroclimate_indicators["precipitation_24h_mm"]

            # Contrato canônico da classificação pluviométrica 24h.
            # A classificação é produzida pelo AgroClimateIndicatorService;
            # este serviço apenas materializa o resultado no map_point.
            enriched["precipitation_24h_class"] = (
                agroclimate_indicators["precipitation_24h_class"]
            )
            enriched["precipitation_24h_class_label"] = (
                agroclimate_indicators["precipitation_24h_class_label"]
            )

            enriched["precipitacao_1h"] = agroclimate_indicators["precipitation_1h_mm"]
            enriched["precipitacao_24h"] = agroclimate_indicators["precipitation_24h_mm"]
            enriched["precipitation"] = agroclimate_indicators["precipitation_1h_mm"]

            # ==================================================
            # HISTÃ“RICO REAL DE GEADA
            # ==================================================

            historical = (
                historical_by_municipality.get(
                    municipality
                )
            )

            if historical is None:

                enriched["frost"] = False
                enriched["frost_occurrences"] = 0
                enriched["frost_last_date"] = None
                enriched["frost_temperature_minimum"] = None
                enriched["historical_frost"] = False

                # EvidÃªncia histÃ³rica estruturada.
                enriched["historical_total_days"] = 0
                enriched["historical_frost_days"] = 0
                enriched["historical_frost_frequency"] = 0.0
                enriched["historical_frost_episodes"] = 0
                enriched["historical_min_temperature"] = None

            else:

                frost_dates = historical["frost_dates"]
                total_days = historical["total_records"]
                frost_days = historical["frost_records"]

                enriched["frost"] = (
                    frost_days > 0
                )

                enriched["frost_occurrences"] = frost_days
                enriched["frost_last_date"] = historical["last_date"]
                enriched["frost_temperature_minimum"] = historical["last_minimum"]
                enriched["historical_frost"] = (
                    frost_days > 0
                )

                enriched["historical_total_days"] = total_days
                enriched["historical_frost_days"] = frost_days
                enriched["historical_frost_frequency"] = (
                    frost_days / total_days
                    if total_days > 0
                    else 0.0
                )
                enriched["historical_frost_episodes"] = (
                    self._count_frost_episodes(
                        frost_dates
                    )
                )
                enriched["historical_min_temperature"] = (
                    historical["minimum_temperature"]
                )

            enriched_points.append(
                enriched
            )

        # ==========================================================
        # CONTRATO TÉRMICO MATERIALIZADO
        # ==========================================================
        # Cada ponto devolvido por este método possui sempre: temperature,
        # temperature_class e temperature_class_label. Quando a temperatura
        # não está disponível, a classificação permanece explicitamente como
        # ``unavailable`` / ``Sem dado``. Assim, ausência de dado nunca é
        # convertida em uma faixa térmica válida por conveniência visual.

        return enriched_points

    # ==========================================================
    # AVALIAÃ‡ÃƒO MUNICIPAL ÃšNICA DO FRI
    # ==========================================================

    def _attach_frost_intelligence(
        self,
        map_points,
    ):
        """
        Executa exatamente uma avaliação de Inteligência por município.

        NÚCLEO DA CORREÇÃO — ALERTAS:

        - Cada município recebe um contexto próprio e isolado.
        - O resultado de Intelligence pertence exclusivamente ao município
          avaliado e permanece dentro do respectivo map_point.
        - O DashboardService não concatena alertas de municípios diferentes.
        - O contexto global de alerts permanece vazio nesta camada.
        - A DashboardFacade seleciona posteriormente o município principal.
        - FRI somente é obtido do resultado ``frost``.
        - O score de uma regra meteorológica não é apresentado como FRI.
        """

        if not map_points:
            return []

        evaluated_points = []

        for point in map_points:
            evaluated = dict(point)

            context = {
                "municipio_id": point.get("municipio_id"),
                "municipio_nome": (
                    point.get("municipio_nome")
                    or point.get("nome")
                ),
                "temperature": point.get("temperature"),
                "humidity": point.get("humidity"),
                "wind_speed": point.get("wind_speed"),
                "cloud_cover": point.get("cloud_cover"),
                "precipitation_24h_mm": point.get(
                    "precipitation_24h_mm"
                ),
                "altitude": point.get("altitude"),
                "historical_frost": point.get("historical_frost"),
                "historical_total_days": point.get(
                    "historical_total_days"
                ),
                "historical_frost_days": point.get(
                    "historical_frost_days"
                ),
                "historical_frost_frequency": point.get(
                    "historical_frost_frequency"
                ),
                "historical_frost_episodes": point.get(
                    "historical_frost_episodes"
                ),
                "historical_min_temperature": point.get(
                    "historical_min_temperature"
                ),
                "analysis_date": point.get("analysis_date"),
            }

            try:
                intelligence = self.frost_risk_service.process(
                    context
                )
            except Exception:
                intelligence = {}

            if not isinstance(intelligence, dict):
                intelligence = {}

            frost = intelligence.get("frost", {})
            if not isinstance(frost, dict):
                frost = {}

            rule_results = intelligence.get("rule_results", [])
            insights = intelligence.get("insights", [])
            recommendations = intelligence.get("recommendations", [])
            alerts = intelligence.get("alerts", [])
            explainability = intelligence.get("explainability", {})

            if not isinstance(rule_results, list):
                rule_results = []
            if not isinstance(insights, list):
                insights = []
            if not isinstance(recommendations, list):
                recommendations = []
            if not isinstance(alerts, list):
                alerts = []
            if not isinstance(explainability, dict):
                explainability = {}

            # Normalização transversal: deduplicação somente dentro da
            # avaliação do município corrente. Municípios distintos nunca
            # são comparados ou fundidos.
            alerts = self._normalize_municipal_alerts(
                alerts,
                municipio_id=point.get("municipio_id"),
                municipio_nome=(
                    point.get("municipio_nome")
                    or point.get("nome")
                ),
            )

            # FRI canônico: somente o resultado da FrostRule.
            evaluated["fri"] = frost.get("fri")
            if evaluated["fri"] is None:
                evaluated["fri"] = frost.get("score")

            evaluated["severity"] = frost.get("severity")
            evaluated["confidence"] = frost.get("confidence")

            evaluated["frost_factors"] = frost.get(
                "frost_factors"
            )
            if evaluated["frost_factors"] is None:
                evaluated["frost_factors"] = frost.get("factors")

            # Inteligência exclusivamente deste município.
            evaluated["rule_results"] = rule_results
            evaluated["insights"] = insights
            evaluated["recommendations"] = recommendations
            evaluated["alerts"] = alerts
            evaluated["explainability"] = explainability

            # Compatibilidade com a DashboardFacade.
            evaluated["insight"] = (
                insights[0] if insights else None
            )
            evaluated["recommendation"] = (
                recommendations[0]
                if recommendations
                else None
            )
            evaluated["alert"] = (
                alerts[0] if alerts else None
            )

            # Rastreabilidade da mesma avaliação.
            evaluated["frost_evaluation"] = frost
            evaluated["intelligence_evaluation"] = {
                "frost": frost,
                "rule_results": rule_results,
                "insights": insights,
                "recommendations": recommendations,
                "alerts": alerts,
                "explainability": explainability,
            }

            evaluated_points.append(evaluated)

        # Não criar, concatenar ou deduplicar alertas globais aqui.
        return evaluated_points

    @staticmethod
    def _normalize_municipal_alerts(
        alerts,
        municipio_id=None,
        municipio_nome=None,
    ):
        """
        Normaliza os alertas de uma única avaliação municipal.

        A deduplicação é intra-municipal. Alertas de municípios distintos
        permanecem independentes e nunca são fundidos aqui.
        """

        if not isinstance(alerts, list):
            return []

        normalized = []
        seen = set()

        for alert in alerts:
            if not isinstance(alert, dict):
                continue

            item = dict(alert)

            # Proveniência territorial explícita.
            item["municipio_id"] = municipio_id
            item["municipio_nome"] = municipio_nome

            identity = (
                item.get("id"),
                item.get("engine"),
                item.get("title"),
                item.get("message"),
                item.get("severity"),
                item.get("score"),
            )

            if identity in seen:
                continue

            seen.add(identity)
            normalized.append(item)

        return normalized


    # EPISÃ“DIOS HISTÃ“RICOS DE GEADA
    # ==========================================================

    @staticmethod
    def _count_frost_episodes(
        frost_dates,
    ):
        """
        Conta episÃ³dios distintos de geada.

        Dias consecutivos pertencem ao mesmo episÃ³dio.
        Dias separados por pelo menos um dia sem geada
        iniciam novo episÃ³dio.

        NÃ£o calcula risco. Apenas estrutura a evidÃªncia
        histÃ³rica para a camada de InteligÃªncia.
        """

        if not frost_dates:
            return 0

        ordered_dates = sorted(
            set(frost_dates)
        )

        episodes = 1
        previous_date = ordered_dates[0]

        for current_date in ordered_dates[1:]:

            if current_date != previous_date + timedelta(days=1):
                episodes += 1

            previous_date = current_date

        return episodes

    # ==========================================================
    # SERIALIZAÇÃO DE DATAS
    # ==========================================================

    @staticmethod
    def _serialize_datetime(value):
        """
        Converte datas recebidas pelo WeatherDTO para representação
        serializável no map_point, preservando None quando ausentes.
        """

        if value is None:
            return None

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return str(value)

    # ==========================================================
    # CONVERSÃƒO NUMÃ‰RICA
    # ==========================================================

    # ==========================================================
    # CONTEXTO METEOROLÓGICO CANÔNICO
    # ==========================================================

    def _build_canonical_weather_context(self):
        """
        Constrói o contexto meteorológico único do ciclo atual.

        Fonte exclusiva:
            self._current_weather_dtos

        O método não consulta Provider nem banco para obter uma nova
        observação. Apenas organiza os DTOs já produzidos por
        _refresh_current_weather().
        """

        municipios = list(
            Municipio.objects
            .all()
            .order_by("nome")
        )

        if not municipios:
            return None

        municipio = municipios[0]
        observation = self._current_weather_dtos.get(
            municipio.nome
        )

        if observation is None:
            return None

        precipitation_24h_values = []

        for municipio_monitorado in municipios:
            dto = self._current_weather_dtos.get(
                municipio_monitorado.nome
            )

            if dto is None:
                continue

            value = self._to_float(
                getattr(
                    dto,
                    "precipitation_24h_mm",
                    getattr(
                        dto,
                        "precipitacao_24h",
                        None,
                    ),
                )
            )

            if value is not None:
                precipitation_24h_values.append(value)

        precipitation_24h_average = None

        if (
            len(precipitation_24h_values)
            == len(municipios)
        ):
            precipitation_24h_average = (
                sum(precipitation_24h_values)
                / len(precipitation_24h_values)
            )

        return {
            "municipio": municipio,
            "observation": observation,
            "temperature": self._to_float(
                getattr(
                    observation,
                    "temperature",
                    getattr(
                        observation,
                        "temperatura",
                        None,
                    ),
                )
            ),
            "humidity": self._to_float(
                getattr(
                    observation,
                    "humidity",
                    getattr(
                        observation,
                        "umidade",
                        None,
                    ),
                )
            ),
            "precipitation_1h_mm": self._to_float(
                getattr(
                    observation,
                    "precipitation_1h_mm",
                    getattr(
                        observation,
                        "precipitacao_1h",
                        None,
                    ),
                )
            ),
            "precipitation_24h_mm": precipitation_24h_average,
            "precipitation_24h_values": precipitation_24h_values,
            "rain_now": getattr(
                observation,
                "rain_now",
                getattr(
                    observation,
                    "chuva_agora",
                    None,
                ),
            ),
            "wind_speed": self._to_float(
                getattr(
                    observation,
                    "wind_speed",
                    getattr(
                        observation,
                        "velocidade_vento",
                        None,
                    ),
                )
            ),
            "cloud_cover": self._to_float(
                getattr(
                    observation,
                    "cloud_cover",
                    getattr(
                        observation,
                        "cobertura_nuvens",
                        None,
                    ),
                )
            ),
        }


    @staticmethod
    def _to_float(
        value,
    ):

        if value is None:

            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 5.2 — INTEGRAÇÃO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.8
#
# Integração implementada:
#     HistoryService
#         -> HistoricalClimateIndicatorService
#         -> map_point["historical_indicators"]
#
# Indicadores integrados nesta etapa:
#     amplitude_termica_diaria
#     amplitude_termica_media
#     amplitude_termica_minima
#     amplitude_termica_maxima
#     amplitude_termica_dias_validos
#     amplitude_termica_dias_disponiveis
#
# Garantias preservadas:
#     - nenhuma regra de FRI é criada ou repetida;
#     - FrostRiskService continua sendo a única avaliação oficial do FRI;
#     - nenhum indicador é calculado no frontend;
#     - HistoryService permanece responsável apenas pela série histórica;
#     - HistoricalClimateIndicatorService permanece responsável pelo cálculo;
#     - None permanece None quando não há dado suficiente;
#     - os demais dados do map_point são preservados.
#
# A integração não altera ainda a interface visual. A apresentação dos novos
# indicadores será tratada somente na etapa correspondente do cronograma.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 5.3 — INTEGRAÇÃO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.9 — integração anterior da Fase 5.
#
# Evolução implementada:
#     HistoricalClimateIndicatorService v5.3
#         -> map_point["historical_indicators"]
#
# Indicador acrescentado nesta etapa:
#     frequencia_temperaturas_criticas
#
# Indicadores anteriores preservados:
#     tendencia_termica
#     tendencia_termica_diferenca
#     tendencia_termica_dias_validos
#     amplitude_termica_diaria
#     amplitude_termica_media
#     amplitude_termica_minima
#     amplitude_termica_maxima
#     amplitude_termica_dias_validos
#     amplitude_termica_dias_disponiveis
#
# Responsabilidades preservadas:
#     - HistoryService fornece a série histórica estruturada;
#     - HistoricalClimateIndicatorService calcula os indicadores;
#     - DashboardService somente integra e distribui os resultados;
#     - frontend não calcula indicadores;
#     - FRI continua com avaliação oficial única;
#     - nenhuma regra de severidade, confiança, alerta ou recomendação foi criada.
#
# Tratamento de ausência:
#     None permanece None quando não houver série válida suficiente.
#
# Nenhuma alteração visual foi realizada nesta etapa.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — FASE 8 / CORREÇÃO DE CONTRATO PLUVIOMÉTRICO 24H
# ============================================================================
#
# Correção: materialização explícita de precipitation_24h_class e
# precipitation_24h_class_label no map_point após a execução do
# AgroClimateIndicatorService.
#
# A regra de classificação permanece exclusivamente no serviço especializado.
# O DashboardService não cria limiares, não recalcula a classificação e não
# altera FRI, severidade, confiança, ranking ou demais indicadores.
#
# Objetivo: impedir que o valor numérico precipitation_24h_mm chegue ao
# consumidor sem os respectivos campos de classificação já produzidos pelo
# backend.
# ============================================================================

# ============================================================================
# AUDITORIA — NÚCLEO DO PROBLEMA: ALERTAS DUPLICADOS / CRUZADOS
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.8
#
# Resultado lógico:
#
#     Cada map_point possui um único contexto municipal.
#     Cada contexto executa uma única chamada ao FrostRiskService.
#     O resultado de alerts permanece restrito ao próprio map_point.
#
#     O DashboardService NÃO:
#         - concatena alertas dos seis municípios;
#         - cria uma coleção territorial de alerts;
#         - executa novamente o FrostRiskService;
#         - deduplica alertas por título/valor/severidade;
#         - transforma score meteorológico em FRI.
#
# Fluxo:
#
#     map_point municipal
#         -> contexto municipal isolado
#         -> FrostRiskService.process()
#         -> Intelligence municipal
#         -> map_point municipal
#         -> DashboardFacade
#         -> apresentação
#
# Escopo:
#
#     map_point["alerts"] = alertas daquele município.
#
#     context["alerts"] = []
#         no DashboardService; a seleção global permanece na Facade.
#
# O FRI é obtido exclusivamente de intelligence["frost"].
# precipitation_24h_mm é transportado no contexto canônico.
#
# ============================================================================

# ============================================================================
# AUDITORIA TRANSVERSAL — ALERTAS — FASE 3
# ============================================================================
#
# Resultado lógico consolidado:
#
# Fonte -> Aquisição -> Provider -> DTO -> Persistência
#       -> MapService -> map_point municipal
#       -> DashboardService
#       -> contexto municipal isolado
#       -> Intelligence
#       -> normalização municipal
#       -> map_point municipal
#       -> DashboardFacade
#       -> Apresentação
#
# Garantias:
# - uma avaliação Intelligence por município;
# - nenhum contexto municipal recebe dados de outro município;
# - precipitation_24h_mm é o dado pluviométrico canônico de entrada;
# - alerts são normalizados somente dentro da avaliação corrente;
# - alertas de municípios diferentes não são fundidos;
# - não existe agregação territorial de alerts no DashboardService;
# - context["alerts"] permanece reservado à seleção da camada Facade;
# - cada alerta recebe municipio_id e municipio_nome para rastreabilidade;
# - score permanece score;
# - FRI é derivado exclusivamente do resultado frost;
# - nenhuma regra de limiar foi recriada neste serviço;
# - não há segunda chamada ao FrostRiskService.
#
# A correção é de fluxo e escopo: impede que a camada DashboardService
# transforme resultados municipais em uma coleção territorial/global.
# ============================================================================


# ============================================================================
# AUDITORIA — FASE 3 — CORREÇÃO FINAL DO TRANSPORTE DE ALERTAS
# ============================================================================
#
# Problema identificado:
#     O DashboardService restringia ``context["alerts"]`` ao primeiro alerta
#     do município principal. Assim, uma regra meteorológica válida em outro
#     município podia existir no map_point municipal e ainda assim não chegar
#     ao painel global.
#
# Correção:
#     - cada município executa Intelligence uma única vez;
#     - cada map_point preserva ``municipal_alerts``;
#     - todos os alertas já produzidos são consolidados em
#       ``context["alerts"]``;
#     - a deduplicação é feita somente sobre a identidade do alerta já
#       materializado, sem nova regra ou novo cálculo;
#     - o ponto principal recebe a coleção territorial como contrato de
#       transporte para a DashboardFacade;
#     - FRI continua vindo exclusivamente de ``intelligence["frost"]``;
#     - ``precipitation_24h_mm`` continua sendo a métrica canônica da regra
#       meteorológica;
#     - nenhum score meteorológico é convertido em FRI;
#     - nenhum consumidor precisa recalcular ou reinterpretar o alerta.
#
# Fluxo corrigido:
#
#     Fonte
#       -> Aquisição
#       -> Provider
#       -> DTO
#       -> Persistência
#       -> MapService / map_point
#       -> DashboardService
#       -> Intelligence municipal
#       -> alerts municipais
#       -> consolidação territorial canônica
#       -> DashboardFacade
#       -> painel de alertas
#
# Resultado esperado no cenário validado:
#     Frost Rule:
#         FRI = 34
#     Meteorological Alert Rule:
#         precipitation_24h_mm = 20.5
#         severidade = low
#
# Portanto, o painel deve receber 2 alertas quando os dois resultados
# estiverem materializados no ciclo.
#
# Nenhuma alteração realizada em:
#     - KPIService
#     - ChartService
#     - MapService
#     - popup
#     - JavaScript do mapa
#     - regras de FRI
#
# ============================================================================
