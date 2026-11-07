"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃƒÆ’O PAULO - UNIVESP

Curso...........: Bacharelado em CiÃƒÂªncia de Dados
Disciplina......: Trabalho de ConclusÃƒÂ£o de Curso (TCC)
Projeto.........: AgroClima CafÃƒÂ©
MÃƒÂ³dulo..........: Dashboard
Arquivo.........: dashboard_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: SÃƒÂ£o JoÃƒÂ£o da Boa Vista - SP
Ano.............: 2026

DescriÃƒÂ§ÃƒÂ£o.......:
ServiÃƒÂ§o responsÃƒÂ¡vel por consolidar todos os dados estruturados
da Dashboard Principal.

Responsabilidades:
    Ã¢â‚¬Â¢ Consolidar KPIs, grÃƒÂ¡ficos, ranking, eventos e mapa.
    Ã¢â‚¬Â¢ Enriquecer os pontos geogrÃƒÂ¡ficos com dados meteorolÃƒÂ³gicos.
    Ã¢â‚¬Â¢ Disponibilizar ocorrÃƒÂªncias histÃƒÂ³ricas reais de geada.
    Ã¢â‚¬Â¢ Disponibilizar indicadores histÃƒÂ³ricos estruturados para a
      camada de InteligÃƒÂªncia.
    Ã¢â‚¬Â¢ NÃƒÂ£o executar regras de InteligÃƒÂªncia.

