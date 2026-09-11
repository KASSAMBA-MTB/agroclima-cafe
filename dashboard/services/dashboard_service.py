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
        # KPIs
        # ======================================================

        kpis = self.kpi_service.get_kpis()

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

        context["alerts"] = []

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
        Executa a avaliaÃ§Ã£o oficial de InteligÃªncia uma Ãºnica vez por
        municÃpio e incorpora o resultado ao respectivo ``map_point``.

        Regra arquitetural da FASE 2A:

            um municÃpio
                -> uma avaliaÃ§Ã£o oficial
                -> um map_point canÃ´nico
                -> mapa / popup / ranking / alerta / insight

        Este mÃ©todo nÃ£o implementa regras de FRI. Ele apenas encaminha
        ao FrostRiskService o contexto estruturado jÃ¡ produzido por
        ``_attach_climate_data`` e distribui o resultado retornado pelo
        motor oficial nos campos canÃ´nicos do map_point.

        Nenhum consumidor posterior deve chamar novamente
        FrostRiskService para o mesmo municÃpio.
        """

        if not map_points:
            return []

        evaluated_points = []

        for point in map_points:
            evaluated = dict(point)

            context = {
                "temperature": point.get("temperature"),
                "humidity": point.get("humidity"),
                "wind_speed": point.get("wind_speed"),
                "cloud_cover": point.get("cloud_cover"),
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
                frost = self.frost_risk_service.evaluate_frost(
                    context
                )
            except Exception:
                frost = {}

            if not isinstance(frost, dict):
                frost = {}

            # --------------------------------------------------
            # CONTRATO CANÃ”NICO DO MAP_POINT
            # --------------------------------------------------
            # O valor de FRI Ã© materializado uma Ãºnica vez.
            # Nenhuma conversÃ£o, ponderaÃ§Ã£o ou novo cÃ¡lculo Ã© feito.
            evaluated["fri"] = frost.get("score")
            evaluated["severity"] = frost.get("severity")
            evaluated["confidence"] = frost.get("confidence")

            # Apenas distribui o resultado oficial retornado pela
            # camada de InteligÃªncia. NÃ£o reconstrÃ³i esses campos.
            evaluated["frost_factors"] = frost.get(
                "frost_factors"
            )

            if evaluated["frost_factors"] is None:
                evaluated["frost_factors"] = frost.get("factors")

            evaluated["insight"] = frost.get("insight")
            evaluated["recommendation"] = frost.get(
                "recommendation"
            )
            evaluated["alert"] = frost.get("alert")

            # Preserva a avaliaÃ§Ã£o oficial completa para auditoria
            # e rastreabilidade, sem criar uma segunda avaliaÃ§Ã£o.
            evaluated["frost_evaluation"] = frost

            evaluated_points.append(evaluated)

        return evaluated_points

    # ==========================================================
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
