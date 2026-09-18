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
        # Cada map_point mantém a inteligência e os alertas do próprio
        # município em ``municipal_alerts`` e ``alerts``.
        #
        # Para o painel global, os alertas já materializados pela camada
        # de Inteligência são consolidados uma única vez neste ciclo.
        # Esta etapa é somente de transporte/normalização:
        # não recalcula regras, não altera severidade e não transforma
        # score meteorológico em FRI.
        #
        # O ponto principal recebe a coleção territorial somente como
        # contrato de transporte para a DashboardFacade.
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
            enriched["precipitation_1h_mm"] = agroclimate_indicators.get(
                "precipitation_1h_mm",
                enriched["precipitation_1h_mm"],
            )
            enriched["precipitation_24h_mm"] = agroclimate_indicators.get(
                "precipitation_24h_mm",
                enriched["precipitation_24h_mm"],
            )

            # Contrato canônico da classificação pluviométrica 24h.
            # A classificação é produzida pelo AgroClimateIndicatorService;
            # este serviço apenas materializa o resultado no map_point.
            # O serviço especializado é a autoridade desses campos.
            # ``get`` mantém compatibilidade com testes/adapters que retornam
            # apenas o subconjunto de indicadores disponível no contrato.
            # Ausência permanece None e nunca é convertida em valor sintético.
            enriched["precipitation_24h_class"] = (
                agroclimate_indicators.get("precipitation_24h_class")
            )
            enriched["precipitation_24h_class_label"] = (
                agroclimate_indicators.get(
                    "precipitation_24h_class_label"
                )
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
        - O DashboardService não recalcula alertas nem cruza contextos
          municipais.
        - Os alertas permanecem municipais durante a avaliação.
        - A consolidação territorial posterior é apenas de transporte.
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

            # --------------------------------------------------
            # API CANÔNICA DO FRI
            # --------------------------------------------------
            # O FRI é obtido pela API pública evaluate_frost().
            # O resultado completo da mesma execução permanece
            # disponível em FrostRiskService.last_result.
            #
            # Isso evita:
            #   - segunda execução do IntelligenceEngine;
            #   - divergência entre FRI e demais resultados;
            #   - dependência direta do DashboardService sobre a
            #     estrutura interna do motor.
            try:
                frost = self.frost_risk_service.evaluate_frost(
                    context
                )
            except Exception:
                frost = {}

            if not isinstance(frost, dict):
                frost = {}

            intelligence = getattr(
                self.frost_risk_service,
                "last_result",
                {},
            )

            if not isinstance(intelligence, dict):
                intelligence = {}

            # Compatibilidade defensiva com testes/adapters que
            # implementam apenas evaluate_frost(). Em produção,
            # FrostRiskService V1.1/V1.2 sempre fornece last_result
            # com o resultado completo da mesma avaliação.
            if not intelligence:
                intelligence = {
                    "frost": frost,
                }
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
        Constrói o contexto meteorológico regional único do ciclo atual.

        Fonte exclusiva:
            self._current_weather_dtos

        O método não realiza nova aquisição e não consulta Provider.
        Os DTOs foram produzidos previamente por
        ``_refresh_current_weather()``.

        Contrato semântico:
            - ``temperature`` representa a média regional das temperaturas
              disponíveis quando todos os municípios monitorados possuem
              observação válida;
            - ``precipitation_1h_mm`` representa a média regional da chuva
              da última hora quando todos os municípios possuem valor válido;
            - ``precipitation_24h_mm`` representa a média regional do
              acumulado de 24 horas quando todos os municípios possuem
              valor válido;
            - ``rain_now`` representa ocorrência de chuva no território
              quando todos os estados municipais são conhecidos;
            - ``municipio`` permanece como compatibilidade e identifica o
              município principal do ciclo. Ele não define os valores
              regionais agregados.

        Ausência de dado:
            nenhuma média regional é calculada a partir de subconjunto
            silenciosamente. Se faltar um valor obrigatório em qualquer
            município monitorado, a média correspondente permanece None.
        """

        municipios = list(
            Municipio.objects
            .all()
            .order_by("nome")
        )

        if not municipios:
            return None

        dto_by_name = {
            municipio.nome: self._current_weather_dtos.get(municipio.nome)
            for municipio in municipios
        }

        valid_dtos = [
            dto
            for dto in dto_by_name.values()
            if dto is not None
        ]

        if not valid_dtos:
            return None

        # O município principal é apenas uma referência de transporte.
        # Os indicadores regionais não dependem de sua posição na lista.
        municipio = next(
            (
                municipio
                for municipio in municipios
                if dto_by_name.get(municipio.nome) is not None
            ),
            None,
        )

        observation = (
            dto_by_name.get(municipio.nome)
            if municipio is not None
            else None
        )

        def dto_value(dto, *names):
            for name in names:
                value = getattr(dto, name, None)
                if value is not None:
                    return self._to_float(value)
            return None

        def aggregate(values):
            if len(values) != len(municipios):
                return None
            if any(value is None for value in values):
                return None
            return sum(values) / len(values)

        temperature_values = [
            dto_value(dto, "temperature", "temperatura")
            for dto in dto_by_name.values()
            if dto is not None
        ]
        humidity_values = [
            dto_value(dto, "humidity", "umidade")
            for dto in dto_by_name.values()
            if dto is not None
        ]
        precipitation_1h_values = [
            dto_value(
                dto,
                "precipitation_1h_mm",
                "precipitacao_1h",
            )
            for dto in dto_by_name.values()
            if dto is not None
        ]
        precipitation_24h_values = [
            dto_value(
                dto,
                "precipitation_24h_mm",
                "precipitacao_24h",
            )
            for dto in dto_by_name.values()
            if dto is not None
        ]
        wind_speed_values = [
            dto_value(dto, "wind_speed", "velocidade_vento")
            for dto in dto_by_name.values()
            if dto is not None
        ]
        cloud_cover_values = [
            dto_value(dto, "cloud_cover", "cobertura_nuvens")
            for dto in dto_by_name.values()
            if dto is not None
        ]

        rain_states = [
            getattr(
                dto,
                "rain_now",
                getattr(dto, "chuva_agora", None),
            )
            for dto in dto_by_name.values()
            if dto is not None
        ]

        all_municipalities_available = (
            len(valid_dtos) == len(municipios)
        )

        rain_now = None
        if all_municipalities_available and all(
            state is not None for state in rain_states
        ):
            rain_now = any(bool(state) for state in rain_states)

        return {
            # Compatibilidade com KPIService atual.
            "municipio": municipio,
            "observation": observation,

            # Identidade explícita do município de referência.
            "primary_municipio": municipio,

            # Escopo regional explícito.
            "municipality_count": len(municipios),
            "municipalities_available": len(valid_dtos),
            "all_municipalities_available": all_municipalities_available,

            # Valores regionais canônicos.
            "temperature": aggregate(temperature_values),
            "temperature_mean": aggregate(temperature_values),
            "humidity": aggregate(humidity_values),
            "humidity_mean": aggregate(humidity_values),
            "precipitation_1h_mm": aggregate(
                precipitation_1h_values
            ),
            "precipitation_1h_values": precipitation_1h_values,
            "precipitation_24h_mm": aggregate(
                precipitation_24h_values
            ),
            "precipitation_24h_values": precipitation_24h_values,
            "rain_now": rain_now,

            # Campos estruturados adicionais.
            "wind_speed": aggregate(wind_speed_values),
            "wind_speed_values": wind_speed_values,
            "cloud_cover": aggregate(cloud_cover_values),
            "cloud_cover_values": cloud_cover_values,
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
# REGISTRO DE AUDITORIA — VERSÃO 3.10 — CONTRATO CANÔNICO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.8 — arquivo corrente anexado em 17/09/2026.
#
# Correções incorporadas nesta versão:
#
# 1. CONTEXTO REGIONAL
#    O contexto meteorológico deixou de usar silenciosamente o primeiro
#    município como origem dos valores regionais. ``municipio`` permanece
#    apenas como referência de compatibilidade.
#
# 2. TEMPERATURA REGIONAL
#    ``temperature`` e ``temperature_mean`` passam a representar a média
#    das temperaturas dos municípios monitorados quando todos possuem
#    observação válida.
#
# 3. PRECIPITAÇÃO REGIONAL
#    ``precipitation_1h_mm`` e ``precipitation_24h_mm`` são agregados
#    explicitamente no contexto regional. O acumulado de 24h mantém a
#    semântica oficial já adotada pelo projeto: média dos municípios.
#
# 4. AUSÊNCIA DE DADOS
#    Uma média regional não é produzida a partir de subconjunto semântico-
#    mente incompleto. Quando faltar dado obrigatório em qualquer município,
#    a média correspondente permanece None.
#
# 5. CHUVA AGORA
#    ``rain_now`` só é materializado no contexto regional quando todos os
#    estados municipais estão disponíveis. A ocorrência territorial é True
#    quando pelo menos um município registra chuva.
#
# 6. IDENTIDADE DO MUNICÍPIO PRINCIPAL
#    ``primary_municipio`` torna explícita a finalidade de transporte do
#    município de referência, evitando que sua posição na ordenação seja
#    confundida com uma definição regional.
#
# 7. ALERTAS
#    A implementação corrente consolida os alertas municipais já produzidos
#    pela Inteligência para o painel global. Esta operação não executa regra,
#    não recalcula score, não altera severidade e não converte score em FRI.
#
# 8. FRI
#    O FRI continua sendo obtido exclusivamente de ``intelligence["frost"]``
#    dentro de ``_attach_frost_intelligence``. O Ranking deve consumir esse
#    valor materializado e não recalculá-lo.
#
# 9. INTELLIGENCE MUNICIPAL
#    Cada município recebe uma avaliação isolada por ciclo. Os resultados
#    são mantidos no respectivo map_point.
#
# 10. FRONTEND
#     Nenhum cálculo de indicador, FRI, severidade ou classificação é
#     introduzido neste serviço para consumo pelo frontend.
#
# ============================================================================
# CRITÉRIO DE ACEITE — DASHBOARD SERVICE V3.10
# ============================================================================
#
# A versão somente deve ser considerada aceita quando todos os itens abaixo
# forem comprovados no projeto:
#
# [A] FUNCIONAL
#     - Django inicia sem erro.
#     - Dashboard principal responde normalmente.
#     - Os seis municípios monitorados continuam presentes.
#
# [B] CONTEXTO METEOROLÓGICO
#     - temperature == média dos seis municípios quando todos disponíveis.
#     - precipitation_24h_mm == média dos seis municípios.
#     - precipitation_1h_mm == média dos seis municípios.
#     - nenhum valor None é convertido em zero.
#     - municipality_count == 6 no cenário operacional completo.
#
# [C] MUNICIPAL
#     - cada map_point mantém sua própria temperatura.
#     - cada map_point mantém sua própria precipitation_1h_mm.
#     - cada map_point mantém sua própria precipitation_24h_mm.
#     - popup não recebe a média regional como temperatura municipal.
#
# [D] INTELIGÊNCIA
#     - uma avaliação por município por ciclo.
#     - FRI vem somente de FrostRule/intelligence["frost"].
#     - score meteorológico permanece score.
#     - severidade permanece a produzida pela Inteligência.
#
# [E] ALERTAS
#     - alertas mantêm municipio_id e municipio_nome.
#     - alertas de municípios distintos não são fundidos indevidamente.
#     - a coleção global contém os alertas efetivamente materializados.
#     - o painel global não recria regras.
#
# [F] REGRESSÃO
#     - testes existentes de clima permanecem aprovados.
#     - testes existentes de dashboard permanecem aprovados.
#     - testes de ranking não demonstram nova execução de FrostRiskService.
#     - nenhum contrato frontend existente perde campo canônico.
#
# [G] AUDITORIA ESTRUTURAL
#     - arquivo novo deve manter todas as responsabilidades legítimas da
#       versão-base.
#     - nenhuma função pública existente é removida.
#     - nenhuma dependência necessária é removida sem migração equivalente.
#     - a nova versão deve possuir número de linhas igual ou superior ao
#       arquivo-base auditado.
#
# REJEIÇÃO AUTOMÁTICA:
#     - temperatura regional voltar a depender do primeiro município;
#     - precipitation_24h_mm deixar de ser média regional no contexto KPI;
#     - dado ausente virar zero sem regra explícita;
#     - FRI ser recalculado em outro consumidor;
#     - score meteorológico ser apresentado como FRI;
#     - município A receber inteligência do município B;
#     - regressão em qualquer teste crítico.
#
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA — VERSÃO 3.11 — CORREÇÃO COORDENADA DO FRI
# ============================================================================
#
# Base real:
#     dashboard_service.py utilizado no projeto em 17/09/2026.
#
# Problema identificado:
#     O DashboardService utilizava FrostRiskService.process() diretamente,
#     enquanto o contrato de teste e a API de acesso específico ao FRI utilizam
#     FrostRiskService.evaluate_frost().
#
# Correção:
#     1. evaluate_frost(context) tornou-se a API canônica para obter o FRI.
#     2. last_result transporta o resultado completo da mesma execução.
#     3. rule_results, insights, recommendations, alerts e explainability
#        continuam provenientes da mesma avaliação.
#     4. Nenhum cálculo de FRI foi introduzido no DashboardService.
#
# Garantia arquitetural:
#     contexto municipal
#         -> FrostRiskService.evaluate_frost()
#         -> IntelligenceEngine (uma execução)
#         -> last_result
#         -> FRI + demais resultados
#         -> map_point
#
# Não permitido:
#     - chamar process() e evaluate_frost() no mesmo ciclo;
#     - executar o IntelligenceEngine duas vezes para o mesmo município;
#     - recalcular FRI no DashboardService;
#     - usar score de regra meteorológica como FRI;
#     - misturar inteligência entre municípios.
#
# Critério de aceite:
#     python manage.py check
#     python manage.py test clima dashboard core
#
# Resultado esperado:
#     28 testes OK, sem regressão.
# ============================================================================