VersÃƒÂ£o..........: 3.12
===============================================================================
"""

from core.intelligence.hail_threshold_classification_service import HailThresholdClassificationService

from datetime import timedelta
import logging

from clima.models import (
    HistoricalWeatherDaily,
    Provider,
    WeatherObservation,
)
from clima.services.weather_service import WeatherService
from clima.services.hail_meteorological_input_service import HailMeteorologicalInputService
from core.intelligence.hail_project_context_contract import HailProjectContextContract
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
from dashboard.services.hydric_pressure_regional_service import (
    HydricPressureRegionalService,
)
from dashboard.services.hydric_pressure_regional_synthesis_service import (
    HydricPressureRegionalSynthesisService,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Consolida todos os dados estruturados utilizados pela
    Dashboard.

    NÃƒÂ£o executa regras de negÃƒÂ³cio inteligentes.

    A camada de InteligÃƒÂªncia permanece responsabilidade da
    DashboardFacade.
    """

    def __init__(self):

        self.kpi_service = KPIService()

        self.chart_service = ChartService()

        self.ranking_service = RankingService()

        self.events_service = EventsService()

        self.map_service = MapService()

        # ServiÃ§o meteorolÃ³gico responsÃ¡vel por atualizar a observaÃ§Ã£o
        # atual antes da montagem dos KPIs e dos pontos do mapa.
        self.weather_service = WeatherService()

        # AvaliaÃƒÂ§ÃƒÂ£o oficial e ÃƒÂºnica do FRI por municÃƒpio.
        # O resultado ÃƒÂ© incorporado ao map_point e passa a ser a
        # fonte autoritativa consumida por mapa, popup, ranking,
        # alerta e insight.
        self.frost_risk_service = FrostRiskService()

        # ServiÃ§o responsÃ¡vel pela classificaÃ§Ã£o operacional da temperatura.
        # A classificaÃ§Ã£o Ã© derivada exclusivamente da temperatura observada
        # e materializada no map_point para consumo uniforme pelos componentes.
        # O serviÃ§o nÃ£o acessa banco de dados, API, FRI ou regras de geada.
        self.thermal_classification_service = ThermalClassificationService()

        self.agroclimate_indicator_service = AgroClimateIndicatorService()

        # HistÃ³rico canÃ´nico utilizado como fonte dos indicadores derivados.
        # O HistoryService fornece a sÃ©rie; o serviÃ§o especializado calcula
        # somente os indicadores autorizados da Fase 5.
        self.history_service = HistoryService()
        self.historical_climate_indicator_service = (
            HistoricalClimateIndicatorService()
        )

        # ComposiÃ§Ã£o regional dos resultados jÃ¡ produzidos por
        # HYDRIC_PRESSURE_001. Este serviÃ§o nÃ£o recalcula balanÃ§o nem regra.
        self.hydric_pressure_regional_service = (
            HydricPressureRegionalService()
        )
        self.hydric_pressure_regional_synthesis_service = (
            HydricPressureRegionalSynthesisService()
        )

        # MantÃ©m os DTOs da atualizaÃ§Ã£o meteorolÃ³gica corrente disponÃ­veis
        # para o enriquecimento do map_point. Isso evita perder campos que
        # jÃ¡ existem no WeatherDTO, mas ainda nÃ£o possuem persistÃªncia prÃ³pria
        # em WeatherObservation, como UV e dados de nascer/pÃ´r do sol.
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
        # ATUALIZAÃ‡ÃƒO METEOROLÃ“GICA
        # ======================================================
        # WeatherObservation Ã© atualizada antes dos KPIs e do mapa.
        # Uma falha isolada nÃ£o interrompe os demais municÃ­pios.
        # ======================================================

        weather_refresh = self._refresh_current_weather()
        context["weather_refresh"] = weather_refresh

        # ======================================================
        # CONTEXTO CANÃ”NICO ÃšNICO â€” KPIs
        # ======================================================
        #
        # O KPIService nÃ£o realiza nova aquisiÃ§Ã£o meteorolÃ³gica.
        # Ele recebe exclusivamente o contexto jÃ¡ produzido pelo
        # ciclo corrente de atualizaÃ§Ã£o do DashboardService.
        #
        # Assim, KPI, mapa e demais consumidores partem da mesma
        # cadeia de dados, sem segunda consulta ou interpretaÃ§Ã£o.
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
        # GRÃƒFICOS
        # ======================================================

        context["chart"] = (
            self.chart_service.get_chart()
        )

        # ======================================================
        # PERÃƒODOS DO GRÃƒFICO
        #
        # Disponibiliza separadamente:
        #
        #   Hoje
        #   7 dias
        #   30 dias
        #   HistÃƒÂ³rico
        #
        # O frontend apenas alterna entre os dados
        # jÃƒÂ¡ consolidados pelo ChartService.
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
        # DADOS CLIMÃƒTICOS DOS MUNICÃƒPIOS
        #
        # Somente dados estruturados.
        #
        # Nenhuma regra de inteligÃƒÂªncia ÃƒÂ© executada aqui.
        # ======================================================

        map_points = self._attach_climate_data(
            map_points
        )

        # ======================================================
        # AVALIAÃƒâ€¡ÃƒÆ’O MUNICIPAL ÃƒÅ¡NICA DO FRI
        #
        # Cada municÃƒpio ÃƒÂ© avaliado exatamente uma vez depois
        # que os dados climÃƒÂ¡ticos e histÃƒÂ³ricos jÃƒÂ¡ foram anexados.
        # O resultado completo passa a integrar o map_point.
        # Nenhum consumidor posterior deve recalcular o FRI.
        # ======================================================

        map_points = self._attach_frost_intelligence(
            map_points
        )

        # MP-01.12 â€” contexto global canÃ´nico da avaliaÃ§Ã£o de granizo.
        # Reutiliza o resultado municipal jÃ¡ calculado; nÃ£o reavalia a regra
        # e nÃ£o mistura potencial meteorolÃ³gico com evento factual observado.
        threshold_set = HailThresholdClassificationService().get_latest_provisional()
        context["hail_assessments"] = self._compose_hail_assessments(
            map_points,
            threshold_set=threshold_set,
        )

        # MP-01.6 e MP-01.7 apenas compÃµem resultados jÃ¡ calculados.
        self._attach_hydric_pressure_context(
            context=context,
            map_points=map_points,
            primary_municipio_id=kpis.get("municipio_id"),
        )

        # ======================================================
        # ALERTAS CANÃ”NICOS DA DASHBOARD â€” ESCOPO TERRITORIAL
        #
        # Cada map_point mantÃ©m a inteligÃªncia e os alertas do prÃ³prio
        # municÃ­pio em ``municipal_alerts`` e ``alerts``.
        #
        # Para o painel global, os alertas jÃ¡ materializados pela camada
        # de InteligÃªncia sÃ£o consolidados uma Ãºnica vez neste ciclo.
        # Esta etapa Ã© somente de transporte/normalizaÃ§Ã£o:
        # nÃ£o recalcula regras, nÃ£o altera severidade e nÃ£o transforma
        # score meteorolÃ³gico em FRI.
        #
        # O ponto principal recebe a coleÃ§Ã£o territorial somente como
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

            # Preserva a coleÃ§Ã£o original produzida pela Intelligence
            # para rastreabilidade municipal.
            point["municipal_alerts"] = list(municipal_alerts)

            # ConsolidaÃ§Ã£o somente de resultados jÃ¡ produzidos.
            # Nenhuma regra Ã© executada nesta etapa.
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

            # Cada ponto continua disponibilizando seus prÃ³prios alertas
            # para consumidores territoriais, sem substituir a origem.
            point["alerts"] = list(municipal_alerts)
            point["alert"] = (
                municipal_alerts[0]
                if municipal_alerts
                else None
            )

        # A coleÃ§Ã£o territorial Ã© o contrato global jÃ¡ consolidado.
        # A Facade deve apenas distribuÃ­-la, sem reconstruÃ­-la.
        context["alerts"] = territorial_alerts

        # O ponto principal funciona como portador do contrato global
        # para compatibilidade com consumidores que recebem a inteligÃªncia
        # a partir do municÃ­pio principal.
        if primary_point is not None:
            primary_point["alerts"] = list(territorial_alerts)

        context["map_points"] = map_points

        # ======================================================
        # RANKING
        #
        # O Ranking recebe exatamente os mesmos map_points que
        # foram disponibilizados ao mapa. O FRI jÃƒÂ¡ estÃƒÂ¡ calculado
        # nesses objetos e nÃƒÂ£o pode ser recalculado pelo Ranking.
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

        # ``alerts`` jÃ¡ foi publicado acima como coleÃ§Ã£o canÃ´nica
        # de cardinalidade mÃ¡xima 1. A Facade deve apenas consumir
        # esse resultado, sem reconstruÃ­-lo a partir de municÃ­pios.

        return context

    # ==========================================================
    # DADOS CLIMÃƒTICOS DO MAPA
    # ==========================================================


    # ==========================================================
    # ATUALIZAÃ‡ÃƒO METEOROLÃ“GICA PARA A DASHBOARD
    # ==========================================================

    def _refresh_current_weather(self):
        """
        Atualiza o clima atual de todos os municÃ­pios antes da
        consolidaÃ§Ã£o dos KPIs e dos pontos consumidos pelo mapa.

        NÃ£o calcula FRI nem executa regras de InteligÃªncia.
        Cada municÃ­pio Ã© processado independentemente.
        """

        atualizados = 0
        erros = 0
        resultados = []

        # Cada execuÃ§Ã£o representa um novo ciclo de atualizaÃ§Ã£o.
        # Remove DTOs de municÃ­pios que eventualmente falhem neste ciclo.
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

                # O DTO Ã© a fonte corrente dos campos meteorolÃ³gicos
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
        Adiciona aos pontos geogrÃƒÂ¡ficos os dados estruturados
        disponÃƒveis para cada municÃƒpio.

        Dados meteorolÃƒÂ³gicos:
            Ã¢â‚¬Â¢ temperatura;
            Ã¢â‚¬Â¢ umidade;
            Ã¢â‚¬Â¢ vento;
            Ã¢â‚¬Â¢ cobertura de nuvens;
            Ã¢â‚¬Â¢ chuva ocorrendo agora;
            Ã¢â‚¬Â¢ precipitaÃƒÂ§ÃƒÂ£o da ÃƒÂºltima hora;
            Ã¢â‚¬Â¢ precipitaÃƒÂ§ÃƒÂ£o acumulada em 24 horas;
            Ã¢â‚¬Â¢ horÃƒÂ¡rio da observaÃƒÂ§ÃƒÂ£o.

        Contrato canÃƒÂ´nico:
            Ã¢â‚¬Â¢ chuva_agora;
            Ã¢â‚¬Â¢ precipitacao_1h;
            Ã¢â‚¬Â¢ precipitacao_24h.

        O campo legado ``precipitation`` ÃƒÂ© preservado no map_point
        para compatibilidade, mas seu valor corresponde Ãƒ
        precipitaÃƒÂ§ÃƒÂ£o da ÃƒÂºltima hora nesta etapa da migraÃƒÂ§ÃƒÂ£o.

        Dados histÃƒÂ³ricos de geada:
            Ã¢â‚¬Â¢ ocorrÃƒÂªncia;
            Ã¢â‚¬Â¢ quantidade de ocorrÃƒÂªncias;
            Ã¢â‚¬Â¢ quantidade total de registros histÃƒÂ³ricos;
            Ã¢â‚¬Â¢ frequÃƒÂªncia histÃƒÂ³rica de geada;
            Ã¢â‚¬Â¢ quantidade de episÃƒÂ³dios de geada;
            Ã¢â‚¬Â¢ ÃƒÂºltima data de ocorrÃƒÂªncia;
            Ã¢â‚¬Â¢ temperatura mÃƒnima da ÃƒÂºltima ocorrÃƒÂªncia;
            Ã¢â‚¬Â¢ menor temperatura registrada em ocorrÃƒÂªncia de geada.

        CritÃƒÂ©rio objetivo para ocorrÃƒÂªncia histÃƒÂ³rica de geada:

            temperatura_minima <= 0 Ã‚Â°C

        Este mÃƒÂ©todo NÃƒÆ’O:
            Ã¢â‚¬Â¢ calcula FRI;
            Ã¢â‚¬Â¢ classifica risco;
            Ã¢â‚¬Â¢ calcula confianÃƒÂ§a;
            Ã¢â‚¬Â¢ gera alertas;
            Ã¢â‚¬Â¢ gera recomendaÃƒÂ§ÃƒÂµes;
            Ã¢â‚¬Â¢ executa regras de InteligÃƒÂªncia.

        Os indicadores histÃƒÂ³ricos adicionados aqui constituem
        Os indicadores histÃ³ricos adicionados aqui constituem
        evidÃªncia estruturada para a etapa posterior da FrostRule.
        O cÃ¡lculo Ã© delegado ao HistoricalClimateIndicatorService.
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
        # ÃƒÅ¡LTIMA OBSERVAÃƒâ€¡ÃƒÆ’O METEOROLÃƒâ€œGICA
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
        # HISTÃƒâ€œRICO REAL DE GEADAS
        #
        # Fonte:
        # HistoricalWeatherDaily
        #
        # Somente registros persistidos sÃƒÂ£o considerados.
        # NÃƒÂ£o utiliza previsÃƒÂ£o.
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

            # CritÃƒÂ©rio real de geada.
            if minimum <= 0:

                summary["frost_records"] += 1

                if record.data:
                    summary["frost_dates"].append(
                        record.data
                    )

                # O queryset estÃƒÂ¡ em ordem crescente; portanto,
                # o ÃƒÂºltimo registro de geada ÃƒÂ© o mais recente.
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
        # INDICADORES HISTÃ“RICOS â€” FASE 5
        # ======================================================
        # A sÃ©rie diÃ¡ria Ã© obtida pelo HistoryService. O cÃ¡lculo da
        # amplitude tÃ©rmica permanece exclusivamente no serviÃ§o
        # especializado HistoricalClimateIndicatorService.
        #
        # O resultado Ã© estruturado por municÃ­pio e serÃ¡ anexado ao
        # map_point sem alterar a avaliaÃ§Ã£o oficial do FRI.
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

            # Compatibilidade defensiva com testes e instanciaÃ§Ãµes controladas
            # que utilizam __new__ e, portanto, nÃ£o executam __init__.
            # Em produÃ§Ã£o, o atributo Ã© sempre criado no __init__.
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
                historical_data,
                municipality_key=municipio.pk,
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
            # PADRÃƒÆ’O SEM DADO
            # ==================================================

            enriched["temperature"] = None

            # ClassificaÃ§Ã£o tÃ©rmica canÃ´nica.
            # O valor permanece ``unavailable`` atÃ© que uma temperatura
            # vÃ¡lida seja efetivamente disponibilizada pela observaÃ§Ã£o.
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
            # CONTRATO METEOROLÃƒâ€œGICO CANÃƒâ€NICO Ã¢â‚¬â€ FASE 1
            # ==================================================

            # Chuva ocorrendo agora.
            enriched["rain_now"] = None
            enriched["chuva_agora"] = None

            # PrecipitaÃƒÂ§ÃƒÂ£o da ÃƒÂºltima hora.
            enriched["precipitation_1h_mm"] = None
            enriched["precipitacao_1h"] = None

            # PrecipitaÃƒÂ§ÃƒÂ£o acumulada em 24 horas.
            enriched["precipitation_24h_mm"] = None
            enriched["precipitacao_24h"] = None

            # ETo diÃ¡ria corrente recebida diretamente do WeatherDTO.
            # AusÃªncia permanece None; nÃ£o hÃ¡ cÃ¡lculo ou estimativa aqui.
            enriched["eto_mm_day"] = None

            # Campo legado: mantido por compatibilidade.
            enriched["precipitation"] = None

            enriched["observation_time"] = None

            # Indicadores histÃ³ricos derivados. A ausÃªncia permanece
            # explicitamente representada pelo contrato do serviÃ§o.
            enriched["historical_indicators"] = (
                historical_indicators_by_municipality.get(
                    municipality,
                    {},
                )
            )


            # ==================================================
            # DADOS DA OBSERVAÃƒâ€¡ÃƒÆ’O
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
                # CONTRATO METEOROLÃƒâ€œGICO CANÃƒâ€NICO
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

                # VariÃƒÂ¡veis canÃƒÂ´nicas.
                enriched["rain_now"] = rain_now
                enriched["chuva_agora"] = rain_now

                enriched["precipitation_1h_mm"] = precipitation_1h
                enriched["precipitacao_1h"] = precipitation_1h

                enriched["precipitation_24h_mm"] = precipitation_24h
                enriched["precipitacao_24h"] = precipitation_24h

                # Compatibilidade com consumidores legados.
                # O campo genÃƒÂ©rico passa a representar explicitamente
                # a precipitaÃƒÂ§ÃƒÂ£o da ÃƒÂºltima hora.
                enriched["precipitation"] = precipitation_1h

                # CondiÃƒÂ§ÃƒÂ£o meteorolÃƒÂ³gica canÃƒÂ´nica, quando disponÃƒvel.
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
            # Estes campos podem estar disponÃ­veis na coleta atual mesmo
            # quando ainda nÃ£o existem como colunas em WeatherObservation.
            # O serviÃ§o apenas transporta o valor recebido do Provider.

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

                # ETo diÃ¡ria corrente: transporte direto do WeatherDTO.
                enriched["eto_mm_day"] = self._to_float(
                    getattr(current_dto, "eto_mm_day", None)
                )

            # ==================================================
            # INDICADORES AGROCLIMÃTICOS â€” FASE 2
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

            # Contrato canÃ´nico da classificaÃ§Ã£o pluviomÃ©trica 24h.
            # A classificaÃ§Ã£o Ã© produzida pelo AgroClimateIndicatorService;
            # este serviÃ§o apenas materializa o resultado no map_point.
            # O serviÃ§o especializado Ã© a autoridade desses campos.
            # ``get`` mantÃ©m compatibilidade com testes/adapters que retornam
            # apenas o subconjunto de indicadores disponÃ­vel no contrato.
            # AusÃªncia permanece None e nunca Ã© convertida em valor sintÃ©tico.
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
            # HISTÃƒâ€œRICO REAL DE GEADA
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

                # EvidÃƒÂªncia histÃƒÂ³rica estruturada.
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
        # CONTRATO TÃ‰RMICO MATERIALIZADO
        # ==========================================================
        # Cada ponto devolvido por este mÃ©todo possui sempre: temperature,
        # temperature_class e temperature_class_label. Quando a temperatura
        # nÃ£o estÃ¡ disponÃ­vel, a classificaÃ§Ã£o permanece explicitamente como
        # ``unavailable`` / ``Sem dado``. Assim, ausÃªncia de dado nunca Ã©
        # convertida em uma faixa tÃ©rmica vÃ¡lida por conveniÃªncia visual.

        return enriched_points

    # ==========================================================
    # AVALIAÃƒâ€¡ÃƒÆ’O MUNICIPAL ÃƒÅ¡NICA DO FRI
    # ==========================================================

    def _attach_frost_intelligence(
        self,
        map_points,
    ):
        """
        Executa exatamente uma avaliaÃ§Ã£o de InteligÃªncia por municÃ­pio.

        NÃšCLEO DA CORREÃ‡ÃƒO â€” ALERTAS:

        - Cada municÃ­pio recebe um contexto prÃ³prio e isolado.
        - O resultado de Intelligence pertence exclusivamente ao municÃ­pio
          avaliado e permanece dentro do respectivo map_point.
        - O DashboardService nÃ£o recalcula alertas nem cruza contextos
          municipais.
        - Os alertas permanecem municipais durante a avaliaÃ§Ã£o.
        - A consolidaÃ§Ã£o territorial posterior Ã© apenas de transporte.
        - FRI somente Ã© obtido do resultado ``frost``.
        - O score de uma regra meteorolÃ³gica nÃ£o Ã© apresentado como FRI.
        """

        if not map_points:
            return []

        # MP-01.12: uma chamada Ã  interface pÃºblica do serviÃ§o coleta cada
        # municÃ­pio em uma solicitaÃ§Ã£o Open-Meteo individual, fora do loop de
        # inteligÃªncia. Falha individual nÃ£o interrompe o dashboard.
        hail_inputs_by_id = {}
        try:
            hail_inputs_by_id = HailMeteorologicalInputService().fetch_for_points(
                map_points
            )
        except Exception:
            logger.exception(
                "Falha ao adquirir variÃ¡veis meteorolÃ³gicas MP-01.12 para granizo."
            )
            hail_inputs_by_id = {}

        evaluated_points = []

        for point in map_points:
            evaluated = dict(point)
            historical_indicators = (
                point.get("historical_indicators") or {}
            )

            # HailMeteorologicalInputService indexa a saÃ­da pelo id
            # original de cada map_point. Esse Ã© o identificador primÃ¡rio
            # do contrato de MapService; municipio_id Ã© apenas alias de
            # compatibilidade e nÃ£o deve sombrear a chave canÃ´nica.
            point_id = point.get("id")
            municipio_id = point.get("municipio_id")
            hail_input = hail_inputs_by_id.get(point_id)
            if hail_input is None and municipio_id != point_id:
                hail_input = hail_inputs_by_id.get(municipio_id)

            # RecuperaÃ§Ã£o isolada de sÃ©rie parcial. AusÃªncia e falha sÃ£o
            # representadas como dados ausentes apÃ³s os retries do serviÃ§o;
            # a regra de granizo continua executada uma Ãºnica vez pelo motor.
            required_hail_variables = (
                "cape",
                "wind_speed_925hPa",
                "wind_direction_925hPa",
                "wind_speed_500hPa",
                "wind_direction_500hPa",
            )
            hail_series = (
                hail_input.get("series")
                if isinstance(hail_input, dict)
                else None
            )
            hail_input_incomplete = (
                not isinstance(hail_series, dict)
                or not hail_series
                or any(
                    hail_series.get(variable) is None
                    for variable in required_hail_variables
                )
            )

            # A ausÃªncia indica que a aquisiÃ§Ã£o individual jÃ¡ falhou ou que
            # nÃ£o havia coordenadas utilizÃ¡veis. O serviÃ§o jÃ¡ aplicou seu
            # retry HTTP; repetir aqui multiplicaria as tentativas. Reconsulta
            # somente sÃ©ries parciais efetivamente recebidas, que nÃ£o entram
            # no cache e podem ser recuperadas nesta chamada isolada.
            has_partial_hail_input = (
                isinstance(hail_input, dict)
                and isinstance(hail_series, dict)
                and bool(hail_series)
                and hail_input_incomplete
            )
            if has_partial_hail_input:
                try:
                    individual_inputs = HailMeteorologicalInputService().fetch_for_points(
                        [point]
                    )
                    individual_input = individual_inputs.get(point_id)
                    if individual_input is None and municipio_id != point_id:
                        individual_input = individual_inputs.get(municipio_id)
                    if isinstance(individual_input, dict) and individual_input.get("series"):
                        hail_input = individual_input
                except Exception:
                    logger.exception(
                        "Falha na recuperaÃ§Ã£o meteorolÃ³gica individual de granizo "
                        "para municÃ­pio id=%s nome=%s.",
                        point_id,
                        point.get("nome") or point.get("municipio_nome"),
                    )

            if not isinstance(hail_input, dict):
                hail_input = {}

            context = {
                # MP-01.12 â€” variÃ¡veis meteorolÃ³gicas reais da coordenada municipal.
                # A proveniÃªncia e o instante vÃ¡lido acompanham os valores.
                "series": hail_input.get("series") or {},
                "provenance": hail_input.get("provenance") or {},
                "valid_from": hail_input.get("valid_from"),
                "valid_to": hail_input.get("valid_to"),

                # MapService publica o PK do municÃ­pio como ``id``. O alias
                # ``municipio_id`` continua aceito para pontos jÃ¡ adaptados.
                "municipio_id": (
                    point.get("municipio_id") or point.get("id")
                ),
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
                "analysis_date": (
                    point.get("analysis_date")
                    or historical_indicators.get("analysis_date")
                ),

                # ==================================================
                # BALANÃ‡O HÃDRICO CANÃ”NICO â€” MP-01.6
                #
                # Estes campos sÃ£o somente transportados do resultado
                # jÃ¡ calculado por HistoricalClimateIndicatorService.
                # HydricPressureRule continua sendo a autoridade para
                # produzir hydric_state.
                # ==================================================
                "hydric_balance_method": (
                    historical_indicators.get(
                        "hydric_balance_method"
                    )
                ),
                "hydric_balance_scope": (
                    historical_indicators.get(
                        "hydric_balance_scope"
                    )
                ),
                "hydric_balance_status": (
                    historical_indicators.get(
                        "hydric_balance_status"
                    )
                ),
                "cad_mm": (
                    historical_indicators.get("cad_mm")
                ),
                "arm_final_mm": (
                    historical_indicators.get(
                        "arm_final_mm"
                    )
                ),
                "arm_final_percentual": (
                    historical_indicators.get(
                        "arm_final_percentual"
                    )
                ),
                "deficit_hidrico_acumulado": (
                    historical_indicators.get(
                        "deficit_hidrico_acumulado"
                    )
                ),
                "excedente_hidrico_acumulado": (
                    historical_indicators.get(
                        "excedente_hidrico_acumulado"
                    )
                ),
                "deficit_hidrico_mm": (
                    historical_indicators.get(
                        "deficit_hidrico_mm"
                    )
                ),
                "excedente_hidrico_mm": (
                    historical_indicators.get(
                        "excedente_hidrico_mm"
                    )
                ),
            }

            # --------------------------------------------------
            # RESULTADO INTEGRAL DA AVALIAÃ‡ÃƒO MUNICIPAL
            # --------------------------------------------------
            # O retorno vinculado Ã  chamada contÃ©m o FRI e o resultado
            # integral do IntelligenceEngine desta avaliaÃ§Ã£o municipal.
            #
            # Isso evita:
            #   - segunda execuÃ§Ã£o do IntelligenceEngine;
            #   - divergÃªncia entre FRI e demais resultados;
            #   - leitura posterior de estado mutÃ¡vel compartilhado.
            intelligence = {}

            try:
                evaluate_with_result = getattr(
                    type(self.frost_risk_service),
                    "evaluate_frost_with_result",
                    None,
                )
                if callable(evaluate_with_result):
                    intelligence = self.frost_risk_service.evaluate_frost_with_result(
                        context
                    )
                else:
                    # Compatibilidade com adapters legados que sÃ³ expÃµem
                    # evaluate_frost(): preserva o FRI sem consultar estado
                    # compartilhado ou executar o motor uma segunda vez.
                    frost = self.frost_risk_service.evaluate_frost(context)
                    intelligence = {"frost": frost}
            except Exception:
                intelligence = {}

            if not isinstance(intelligence, dict):
                intelligence = {}

            frost = intelligence.get("frost", {})
            if not isinstance(frost, dict):
                frost = {}

            rule_results = intelligence.get("rule_results", [])
            if not isinstance(rule_results, list):
                rule_results = []

            # Contrato de granizo: comparar todos os resultados da mesma
            # execuÃ§Ã£o e escolher o payload com maior completude estrutural.
            # derived + drivers nÃ£o bastam se complementary_values se perdeu.
            # Nenhuma regra Ã© reexecutada e nenhum indicador Ã© recalculado aqui.
            hail = intelligence.get("hail", {})
            if not isinstance(hail, dict):
                hail = {}

            hail_candidates = [
                result for result in rule_results
                if isinstance(result, dict)
                and (
                    result.get("rule_id") == "HAIL_POTENTIAL_001"
                    or result.get("id") == "HAIL_POTENTIAL_001"
                )
            ]

            def _hail_completeness(result):
                if not isinstance(result, dict):
                    return (0, 0, 0, 0, 0, 0)
                derived = result.get("derived")
                drivers = result.get("drivers")
                complementary = result.get("complementary_values")
                if not isinstance(complementary, dict):
                    complementary = (
                        (result.get("municipal_result") or {}).get(
                            "complementary_values"
                        )
                        if isinstance(result.get("municipal_result"), dict)
                        else {}
                    )
                provenance = result.get("provenance")
                data_quality = result.get("data_quality")
                return (
                    int(isinstance(derived, dict) and bool(derived)),
                    int(isinstance(drivers, (list, tuple)) and bool(drivers)),
                    int(isinstance(complementary, dict) and bool(complementary)),
                    int(result.get("assessment_status") == "ASSESSED"),
                    int(isinstance(provenance, dict) and bool(provenance)),
                    int(isinstance(data_quality, dict) and bool(data_quality)),
                )

            if hail_candidates:
                best_candidate = max(
                    [hail, *hail_candidates],
                    key=_hail_completeness,
                )
                if _hail_completeness(best_candidate) > _hail_completeness(hail):
                    hail = best_candidate

            if not isinstance(hail, dict):
                hail = {}
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

            # NormalizaÃ§Ã£o transversal: deduplicaÃ§Ã£o somente dentro da
            # avaliaÃ§Ã£o do municÃ­pio corrente. MunicÃ­pios distintos nunca
            # sÃ£o comparados ou fundidos.
            alerts = self._normalize_municipal_alerts(
                alerts,
                municipio_id=(
                    point.get("municipio_id") or point.get("id")
                ),
                municipio_nome=(
                    point.get("municipio_nome")
                    or point.get("nome")
                ),
            )

            # FRI canÃ´nico: somente o resultado da FrostRule.
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

            # InteligÃªncia exclusivamente deste municÃ­pio.
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

            # Rastreabilidade da mesma avaliaÃ§Ã£o.
            evaluated["frost_evaluation"] = frost

            # MP-01.11 / MP-01.12 â€” transporte do resultado experimental
            # produzido na mesma execuÃ§Ã£o do IntelligenceEngine. A ausÃªncia
            # de variÃ¡veis obrigatÃ³rias permanece explÃ­cita no resultado da
            # HailPotentialRule; nÃ£o Ã© convertida em potencial baixo/zero.
            evaluated["hail_potential_evaluation"] = hail
            evaluated["hail_meteorological_input"] = {
                "series": dict(hail_input.get("series") or {}),
                "valid_from": hail_input.get("valid_from"),
                "valid_to": hail_input.get("valid_to"),
                "provenance": dict(hail_input.get("provenance") or {}),
            }
            evaluated["intelligence_evaluation"] = {
                "frost": frost,
                "hail": hail,
                "rule_results": rule_results,
                "insights": insights,
                "recommendations": recommendations,
                "alerts": alerts,
                "explainability": explainability,
            }

            evaluated_points.append(evaluated)

        # NÃ£o criar, concatenar ou deduplicar alertas globais aqui.
        return evaluated_points

    @staticmethod
    def _compose_hail_assessments(map_points, threshold_set=None):
        """
        Publica o contrato global a partir das avaliaÃ§Ãµes municipais jÃ¡
        produzidas pela execuÃ§Ã£o Ãºnica de InteligÃªncia.
        """
        assessments = []
        classification_service = HailThresholdClassificationService()

        for point in map_points or []:
            if not isinstance(point, dict):
                continue

            intelligence = point.get("intelligence_evaluation")
            if not isinstance(intelligence, dict):
                intelligence = {}

            hail = intelligence.get("hail")
            fallback_candidates = [
                point.get("hail_potential_evaluation"),
            ]
            rule_results = point.get("rule_results", [])
            if isinstance(rule_results, list):
                fallback_candidates.extend(
                    result for result in rule_results
                    if isinstance(result, dict)
                    and (
                        result.get("rule_id") == "HAIL_POTENTIAL_001"
                        or result.get("id") == "HAIL_POTENTIAL_001"
                    )
                )

            # NÃ£o aceitar um dicionÃ¡rio vazio/incompleto como autoridade
            # quando a mesma avaliaÃ§Ã£o jÃ¡ contÃ©m o resultado canÃ´nico completo.
            candidates = [
                candidate
                for candidate in [hail, *fallback_candidates]
                if isinstance(candidate, dict)
                and any(
                    key in candidate
                    for key in (
                        "assessment_status",
                        "rule_id",
                        "id",
                        "derived",
                        "drivers",
                    )
                )
            ]
            if not candidates:
                continue

            def _project_hail_completeness(candidate):
                derived = candidate.get("derived")
                drivers = candidate.get("drivers")
                complementary = candidate.get("complementary_values")
                if not isinstance(complementary, dict):
                    municipal_result = candidate.get("municipal_result")
                    complementary = (
                        municipal_result.get("complementary_values", {})
                        if isinstance(municipal_result, dict)
                        else {}
                    )
                provenance = candidate.get("provenance")
                data_quality = candidate.get("data_quality")
                return (
                    int(isinstance(derived, dict) and bool(derived)),
                    int(isinstance(drivers, (list, tuple)) and bool(drivers)),
                    int(isinstance(complementary, dict) and bool(complementary)),
                    int(candidate.get("assessment_status") == "ASSESSED"),
                    int(isinstance(provenance, dict) and bool(provenance)),
                    int(isinstance(data_quality, dict) and bool(data_quality)),
                )

            hail = max(candidates, key=_project_hail_completeness)

            assessment = (
                HailProjectContextContract.from_municipal_result(
                                    hail=hail,
                                    municipio_id=point.get("id", point.get("municipio_id")),
                                    municipio_nome=point.get("nome", point.get("municipio_nome")),
                                ).as_dict()
            )
            assessment["experimental_threshold_classification"] = (
                classification_service.evaluate(
                    hail,
                    threshold_set=threshold_set,
                )
            )
            assessments.append(assessment)

        return assessments

    def _compose_hydric_pressure_regional(self, map_points):
        """
        ReÃºne exclusivamente os resultados municipais jÃ¡ produzidos por
        HYDRIC_PRESSURE_001 na mesma avaliaÃ§Ã£o de InteligÃªncia.

        NÃ£o recalcula balanÃ§o, nÃ£o executa HydricPressureRule novamente e
        nÃ£o cria um novo estado hÃ­drico regional.
        """
        results = []

        for point in map_points or []:
            rule_results = point.get("rule_results", [])
            if not isinstance(rule_results, list):
                continue

            for result in rule_results:
                if not isinstance(result, dict):
                    continue

                if result.get("rule_id") != "HYDRIC_PRESSURE_001":
                    continue

                results.append(dict(result))

        service = getattr(
            self,
            "hydric_pressure_regional_service",
            None,
        )
        if service is None:
            service = HydricPressureRegionalService()
            self.hydric_pressure_regional_service = service

        return service.compose(results)

    def _attach_hydric_pressure_context(
        self,
        context,
        map_points,
        primary_municipio_id=None,
    ):
        """Transporta a coleÃ§Ã£o MP-01.6 e sua sÃ­ntese MP-01.7."""
        regional_context = self._compose_hydric_pressure_regional(
            map_points
        )

        synthesis_service = getattr(
            self,
            "hydric_pressure_regional_synthesis_service",
            None,
        )
        if synthesis_service is None:
            synthesis_service = HydricPressureRegionalSynthesisService()
            self.hydric_pressure_regional_synthesis_service = (
                synthesis_service
            )

        synthesis = synthesis_service.synthesize(regional_context)

        context["hydric_pressure_regional"] = regional_context
        context["hydric_pressure_regional_synthesis"] = synthesis

        # A explicabilidade recebe a sÃ­ntese pronta pela API do mesmo
        # IntelligenceEngine. Esta chamada nÃ£o avalia regras nem altera FRI.
        context["hydric_pressure_regional_explainability"] = (
            self.frost_risk_service.intelligence.explain_regional_evidence(
                context
            )
        )

        primary_point = next(
            (
                point
                for point in map_points or []
                if point.get("id", point.get("municipio_id"))
                == primary_municipio_id
            ),
            None,
        )
        if primary_point is not None:
            primary_point["hydric_pressure_regional"] = regional_context
            primary_point["hydric_pressure_regional_synthesis"] = synthesis

        return context


    @staticmethod
    def _normalize_municipal_alerts(
        alerts,
        municipio_id=None,
        municipio_nome=None,
    ):
        """
        Normaliza os alertas de uma Ãºnica avaliaÃ§Ã£o municipal.

        A deduplicaÃ§Ã£o Ã© intra-municipal. Alertas de municÃ­pios distintos
        permanecem independentes e nunca sÃ£o fundidos aqui.
        """

        if not isinstance(alerts, list):
            return []

        normalized = []
        seen = set()

        for alert in alerts:
            if not isinstance(alert, dict):
                continue

            item = dict(alert)

            # ProveniÃªncia territorial explÃ­cita.
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


    # EPISÃƒâ€œDIOS HISTÃƒâ€œRICOS DE GEADA
    # ==========================================================

    @staticmethod
    def _count_frost_episodes(
        frost_dates,
    ):
        """
        Conta episÃƒÂ³dios distintos de geada.

        Dias consecutivos pertencem ao mesmo episÃƒÂ³dio.
        Dias separados por pelo menos um dia sem geada
        iniciam novo episÃƒÂ³dio.

        NÃƒÂ£o calcula risco. Apenas estrutura a evidÃƒÂªncia
        histÃƒÂ³rica para a camada de InteligÃƒÂªncia.
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
    # SERIALIZAÃ‡ÃƒO DE DATAS
    # ==========================================================

    @staticmethod
    def _serialize_datetime(value):
        """
        Converte datas recebidas pelo WeatherDTO para representaÃ§Ã£o
        serializÃ¡vel no map_point, preservando None quando ausentes.
        """

        if value is None:
            return None

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return str(value)

    # ==========================================================
    # CONVERSÃƒÆ’O NUMÃƒâ€°RICA
    # ==========================================================

    # ==========================================================
    # CONTEXTO METEOROLÃ“GICO CANÃ”NICO
    # ==========================================================

    def _build_canonical_weather_context(self):
        """
        ConstrÃ³i o contexto meteorolÃ³gico regional Ãºnico do ciclo atual.

        Fonte exclusiva:
            self._current_weather_dtos

        O mÃ©todo nÃ£o realiza nova aquisiÃ§Ã£o e nÃ£o consulta Provider.
        Os DTOs foram produzidos previamente por
        ``_refresh_current_weather()``.

        Contrato semÃ¢ntico:
            - ``temperature`` representa a mÃ©dia regional das temperaturas
              disponÃ­veis quando todos os municÃ­pios monitorados possuem
              observaÃ§Ã£o vÃ¡lida;
            - ``precipitation_1h_mm`` representa a mÃ©dia regional da chuva
              da Ãºltima hora quando todos os municÃ­pios possuem valor vÃ¡lido;
            - ``precipitation_24h_mm`` representa a mÃ©dia regional do
              acumulado de 24 horas quando todos os municÃ­pios possuem
              valor vÃ¡lido;
            - ``eto_mm_day`` representa a mÃ©dia regional da ETo diÃ¡ria
              corrente quando todos os municÃ­pios possuem valor vÃ¡lido;
            - ``rain_now`` representa ocorrÃªncia de chuva no territÃ³rio
              quando todos os estados municipais sÃ£o conhecidos;
            - ``municipio`` permanece como compatibilidade e identifica o
              municÃ­pio principal do ciclo. Ele nÃ£o define os valores
              regionais agregados.

        AusÃªncia de dado:
            nenhuma mÃ©dia regional Ã© calculada a partir de subconjunto
            silenciosamente. Se faltar um valor obrigatÃ³rio em qualquer
            municÃ­pio monitorado, a mÃ©dia correspondente permanece None.
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

        # O municÃ­pio principal Ã© apenas uma referÃªncia de transporte.
        # Os indicadores regionais nÃ£o dependem de sua posiÃ§Ã£o na lista.
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
        eto_values = [
            dto_value(
                dto,
                "eto_mm_day",
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

        # Acumulados histÃ³ricos canÃ´nicos de precipitaÃ§Ã£o.
        # A fonte Ã© exclusivamente HistoricalWeatherDaily atravÃ©s do
        # HistoryService; nÃ£o hÃ¡ substituiÃ§Ã£o por precipitation_24h_mm.
        precipitation_7d_mm = (
            self.history_service.precipitation_7d_mm()
        )
        precipitation_30d_mm = (
            self.history_service.precipitation_30d_mm()
        )

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

            # Identidade explÃ­cita do municÃ­pio de referÃªncia.
            "primary_municipio": municipio,

            # Escopo regional explÃ­cito.
            "municipality_count": len(municipios),
            "municipalities_available": len(valid_dtos),
            "all_municipalities_available": all_municipalities_available,

            # Valores regionais canÃ´nicos.
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
            "eto_mm_day": aggregate(eto_values),
            "eto_values": eto_values,

            # MÃ©tricas temporais canÃ´nicas para consumidores derivados.
            "precipitation_7d_mm": precipitation_7d_mm,
            "precipitation_30d_mm": precipitation_30d_mm,

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
# REGISTRO DE AUDITORIA â€” FASE 5.2 â€” INTEGRAÃ‡ÃƒO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.8
#
# IntegraÃ§Ã£o implementada:
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
#     - nenhuma regra de FRI Ã© criada ou repetida;
#     - FrostRiskService continua sendo a Ãºnica avaliaÃ§Ã£o oficial do FRI;
#     - nenhum indicador Ã© calculado no frontend;
#     - HistoryService permanece responsÃ¡vel apenas pela sÃ©rie histÃ³rica;
#     - HistoricalClimateIndicatorService permanece responsÃ¡vel pelo cÃ¡lculo;
#     - None permanece None quando nÃ£o hÃ¡ dado suficiente;
#     - os demais dados do map_point sÃ£o preservados.
#
# A integraÃ§Ã£o nÃ£o altera ainda a interface visual. A apresentaÃ§Ã£o dos novos
# indicadores serÃ¡ tratada somente na etapa correspondente do cronograma.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA â€” FASE 5.3 â€” INTEGRAÃ‡ÃƒO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.9 â€” integraÃ§Ã£o anterior da Fase 5.
#
# EvoluÃ§Ã£o implementada:
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
#     - HistoryService fornece a sÃ©rie histÃ³rica estruturada;
#     - HistoricalClimateIndicatorService calcula os indicadores;
#     - DashboardService somente integra e distribui os resultados;
#     - frontend nÃ£o calcula indicadores;
#     - FRI continua com avaliaÃ§Ã£o oficial Ãºnica;
#     - nenhuma regra de severidade, confianÃ§a, alerta ou recomendaÃ§Ã£o foi criada.
#
# Tratamento de ausÃªncia:
#     None permanece None quando nÃ£o houver sÃ©rie vÃ¡lida suficiente.
#
# Nenhuma alteraÃ§Ã£o visual foi realizada nesta etapa.
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA â€” FASE 8 / CORREÃ‡ÃƒO DE CONTRATO PLUVIOMÃ‰TRICO 24H
# ============================================================================
#
# CorreÃ§Ã£o: materializaÃ§Ã£o explÃ­cita de precipitation_24h_class e
# precipitation_24h_class_label no map_point apÃ³s a execuÃ§Ã£o do
# AgroClimateIndicatorService.
#
# A regra de classificaÃ§Ã£o permanece exclusivamente no serviÃ§o especializado.
# O DashboardService nÃ£o cria limiares, nÃ£o recalcula a classificaÃ§Ã£o e nÃ£o
# altera FRI, severidade, confianÃ§a, ranking ou demais indicadores.
#
# Objetivo: impedir que o valor numÃ©rico precipitation_24h_mm chegue ao
# consumidor sem os respectivos campos de classificaÃ§Ã£o jÃ¡ produzidos pelo
# backend.
# ============================================================================

# ============================================================================
# REGISTRO DE AUDITORIA â€” VERSÃƒO 3.10 â€” CONTRATO CANÃ”NICO
# ============================================================================
#
# Arquivo-base:
#     dashboard_service.py v3.8 â€” arquivo corrente anexado em 17/09/2026.
#
# CorreÃ§Ãµes incorporadas nesta versÃ£o:
#
# 1. CONTEXTO REGIONAL
#    O contexto meteorolÃ³gico deixou de usar silenciosamente o primeiro
#    municÃ­pio como origem dos valores regionais. ``municipio`` permanece
#    apenas como referÃªncia de compatibilidade.
#
# 2. TEMPERATURA REGIONAL
#    ``temperature`` e ``temperature_mean`` passam a representar a mÃ©dia
#    das temperaturas dos municÃ­pios monitorados quando todos possuem
#    observaÃ§Ã£o vÃ¡lida.
#
# 3. PRECIPITAÃ‡ÃƒO REGIONAL
#    ``precipitation_1h_mm`` e ``precipitation_24h_mm`` sÃ£o agregados
#    explicitamente no contexto regional. O acumulado de 24h mantÃ©m a
#    semÃ¢ntica oficial jÃ¡ adotada pelo projeto: mÃ©dia dos municÃ­pios.
#
# 4. AUSÃŠNCIA DE DADOS
#    Uma mÃ©dia regional nÃ£o Ã© produzida a partir de subconjunto semÃ¢ntico-
#    mente incompleto. Quando faltar dado obrigatÃ³rio em qualquer municÃ­pio,
#    a mÃ©dia correspondente permanece None.
#
# 5. CHUVA AGORA
#    ``rain_now`` sÃ³ Ã© materializado no contexto regional quando todos os
#    estados municipais estÃ£o disponÃ­veis. A ocorrÃªncia territorial Ã© True
#    quando pelo menos um municÃ­pio registra chuva.
#
# 6. IDENTIDADE DO MUNICÃPIO PRINCIPAL
#    ``primary_municipio`` torna explÃ­cita a finalidade de transporte do
#    municÃ­pio de referÃªncia, evitando que sua posiÃ§Ã£o na ordenaÃ§Ã£o seja
#    confundida com uma definiÃ§Ã£o regional.
#
# 7. ALERTAS
#    A implementaÃ§Ã£o corrente consolida os alertas municipais jÃ¡ produzidos
#    pela InteligÃªncia para o painel global. Esta operaÃ§Ã£o nÃ£o executa regra,
#    nÃ£o recalcula score, nÃ£o altera severidade e nÃ£o converte score em FRI.
#
# 8. FRI
#    O FRI continua sendo obtido exclusivamente de ``intelligence["frost"]``
#    dentro de ``_attach_frost_intelligence``. O Ranking deve consumir esse
#    valor materializado e nÃ£o recalculÃ¡-lo.
#
# 9. INTELLIGENCE MUNICIPAL
#    Cada municÃ­pio recebe uma avaliaÃ§Ã£o isolada por ciclo. Os resultados
#    sÃ£o mantidos no respectivo map_point.
#
# 10. FRONTEND
#     Nenhum cÃ¡lculo de indicador, FRI, severidade ou classificaÃ§Ã£o Ã©
#     introduzido neste serviÃ§o para consumo pelo frontend.
#
# ============================================================================
# CRITÃ‰RIO DE ACEITE â€” DASHBOARD SERVICE V3.10
# ============================================================================
#
# A versÃ£o somente deve ser considerada aceita quando todos os itens abaixo
# forem comprovados no projeto:
#
# [A] FUNCIONAL
#     - Django inicia sem erro.
#     - Dashboard principal responde normalmente.
#     - Os seis municÃ­pios monitorados continuam presentes.
#
# [B] CONTEXTO METEOROLÃ“GICO
#     - temperature == mÃ©dia dos seis municÃ­pios quando todos disponÃ­veis.
#     - precipitation_24h_mm == mÃ©dia dos seis municÃ­pios.
#     - precipitation_1h_mm == mÃ©dia dos seis municÃ­pios.
#     - nenhum valor None Ã© convertido em zero.
#     - municipality_count == 6 no cenÃ¡rio operacional completo.
#
# [C] MUNICIPAL
#     - cada map_point mantÃ©m sua prÃ³pria temperatura.
#     - cada map_point mantÃ©m sua prÃ³pria precipitation_1h_mm.
#     - cada map_point mantÃ©m sua prÃ³pria precipitation_24h_mm.
#     - popup nÃ£o recebe a mÃ©dia regional como temperatura municipal.
#
# [D] INTELIGÃŠNCIA
#     - uma avaliaÃ§Ã£o por municÃ­pio por ciclo.
#     - FRI vem somente de FrostRule/intelligence["frost"].
#     - score meteorolÃ³gico permanece score.
#     - severidade permanece a produzida pela InteligÃªncia.
#
# [E] ALERTAS
#     - alertas mantÃªm municipio_id e municipio_nome.
#     - alertas de municÃ­pios distintos nÃ£o sÃ£o fundidos indevidamente.
#     - a coleÃ§Ã£o global contÃ©m os alertas efetivamente materializados.
#     - o painel global nÃ£o recria regras.
#
# [F] REGRESSÃƒO
#     - testes existentes de clima permanecem aprovados.
#     - testes existentes de dashboard permanecem aprovados.
#     - testes de ranking nÃ£o demonstram nova execuÃ§Ã£o de FrostRiskService.
#     - nenhum contrato frontend existente perde campo canÃ´nico.
#
# [G] AUDITORIA ESTRUTURAL
#     - arquivo novo deve manter todas as responsabilidades legÃ­timas da
#       versÃ£o-base.
#     - nenhuma funÃ§Ã£o pÃºblica existente Ã© removida.
#     - nenhuma dependÃªncia necessÃ¡ria Ã© removida sem migraÃ§Ã£o equivalente.
#     - a nova versÃ£o deve possuir nÃºmero de linhas igual ou superior ao
#       arquivo-base auditado.
#
# REJEIÃ‡ÃƒO AUTOMÃTICA:
#     - temperatura regional voltar a depender do primeiro municÃ­pio;
#     - precipitation_24h_mm deixar de ser mÃ©dia regional no contexto KPI;
#     - dado ausente virar zero sem regra explÃ­cita;
#     - FRI ser recalculado em outro consumidor;
#     - score meteorolÃ³gico ser apresentado como FRI;
#     - municÃ­pio A receber inteligÃªncia do municÃ­pio B;
#     - regressÃ£o em qualquer teste crÃ­tico.
#
# ============================================================================

# ============================================================================
# REGISTRO DE AUDITORIA â€” VERSÃƒO 3.12 â€” INTEGRAÃ‡ÃƒO MP-01.6 â€” PRESSÃƒO HÃDRICA REGIONAL
# ============================================================================
#
# Base real:
#     dashboard_service.py utilizado no projeto em 17/09/2026.
#
# Problema identificado:
#     O DashboardService utilizava FrostRiskService.process() diretamente,
#     enquanto o contrato de teste e a API de acesso especÃ­fico ao FRI utilizam
#     FrostRiskService.evaluate_frost().
#
# CorreÃ§Ã£o:
#     1. evaluate_frost_with_result(context) retorna o resultado completo.
#     2. evaluate_frost(context) permanece compatÃ­vel e retorna somente FRI.
#     3. rule_results, insights, recommendations, alerts e explainability
#        continuam provenientes da mesma avaliaÃ§Ã£o.
#     4. O transporte nÃ£o usa estado compartilhado mutÃ¡vel.
#     5. Nenhum cÃ¡lculo de FRI foi introduzido no DashboardService.
#
# Garantia arquitetural:
#     contexto municipal
#         -> FrostRiskService.evaluate_frost_with_result()
#         -> IntelligenceEngine (uma execuÃ§Ã£o)
#         -> retorno vinculado Ã  chamada
#         -> FRI + demais resultados
#         -> map_point
#
# NÃ£o permitido:
#     - chamar process() e evaluate_frost() no mesmo ciclo;
#     - executar o IntelligenceEngine duas vezes para o mesmo municÃ­pio;
#     - recalcular FRI no DashboardService;
#     - usar score de regra meteorolÃ³gica como FRI;
#     - misturar inteligÃªncia entre municÃ­pios.
#
# CritÃ©rio de aceite:
#     python manage.py check
#     python manage.py test clima dashboard core
#
# Resultado esperado:
#     28 testes OK, sem regressÃ£o.
# ============================================================================


# REGISTRO DE AUDITORIA â€” VERSÃƒO 3.12 â€” INTEGRAÃ‡ÃƒO MP-01.6
#
# Contrato:
#     HistoricalClimateIndicatorService
#         -> historical_indicators
#         -> contexto municipal
#         -> FrostRiskService.evaluate_frost()
#         -> IntelligenceEngine (uma execuÃ§Ã£o)
#         -> rule_results
#         -> HYDRIC_PRESSURE_001
#         -> _compose_hydric_pressure_regional()
#         -> hydric_pressure_regional
#
# Garantias:
#     - HydricBalanceService continua sendo a origem do balanÃ§o.
#     - HydricPressureRule continua sendo a Ãºnica autoridade de hydric_state.
#     - Nenhum estado hÃ­drico Ã© recalculado no DashboardService.
#     - A sÃ­ntese regional consome somente rule_results jÃ¡ produzidos.
#     - MunicÃ­pios permanecem isolados durante a avaliaÃ§Ã£o.
#     - FRI, FROST_001 e METEO_ALERT_001 nÃ£o sÃ£o alterados.
#     - A coleÃ§Ã£o regional nÃ£o substitui os resultados municipais.
#
# CritÃ©rio de aceite externo:
#     python manage.py check
#     python manage.py test clima dashboard core
# ============================================================================


# ============================================================================
# REGISTRO DE AUDITORIA â€” VERSÃƒO 3.12 â€” CONTRATO CANÃ”NICO ETo
# ============================================================================
#
# Base: dashboard_service.py corrente auditado em 24/09/2026.
#
# CorreÃ§Ã£o aplicada:
#     1. WeatherDTO.eto_mm_day integra o contexto meteorolÃ³gico canÃ´nico.
#     2. A ETo regional Ã© agregada pela mesma regra estrutural dos demais
#        indicadores regionais: mÃ©dia dos seis municÃ­pios quando todos
#        possuem valor vÃ¡lido; ausÃªncia permanece None.
#     3. eto_values preserva a evidÃªncia municipal utilizada na agregaÃ§Ã£o.
#     4. map_point transporta eto_mm_day diretamente do WeatherDTO, sem
#        cÃ¡lculo, estimativa ou nova aquisiÃ§Ã£o.
#
# Responsabilidades preservadas:
#     - WeatherService continua responsÃ¡vel pela aquisiÃ§Ã£o;
#     - WeatherDTO continua sendo a origem corrente;
#     - DashboardService somente transporta e agrega o contexto canÃ´nico;
#     - KPIService serÃ¡ o consumidor seguinte do novo campo;
#     - ChartService permanece sem nova regra de aquisiÃ§Ã£o;
#     - FRI, InteligÃªncia, ranking, alertas e mapa-base permanecem preservados.
#
# Regra de ausÃªncia:
#     None permanece None quando qualquer municÃ­pio monitorado nÃ£o possui
#     ETo vÃ¡lida. Nenhum valor Ã© inventado ou substituÃ­do por zero.
# ============================================================================
