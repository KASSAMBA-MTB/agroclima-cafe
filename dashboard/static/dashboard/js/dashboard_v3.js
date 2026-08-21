/* ==========================================================
   AGROCLIMA CAFÉ

   DASHBOARD V3
   MAP CONTROLLER — FASE 2

   Mapa Territorial Inteligente

   Responsabilidades deste arquivo:

   - Inicializar o mapa Leaflet
   - Carregar os 6 municípios monitorados
   - Carregar os limites territoriais
   - Exibir marcadores
   - Exibir popups
   - Exibir FRI, confiança e classificação
   - Controlar a camada Municípios
   - Controlar a camada Geadas
   - Exibir superfície interpolada de FRI na camada Geadas
   - Preparar as camadas futuras de Temperatura
     e Precipitação

   IMPORTANTE:

   Nenhuma regra de inteligência climática é calculada
   neste arquivo.

   Os valores de FRI, confiança e severidade são
   fornecidos pelo backend/DashboardFacade.

   ========================================================== */


const MapController = {

    /* ======================================================
       ESTADO
    ====================================================== */

    initialized: false,

    map: null,

    markers: [],

    markerLayer: null,

    territoryLayer: null,

    territoryLoaded: false,

    territoryGeoJson: null,

    friSurfaceLayer: null,

    friSurfacePoints: [],

    points: [],

    pointIndex: {},

    activeLayer: "municipios",


    /* ======================================================
       MUNICÍPIOS MONITORADOS — CÓDIGOS IBGE

       A associação territorial utiliza o código IBGE como
       chave primária.

       O nome normalizado permanece como fallback para
       compatibilidade com fontes que não retornem o código.

       Nenhum município possui tratamento visual especial.
       ====================================================== */

    monitoredMunicipalities: {

        "3500402": "Águas da Prata",

        "3102605": "Andradas",

        "3515186": "Espírito Santo do Pinhal",

        "3151800": "Poços de Caldas",

        "3549102": "São João da Boa Vista",

        "3556404": "Vargem Grande do Sul"

    },


    /* ======================================================
       FONTE TERRITORIAL

       BR_Municipios_2024

       Os seis códigos abaixo correspondem aos municípios
       monitorados pelo AgroClima Café.

       Vargem Grande do Sul = 3556404
       ====================================================== */

    territoryGeoJsonUrl:

        "https://geo.infrasa.gov.br/server/rest/services/Hosted/BR_Municipios_2024/FeatureServer/0/query" +

        "?where=cd_mun%20in%20(%273500402%27%2C%273102605%27%2C%273151800%27%2C%273515186%27%2C%273556404%27%2C%273549102%27)" +

        "&outFields=cd_mun%2Cnm_mun%2Csigla_uf" +

        "&returnGeometry=true" +

        "&outSR=4326" +

        "&f=geojson",


    /* ======================================================
       PADRÃO TERRITORIAL

       Utilizado na camada MUNICÍPIOS.

       Todos os municípios possuem exatamente o mesmo
       padrão visual.

       Não existe destaque permanente para Vargem Grande
       do Sul ou qualquer outro município.
       ====================================================== */

    territoryStyle: {

        color:
            "#6f543c",

        weight:
            1.6,

        opacity:
            0.85,

        fillColor:
            "#dfe9d5",

        fillOpacity:
            0.32

    },


    /* ======================================================
       ESTILOS DA CAMADA GEADAS
    ====================================================== */

    frostStyles: {

        normal: {

            color:
                "#287a40",

            weight:
                2.0,

            opacity:
                0.90,

            fillColor:
                "#e8f5ec",

            fillOpacity:
                0.00

        },


        attention: {

            color:
                "#9a6a00",

            weight:
                2.0,

            opacity:
                0.90,

            fillColor:
                "#fff4d6",

            fillOpacity:
                0.00

        },


        alert: {

            color:
                "#a94c17",

            weight:
                2.0,

            opacity:
                0.90,

            fillColor:
                "#fff0e5",

            fillOpacity:
                0.00

        },


        critical: {

            color:
                "#a52f2f",

            weight:
                2.2,

            opacity:
                0.95,

            fillColor:
                "#fde7e7",

            fillOpacity:
                0.00

        },


        none: {

            color:
                "#777777",

            weight:
                1.6,

            opacity:
                0.80,

            fillColor:
                "#f0f0f0",

            fillOpacity:
                0.00

        }

    },


    /* ======================================================
       ESTILOS DAS CAMADAS CLIMÁTICAS

       Os limites são usados apenas para representação
       operacional dos dados atuais recebidos pelo backend.
       Nenhuma inteligência agroclimática é criada aqui.
    ====================================================== */

    temperatureStyles: {

        veryCold: { color: "#355c7d", weight: 2.0, opacity: 0.90, fillColor: "#355c7d", fillOpacity: 0.25 },
        cold: { color: "#4f86a8", weight: 2.0, opacity: 0.90, fillColor: "#4f86a8", fillOpacity: 0.25 },
        favorable: { color: "#287a40", weight: 2.0, opacity: 0.90, fillColor: "#287a40", fillOpacity: 0.25 },
        warm: { color: "#9a6a00", weight: 2.0, opacity: 0.90, fillColor: "#9a6a00", fillOpacity: 0.25 },
        hot: { color: "#a94c17", weight: 2.0, opacity: 0.90, fillColor: "#a94c17", fillOpacity: 0.25 },
        unavailable: { color: "#777777", weight: 1.6, opacity: 0.80, fillColor: "#f0f0f0", fillOpacity: 0.35 }

    },


    precipitationStyles: {

        none: { color: "#777777", weight: 1.6, opacity: 0.80, fillColor: "#f0f0f0", fillOpacity: 0.35 },
        low: { color: "#4f86a8", weight: 2.0, opacity: 0.90, fillColor: "#4f86a8", fillOpacity: 0.25 },
        moderate: { color: "#287a40", weight: 2.0, opacity: 0.90, fillColor: "#287a40", fillOpacity: 0.25 },
        high: { color: "#9a6a00", weight: 2.0, opacity: 0.90, fillColor: "#9a6a00", fillOpacity: 0.25 },
        veryHigh: { color: "#a94c17", weight: 2.0, opacity: 0.90, fillColor: "#a94c17", fillOpacity: 0.25 },
        extreme: { color: "#a52f2f", weight: 2.2, opacity: 0.95, fillColor: "#a52f2f", fillOpacity: 0.25 }

    },


    /* ======================================================
       INICIALIZAÇÃO
    ====================================================== */

    init() {

        const container =
            document.getElementById(
                "map-container"
            );


        if (!container) {

            console.error(
                "[AGROCLIMA] Container #map-container não encontrado."
            );

            return;

        }


        if (
            typeof L ===
            "undefined"
        ) {

            console.error(
                "[AGROCLIMA] Leaflet não está disponível."
            );

            return;

        }


        if (
            this.initialized
        ) {

            return;

        }


        this.map =
            L.map(
                "map-container",
                {
                    zoomControl:
                        true
                }
            );


        /* ==================================================
           PAINEL TERRITORIAL
        ================================================== */

        this.map.createPane(
            "territoryPane"
        );


        this.map.getPane(
            "territoryPane"
        ).style.zIndex =
            470;


        /* ==================================================
           SUPERFÍCIE FRI
        ================================================== */

        this.map.createPane(
            "friSurfacePane"
        );

        this.map.getPane(
            "friSurfacePane"
        ).style.zIndex =
            460;


        /* ==================================================
           OPEN STREET MAP
        ================================================== */

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {

                maxZoom:
                    19,

                attribution:
                    "&copy; OpenStreetMap"

            }
        ).addTo(
            this.map
        );


        /* ==================================================
           CAMADA DE MARCADORES
        ================================================== */

        this.markerLayer =
            L.layerGroup()
                .addTo(
                    this.map
                );


        this.createFRISurfaceLayer();


        this.initialized =
            true;


        this.bindLayerButtons();
        this.updateLegend();


        this.loadPoints();


        this.loadTerritory();


        setTimeout(
            () => {

                if (
                    this.map
                ) {

                    this.map.invalidateSize();

                }

            },
            300
        );

    },


    /* ======================================================
       CARREGAR PONTOS DO DJANGO
    ====================================================== */

    loadPoints() {

        const element =
            document.getElementById(
                "agroclima-map-points"
            );


        if (!element) {

            console.error(
                "[AGROCLIMA] Elemento agroclima-map-points não encontrado."
            );

            this.hideLoading();

            return;

        }


        let points;


        try {

            points =
                JSON.parse(
                    element.textContent
                );

        } catch (error) {

            console.error(
                "[AGROCLIMA] Erro ao interpretar map_points:",
                error
            );

            this.hideLoading();

            return;

        }


        if (
            !Array.isArray(
                points
            )
        ) {

            console.error(
                "[AGROCLIMA] map_points não é uma lista."
            );

            this.hideLoading();

            return;

        }


        this.points =
            points;


        console.info(
            "[AGROCLIMA] Total de municípios recebidos:",
            this.points.length
        );


        console.info(
            "[AGROCLIMA] Municípios carregados:",
            this.points.map(
                point =>
                    point.nome
            )
        );


        this.buildPointIndex();


        this.updateMarkers(
            this.points
        );


        this.hideLoading();

    },


    /* ======================================================
       ÍNDICE DOS MUNICÍPIOS
    ====================================================== */

    buildPointIndex() {

        this.pointIndex =
            {};


        this.points.forEach(
            point => {

                const key =
                    this.normalizeName(
                        point.nome
                    );


                if (
                    key
                ) {

                    this.pointIndex[
                        key
                    ] =
                        point;

                }

            }
        );

    },


    /* ======================================================
       CARREGAR TERRITÓRIO
    ====================================================== */

    async loadTerritory() {

        if (
            !this.map
        ) {

            return;

        }


        try {

            console.info(
                "[AGROCLIMA] Consultando fonte territorial..."
            );


            const response =
                await fetch(
                    this.territoryGeoJsonUrl,
                    {

                        method:
                            "GET",

                        headers: {

                            Accept:
                                "application/geo+json, application/json"

                        }

                    }
                );


            if (
                !response.ok
            ) {

                throw new Error(
                    `HTTP ${response.status}`
                );

            }


            const geojson =
                await response.json();


            if (
                !geojson ||
                !Array.isArray(
                    geojson.features
                )
            ) {

                throw new Error(
                    "GeoJSON territorial inválido."
                );

            }


            this.territoryGeoJson = {

                type:
                    "FeatureCollection",

                features:
                    geojson.features
            };


            /* ==================================================
               DIAGNÓSTICO DA FONTE
            ================================================== */

            console.info(
                "[AGROCLIMA] Total de polígonos recebidos:",
                geojson.features.length
            );


            const municipalities =
                geojson.features.map(
                    feature => {

                        const properties =
                            feature.properties ||
                            {};


                        return {

                            code:
                                properties.cd_mun ||
                                properties.CD_MUN ||
                                null,

                            name:
                                properties.nm_mun ||
                                properties.NM_MUN ||
                                "",

                            uf:
                                properties.sigla_uf ||
                                properties.SIGLA_UF ||
                                ""

                        };

                    }
                );


            console.info(
                "[AGROCLIMA] Municípios territoriais recebidos:",
                municipalities
            );


            /* ==================================================
               VALIDAR OS SEIS MUNICÍPIOS MONITORADOS
            ================================================== */

            const monitoredCodes =
                Object.keys(
                    this.monitoredMunicipalities
                );


            const monitoredFeatures =
                geojson.features.filter(
                    feature => {

                        const code =
                            this.getTerritoryCode(
                                feature
                            );


                        return monitoredCodes.includes(
                            code
                        );

                    }
                );


            const loadedCodes =
                monitoredFeatures.map(
                    feature =>
                        this.getTerritoryCode(
                            feature
                        )
                );


            const missingMunicipalities =
                monitoredCodes
                    .filter(
                        code =>
                            !loadedCodes.includes(
                                code
                            )
                    )
                    .map(
                        code =>
                            `${this.monitoredMunicipalities[code]} (${code})`
                    );


            console.info(
                "[AGROCLIMA] Polígonos dos municípios monitorados:",
                monitoredFeatures.length
            );


            console.info(
                "[AGROCLIMA] Municípios monitorados encontrados:",
                monitoredFeatures.map(
                    feature =>
                        `${this.getTerritoryName(feature)} (${this.getTerritoryCode(feature)})`
                )
            );


            if (
                missingMunicipalities.length
            ) {

                console.error(
                    "[AGROCLIMA] Municípios monitorados sem polígono:",
                    missingMunicipalities
                );

            } else {

                console.info(
                    "[AGROCLIMA] VALIDAÇÃO TERRITORIAL: 6/6 municípios encontrados."
                );

            }


            /* ==================================================
               VALIDAÇÃO ESPECÍFICA DE VARGEM GRANDE DO SUL
            ================================================== */

            const vargem =
                monitoredFeatures.find(
                    feature =>
                        this.getTerritoryCode(
                            feature
                        ) ===
                        "3556404"
                );


            if (
                vargem
            ) {

                console.info(
                    "[AGROCLIMA] Vargem Grande do Sul encontrada no GeoJSON: 3556404."
                );

            } else {

                console.error(
                    "[AGROCLIMA] ERRO TERRITORIAL: Vargem Grande do Sul (3556404) não foi retornada pela fonte."
                );

            }


            /* ==================================================
               CRIAR CAMADA TERRITORIAL

               Somente os seis municípios monitorados são
               adicionados ao mapa.

               Isso impede que um município externo, como
               Santo Antônio do Jardim, seja desenhado caso
               a fonte retorne alguma feição adicional.
            ================================================== */

            const monitoredGeoJson = {

                type:
                    "FeatureCollection",

                features:
                    monitoredFeatures

            };


            this.territoryLayer =
                L.geoJSON(
                    monitoredGeoJson,
                    {

                        pane:
                            "territoryPane",

                        style:
                            feature =>
                                this.getTerritoryStyle(
                                    feature
                                ),

                        onEachFeature:
                            (
                                feature,
                                layer
                            ) => {

                                this.bindTerritoryFeature(
                                    feature,
                                    layer
                                );

                            }

                    }
                );


            this.territoryLayer.addTo(
                this.map
            );


            this.territoryLoaded =
                true;


            this.updateTerritoryStyle();
            this.refreshFRISurface();


            /* ==================================================
               ENQUADRAMENTO AUTOMÁTICO
            ================================================== */

            const bounds =
                this.territoryLayer
                    .getBounds();


            if (
                bounds.isValid()
            ) {

                this.map.fitBounds(
                    bounds,
                    {

                        padding:
                            [
                                30,
                                30
                            ],

                        maxZoom:
                            10

                    }
                );

            }


        } catch (error) {

            console.error(
                "[AGROCLIMA] Erro ao carregar território municipal:",
                error
            );

        }

    },


    /* ======================================================
       IDENTIFICAÇÃO TERRITORIAL
    ====================================================== */

    getTerritoryProperties(
        feature
    ) {

        if (
            !feature ||
            !feature.properties
        ) {

            return {};

        }


        return feature.properties;

    },


    getTerritoryCode(
        feature
    ) {

        const properties =
            this.getTerritoryProperties(
                feature
            );


        const code =
            properties.cd_mun ??
            properties.CD_MUN ??
            properties.cod_mun ??
            properties.COD_MUN ??
            null;


        if (
            code === null ||
            code === undefined ||
            code === ""
        ) {

            return "";

        }


        return String(
            code
        )
            .trim()
            .padStart(
                7,
                "0"
            );

    },


    getTerritoryName(
        feature
    ) {

        const properties =
            this.getTerritoryProperties(
                feature
            );


        return String(
            properties.nm_mun ??
            properties.NM_MUN ??
            ""
        ).trim();

    },


    getTerritoryUf(
        feature
    ) {

        const properties =
            this.getTerritoryProperties(
                feature
            );


        return String(
            properties.sigla_uf ??
            properties.SIGLA_UF ??
            ""
        ).trim();

    },


    getPointForTerritoryFeature(
        feature
    ) {

        const code =
            this.getTerritoryCode(
                feature
            );


        if (
            code
        ) {

            const point =
                this.points.find(
                    item => {

                        const itemCode =
                            item.codigo_ibge ??
                            item.codigo_ibge_municipio ??
                            item.cod_mun ??
                            item.codigo_municipio ??
                            null;


                        return (
                            itemCode !== null &&
                            itemCode !== undefined &&
                            String(
                                itemCode
                            )
                                .trim()
                                .padStart(
                                    7,
                                    "0"
                                ) ===
                            code
                        );

                    }
                );


            if (
                point
            ) {

                return point;

            }

        }


        /*
         * Fallback por nome normalizado.
         */

        return this.pointIndex[
            this.normalizeName(
                this.getTerritoryName(
                    feature
                )
            )
        ] || null;

    },


    /* ======================================================
       CLASSIFICAÇÃO OPERACIONAL DE TEMPERATURA
    ====================================================== */

    getTemperatureClass(value) {

        const temperature = Number(value);

        if (!Number.isFinite(temperature)) {
            return "unavailable";
        }

        if (temperature <= 1) {
            return "veryCold";
        }

        if (temperature < 12) {
            return "cold";
        }

        if (temperature < 18) {
            return "cold";
        }

        if (temperature <= 22) {
            return "favorable";
        }

        if (temperature <= 28) {
            return "warm";
        }

        return "hot";

    },


    getTemperatureLabel(value) {

        const labels = {
            veryCold: "Muito fria",
            cold: "Fria",
            favorable: "Faixa favorável",
            warm: "Quente",
            hot: "Muito quente",
            unavailable: "Sem dado"
        };

        return labels[this.getTemperatureClass(value)] || labels.unavailable;

    },


    /* ======================================================
       CLASSIFICAÇÃO OPERACIONAL DE PRECIPITAÇÃO 24H
    ====================================================== */

    getPrecipitationClass(value) {

        const precipitation = Number(value);

        if (!Number.isFinite(precipitation)) {
            return "none";
        }

        if (precipitation <= 0) {
            return "none";
        }

        if (precipitation <= 5) {
            return "low";
        }

        if (precipitation <= 20) {
            return "moderate";
        }

        if (precipitation <= 50) {
            return "high";
        }

        if (precipitation <= 80) {
            return "veryHigh";
        }

        return "extreme";

    },


    getPrecipitationLabel(value) {

        const labels = {
            none: "Sem chuva",
            low: "Chuva baixa",
            moderate: "Chuva moderada",
            high: "Chuva alta",
            veryHigh: "Chuva muito alta",
            extreme: "Chuva extrema"
        };

        return labels[this.getPrecipitationClass(value)] || "Sem dado";

    },


    /* ======================================================
       ESTILO TERRITORIAL
    ====================================================== */

    getTerritoryStyle(
        feature
    ) {

        const point =
            this.getPointForTerritoryFeature(
                feature
            );


        /* ==================================================
           CAMADA GEADAS
        ================================================== */

        if (
            this.activeLayer ===
            "geadas"
        ) {

            const severity =
                point
                    ? this.normalizeSeverity(
                        point.severity
                    )
                    : "none";


            const baseStyle =
                this.frostStyles[
                    severity
                ] ||
                this.frostStyles.none;


            /* ==================================================
               FASE 1 — SUPERFÍCIE FRI

               Os polígonos municipais permanecem apenas como
               limites territoriais. O preenchimento da camada
               Geadas é removido para que a superfície FRI
               interpolada fique visualmente exposta.

               Os dados FRI/severity permanecem inalterados.
            ================================================== */

            return {

                ...baseStyle,

                fillOpacity:
                    0

            };

        }


        /* ==================================================
           CAMADA TEMPERATURA
        ================================================== */

        if (
            this.activeLayer ===
            "temperatura"
        ) {

            const classification =
                this.getTemperatureClass(
                    point && point.temperature
                );

            return (
                this.temperatureStyles[
                    classification
                ] ||
                this.temperatureStyles.unavailable
            );

        }


        /* ==================================================
           CAMADA PRECIPITAÇÃO
        ================================================== */

        if (
            this.activeLayer ===
            "precipitacao"
        ) {

            const classification =
                this.getPrecipitationClass(
                    point && point.precipitation
                );

            return (
                this.precipitationStyles[
                    classification
                ] ||
                this.precipitationStyles.none
            );

        }


        /* ==================================================
           CAMADA MUNICÍPIOS

           PADRÃO ÚNICO PARA TODOS.

           Vargem Grande do Sul NÃO possui tratamento
           especial.
        ================================================== */

        return {

            color:
                this.territoryStyle.color,

            weight:
                this.territoryStyle.weight,

            opacity:
                this.territoryStyle.opacity,

            fillColor:
                this.territoryStyle.fillColor,

            fillOpacity:
                this.territoryStyle.fillOpacity

        };

    },


    /* ======================================================
       INTERAÇÃO COM POLÍGONO
    ====================================================== */

    bindTerritoryFeature(
        feature,
        layer
    ) {

        const name =
            this.getTerritoryName(
                feature
            ) ||
            "Município";


        const uf =
            this.getTerritoryUf(
                feature
            );


        const point =
            this.getPointForTerritoryFeature(
                feature
            );


        layer.bindPopup(
            this.buildTerritoryPopup(
                name,
                uf,
                point
            )
        );


        layer.on({

            mouseover:
                event => {

                    const target =
                        event.target;


                    target.setStyle({

                        weight:
                            2.5,

                        color:
                            "#4f3019",

                        fillOpacity:
                            this.activeLayer ===
                            "geadas"
                                ? 0.03
                                : 0.55

                    });


                    if (
                        !L.Browser.ie &&
                        !L.Browser.opera &&
                        !L.Browser.edge
                    ) {

                        target.bringToFront();

                    }

                },


            mouseout:
                event => {

                    if (
                        this.territoryLayer
                    ) {

                        this.territoryLayer
                            .resetStyle(
                                event.target
                            );


                        this.updateTerritoryStyle();

                    }

                }

        });

    },


    /* ======================================================
       POPUP TERRITORIAL
    ====================================================== */

    buildTerritoryPopup(
        name,
        uf,
        point
    ) {

        const municipio =
            this.escapeHtml(
                name
            );


        const estado =
            this.escapeHtml(
                uf
            );


        if (
            !point
        ) {

            return `
                <div class="agroclima-popup">

                    <div class="agroclima-popup-title">
                        ${municipio}
                    </div>

                    <div class="agroclima-popup-location">
                        ${estado}
                    </div>

                    <div class="agroclima-popup-item">

                        <span class="agroclima-popup-label">
                            Monitoramento
                        </span>

                        <span class="agroclima-popup-value">
                            Município não monitorado
                        </span>

                    </div>

                </div>
            `;

        }


        return this.buildPopup(
            point
        );

    },


    /* ======================================================
       ATUALIZAR ESTILO TERRITORIAL
    ====================================================== */

    updateTerritoryStyle() {

        if (
            !this.territoryLayer
        ) {

            return;

        }


        this.territoryLayer.setStyle(
            feature =>
                this.getTerritoryStyle(
                    feature
                )
        );

    },


    /* ======================================================
       ATUALIZAR POPUPS CONFORME A CAMADA ATIVA
    ====================================================== */

    refreshMapPopups() {

        if (
            this.markerLayer
        ) {

            this.markerLayer.eachLayer(
                marker => {

                    if (
                        marker.__agroclimaPoint
                    ) {

                        marker.setPopupContent(
                            this.buildPopup(
                                marker.__agroclimaPoint
                            )
                        );

                    }

                }
            );

        }


        if (
            this.territoryLayer
        ) {

            this.territoryLayer.eachLayer(
                layer => {

                    const feature =
                        layer.feature;

                    const point =
                        this.getPointForTerritoryFeature(
                            feature
                        );

                    const name =
                        this.getTerritoryName(
                            feature
                        ) || "Município";

                    const uf =
                        this.getTerritoryUf(
                            feature
                        );

                    layer.setPopupContent(
                        this.buildTerritoryPopup(
                            name,
                            uf,
                            point
                        )
                    );

                }
            );

        }

    },


    /* ======================================================
       LEGENDA DINÂMICA DO MAPA
    ====================================================== */

    updateLegend() {

        const container =
            document.querySelector(
                ".map-legend .legend-items"
            );

        if (!container) {
            return;
        }

        const legends = {

            municipios: [
                ["#287a40", "Município monitorado"]
            ],

            geadas: [
                ["#287a40", "Baixo"],
                ["#9a6a00", "Moderado"],
                ["#a94c17", "Alto"],
                ["#a52f2f", "Crítico"],
                ["#777777", "Sem risco"]
            ],

            fri: [
                ["#355c7d", "FRI 0–20"],
                ["#4f86a8", "FRI 20–40"],
                ["#287a40", "FRI 40–60"],
                ["#9a6a00", "FRI 60–80"],
                ["#a52f2f", "FRI 80–100"]
            ],

            temperatura: [
                ["#355c7d", "Muito fria"],
                ["#4f86a8", "Fria"],
                ["#287a40", "Faixa favorável"],
                ["#9a6a00", "Quente"],
                ["#a94c17", "Muito quente"]
            ],

            precipitacao: [
                ["#777777", "Sem chuva"],
                ["#4f86a8", "Baixa"],
                ["#287a40", "Moderada"],
                ["#9a6a00", "Alta"],
                ["#a94c17", "Muito alta"],
                ["#a52f2f", "Extrema"]
            ]

        };

        const items =
            legends[this.activeLayer] ||
            legends.municipios;


        if (
            this.activeLayer === "geadas"
        ) {

            const friItems =
                legends.fri;

            container.innerHTML = `
                <span
                    class="legend-group-label"
                    style="display:block;width:100%;margin-bottom:4px;font-weight:600;"
                >
                    Superfície de risco — FRI
                </span>

                ${friItems
                    .map(
                        ([color, label]) => `
                            <span class="legend-item">
                                <i class="legend-dot" style="background:${color};"></i>
                                ${label}
                            </span>
                        `
                    )
                    .join("")}

                <span
                    class="legend-group-label"
                    style="display:block;width:100%;margin:6px 0 4px;font-weight:600;"
                >
                    Marcadores — severidade
                </span>

                ${items
                    .map(
                        ([color, label]) => `
                            <span class="legend-item">
                                <i class="legend-dot" style="background:${color};"></i>
                                ${label}
                            </span>
                        `
                    )
                    .join("")}
            `;

            return;

        }


        container.innerHTML =
            items
                .map(
                    ([color, label]) => `
                        <span class="legend-item">
                            <i class="legend-dot" style="background:${color};"></i>
                            ${label}
                        </span>
                    `
                )
                .join("");

    },


    /* ======================================================
       OCULTAR LOADING
    ====================================================== */

    hideLoading() {

        const loading =
            document.querySelector(
                "#map-container .map-loading"
            );


        if (
            !loading
        ) {

            return;

        }


        loading.style.display =
            "none";

    },


    /* ======================================================
       ATUALIZAR MARCADORES
    ====================================================== */

    updateMarkers(
        points = []
    ) {

        if (
            !this.initialized ||
            !this.markerLayer
        ) {

            return;

        }


        this.markerLayer.clearLayers();


        this.markers = [];


        if (
            !points.length
        ) {

            console.warn(
                "[AGROCLIMA] Nenhum município disponível para o mapa."
            );

            this.friSurfacePoints = [];
            this.hideFRISurface();

            return;

        }


        const bounds = [];


        points.forEach(
            point => {

                if (
                    point.latitude ===
                        null ||
                    point.latitude ===
                        undefined ||
                    point.longitude ===
                        null ||
                    point.longitude ===
                        undefined
                ) {

                    console.warn(
                        "[AGROCLIMA] Município sem coordenadas:",
                        point.nome
                    );

                    return;

                }


                const latitude =
                    Number(
                        point.latitude
                    );


                const longitude =
                    Number(
                        point.longitude
                    );


                if (
                    !Number.isFinite(
                        latitude
                    ) ||
                    !Number.isFinite(
                        longitude
                    )
                ) {

                    console.warn(
                        "[AGROCLIMA] Coordenadas inválidas:",
                        point.nome
                    );

                    return;

                }


                const icon =
                    this.createMarkerIcon(
                        point
                    );


                const marker =
                    L.marker(
                        [
                            latitude,
                            longitude
                        ],
                        {

                            icon:
                                icon,

                            title:
                                point.nome ||
                                "Município"

                        }
                    );


                marker.__agroclimaPoint = point;

                marker.bindPopup(
                    this.buildPopup(
                        point
                    )
                );


                marker.addTo(
                    this.markerLayer
                );


                this.markers.push(
                    marker
                );


                bounds.push(
                    [
                        latitude,
                        longitude
                    ]
                );

            }
        );


        this.refreshFRISurface();


        if (
            !this.territoryLoaded
        ) {

            if (
                bounds.length === 1
            ) {

                this.map.setView(
                    bounds[0],
                    10
                );

            } else if (
                bounds.length > 1
            ) {

                this.map.fitBounds(
                    bounds,
                    {

                        padding:
                            [
                                30,
                                30
                            ],

                        maxZoom:
                            10

                    }
                );

            }

        }

    },


    /* ======================================================
       SUPERFÍCIE DE RISCO FRI — GEADAS

       A superfície utiliza exclusivamente os valores FRI
       recebidos do backend e as coordenadas reais dos
       municípios monitorados.

       Não há geração de valores climáticos fictícios.
       A interpolação é uma representação espacial estimada
       entre os pontos reais por ponderação IDW.

       A máscara territorial utilizada é o GeoJSON municipal
       carregado pelo próprio MapController. Caso a fonte
       territorial seja alterada para uma geometria específica
       da Mantiqueira Vulcânica, a mesma máscara será utilizada
       sem alterar a lógica de interpolação.
    ====================================================== */

    createFRISurfaceLayer() {

        if (
            this.friSurfaceLayer ||
            typeof L === "undefined"
        ) {

            return;

        }


        const controller =
            this;


        const FRISurfaceLayer =
            L.Layer.extend({

                onAdd(map) {

                    this._map =
                        map;

                    this._canvas =
                        L.DomUtil.create(
                            "canvas",
                            "agroclima-fri-surface"
                        );

                    this._canvas.style.position =
                        "absolute";

                    this._canvas.style.pointerEvents =
                        "none";

                    this._canvas.style.display =
                        "block";

                    this._canvas.style.zIndex =
                        "0";

                    map.getPane(
                        "friSurfacePane"
                    ).appendChild(
                        this._canvas
                    );

                    map.on(
                        "moveend zoomend resize",
                        this._redraw,
                        this
                    );

                    this._redraw();

                },


                onRemove(map) {

                    map.off(
                        "moveend zoomend resize",
                        this._redraw,
                        this
                    );

                    if (
                        this._canvas &&
                        this._canvas.parentNode
                    ) {

                        this._canvas.parentNode.removeChild(
                            this._canvas
                        );

                    }

                    this._canvas =
                        null;

                    this._map =
                        null;

                },


                _redraw() {

                    if (
                        this._map &&
                        this._canvas
                    ) {

                        controller.drawFRISurface(
                            this._canvas
                        );

                    }

                }

            });


        this.friSurfaceLayer =
            new FRISurfaceLayer();

    },


    refreshFRISurface() {

        if (
            this.activeLayer !== "geadas"
        ) {

            this.hideFRISurface();
            return;

        }


        if (
            !this.map ||
            !this.territoryLoaded ||
            !this.territoryGeoJson
        ) {

            return;

        }


        const validPoints =
            this.points
                .map(point => ({
                    point,
                    latitude: Number(point.latitude),
                    longitude: Number(point.longitude),
                    fri: Number(point.fri)
                }))
                .filter(item =>
                    Number.isFinite(item.latitude) &&
                    Number.isFinite(item.longitude) &&
                    Number.isFinite(item.fri)
                );


        this.friSurfacePoints =
            validPoints;


        if (
            validPoints.length < 2
        ) {

            console.warn(
                "[AGROCLIMA] Superfície FRI não criada: são necessários pelo menos 2 pontos FRI válidos."
            );

            this.hideFRISurface();
            return;

        }


        if (
            !this.friSurfaceLayer
        ) {

            this.createFRISurfaceLayer();

        }


        if (
            !this.map.hasLayer(
                this.friSurfaceLayer
            )
        ) {

            this.friSurfaceLayer.addTo(
                this.map
            );

        }


        this.friSurfaceLayer._redraw();

    },


    hideFRISurface() {

        if (
            this.map &&
            this.friSurfaceLayer &&
            this.map.hasLayer(
                this.friSurfaceLayer
            )
        ) {

            this.map.removeLayer(
                this.friSurfaceLayer
            );

        }

    },


    drawFRISurface(canvas) {

        /*
         * ==========================================================
         * FASE 1 — CORREÇÃO DEFINITIVA DA SUPERFÍCIE FRI
         *
         * DIAGNÓSTICO:
         *
         * A implementação anterior interpolava o FRI em escala de
         * cinza, convertia imediatamente para RGB, aplicava blur
         * sobre a imagem colorida e somente depois recortava pela
         * máscara territorial.
         *
         * Em Canvas, esse processo mistura as cores já convertidas
         * com pixels transparentes/pretos das bordas. O resultado
         * pode produzir uma massa escura/cinza e não uma superfície
         * cromática contínua coerente com a escala FRI.
         *
         * ESTRUTURA CORRIGIDA:
         *
         *     FRI REAL
         *        ↓
         *     IDW
         *        ↓
         *     CAMPO ESCALAR FRI 0–100
         *        ↓
         *     SUPERSAMPLING
         *        ↓
         *     SUAVIZAÇÃO DO VALOR FRI
         *        ↓
         *     MÁSCARA TERRITORIAL
         *        ↓
         *     GRADIENTE FRI
         *        ↓
         *     OPACIDADE
         *        ↓
         *     CANVAS
         *
         * A cor somente é criada depois que a superfície já está
         * interpolada, suavizada e mascarada.
         *
         * NENHUM valor de this.friSurfacePoints é alterado.
         * NENHUM valor de point.fri é recalculado.
         * NENHUMA regra do backend é criada neste bloco.
         * ==========================================================
         */

        if (
            !this.map ||
            !canvas ||
            this.activeLayer !== "geadas" ||
            !this.territoryGeoJson ||
            !Array.isArray(
                this.territoryGeoJson.features
            ) ||
            !Array.isArray(
                this.friSurfacePoints
            ) ||
            !this.friSurfacePoints.length
        ) {

            if (canvas) {

                const context =
                    canvas.getContext(
                        "2d"
                    );

                if (context) {

                    context.clearRect(
                        0,
                        0,
                        canvas.width || 0,
                        canvas.height || 0
                    );

                }

            }

            return;

        }


        /* ==========================================================
           DIMENSÕES DO MAPA
        ========================================================== */

        const size =
            this.map.getSize();


        const origin =
            this.map.containerPointToLayerPoint(
                [0, 0]
            );


        const width =
            Math.max(
                1,
                Math.ceil(
                    size.x
                )
            );


        const height =
            Math.max(
                1,
                Math.ceil(
                    size.y
                )
            );


        const dpr =
            Math.min(
                window.devicePixelRatio || 1,
                2
            );


        canvas.width =
            Math.ceil(
                width * dpr
            );


        canvas.height =
            Math.ceil(
                height * dpr
            );


        canvas.style.width =
            `${width}px`;


        canvas.style.height =
            `${height}px`;


        L.DomUtil.setPosition(
            canvas,
            origin
        );


        const context =
            canvas.getContext(
                "2d"
            );


        if (!context) {

            return;

        }


        context.setTransform(
            dpr,
            0,
            0,
            dpr,
            0,
            0
        );


        context.clearRect(
            0,
            0,
            width,
            height
        );


        /* ==========================================================
           EXTENSÃO TERRITORIAL

           A região de cálculo é determinada exclusivamente pelas
           geometrias territoriais monitoradas.
        ========================================================== */

        let minX =
            width;


        let minY =
            height;


        let maxX =
            0;


        let maxY =
            0;


        let hasTerritory =
            false;


        const appendRingToBounds =
            ring => {

                if (
                    !Array.isArray(
                        ring
                    )
                ) {

                    return;

                }


                ring.forEach(
                    coordinate => {

                        if (
                            !Array.isArray(
                                coordinate
                            ) ||
                            coordinate.length < 2
                        ) {

                            return;

                        }


                        const lng =
                            Number(
                                coordinate[0]
                            );


                        const lat =
                            Number(
                                coordinate[1]
                            );


                        if (
                            !Number.isFinite(
                                lng
                            ) ||
                            !Number.isFinite(
                                lat
                            )
                        ) {

                            return;

                        }


                        const point =
                            this.map.latLngToContainerPoint(
                                [
                                    lat,
                                    lng
                                ]
                            );


                        minX =
                            Math.min(
                                minX,
                                point.x
                            );


                        minY =
                            Math.min(
                                minY,
                                point.y
                            );


                        maxX =
                            Math.max(
                                maxX,
                                point.x
                            );


                        maxY =
                            Math.max(
                                maxY,
                                point.y
                            );


                        hasTerritory =
                            true;

                    }
                );

            };


        this.territoryGeoJson.features.forEach(
            feature => {

                const geometry =
                    feature &&
                    feature.geometry;


                if (!geometry) {

                    return;

                }


                if (
                    geometry.type ===
                    "Polygon"
                ) {

                    geometry.coordinates.forEach(
                        appendRingToBounds
                    );

                } else if (
                    geometry.type ===
                    "MultiPolygon"
                ) {

                    geometry.coordinates.forEach(
                        polygon =>
                            polygon.forEach(
                                appendRingToBounds
                            )
                    );

                }

            }
        );


        if (!hasTerritory) {

            return;

        }


        /*
         * A margem existe apenas para que a interpolação possa
         * chegar suavemente à borda antes do recorte final.
         */
        const margin =
            30;


        minX =
            Math.max(
                0,
                Math.floor(
                    minX
                ) - margin
            );


        minY =
            Math.max(
                0,
                Math.floor(
                    minY
                ) - margin
            );


        maxX =
            Math.min(
                width,
                Math.ceil(
                    maxX
                ) + margin
            );


        maxY =
            Math.min(
                height,
                Math.ceil(
                    maxY
                ) + margin
            );


        const regionWidth =
            Math.max(
                1,
                maxX - minX
            );


        const regionHeight =
            Math.max(
                1,
                maxY - minY
            );


        /* ==========================================================
           CAMPO ESCALAR FRI — IDW

           A grade é uma estrutura matemática intermediária.
           Nenhuma célula é enviada diretamente para o mapa.
        ========================================================== */

        const sampleStep =
            3;


        const sampleWidth =
            Math.max(
                2,
                Math.ceil(
                    regionWidth /
                    sampleStep
                )
            );


        const sampleHeight =
            Math.max(
                2,
                Math.ceil(
                    regionHeight /
                    sampleStep
                )
            );


        const scalarCanvas =
            document.createElement(
                "canvas"
            );


        scalarCanvas.width =
            sampleWidth;


        scalarCanvas.height =
            sampleHeight;


        const scalarContext =
            scalarCanvas.getContext(
                "2d",
                {
                    willReadFrequently:
                        true
                }
            );


        if (!scalarContext) {

            return;

        }


        const scalarImage =
            scalarContext.createImageData(
                sampleWidth,
                sampleHeight
            );


        const scalarData =
            scalarImage.data;


        const points =
            this.friSurfacePoints;


        const power =
            2;


        for (
            let sy = 0;
            sy < sampleHeight;
            sy += 1
        ) {

            for (
                let sx = 0;
                sx < sampleWidth;
                sx += 1
            ) {

                const x =
                    minX +
                    (
                        sx + 0.5
                    ) *
                    sampleStep;


                const y =
                    minY +
                    (
                        sy + 0.5
                    ) *
                    sampleStep;


                const latLng =
                    this.map.containerPointToLatLng(
                        [
                            x,
                            y
                        ]
                    );


                let weightedSum =
                    0;


                let weightTotal =
                    0;


                let exactValue =
                    null;


                points.forEach(
                    item => {

                        const fri =
                            Number(
                                item.fri
                            );


                        if (
                            !Number.isFinite(
                                fri
                            )
                        ) {

                            return;

                        }


                        const dx =
                            latLng.lng -
                            Number(
                                item.longitude
                            );


                        const dy =
                            latLng.lat -
                            Number(
                                item.latitude
                            );


                        const distanceSquared =
                            (
                                dx * dx
                            ) +
                            (
                                dy * dy
                            );


                        if (
                            distanceSquared <
                            0.000000000001
                        ) {

                            exactValue =
                                Math.max(
                                    0,
                                    Math.min(
                                        100,
                                        fri
                                    )
                                );

                            return;

                        }


                        const distance =
                            Math.sqrt(
                                distanceSquared
                            );


                        const weight =
                            1 /
                            Math.pow(
                                distance,
                                power
                            );


                        weightedSum +=
                            fri *
                            weight;


                        weightTotal +=
                            weight;

                    }
                );


                let value =
                    exactValue !== null
                        ? exactValue
                        : weightTotal > 0
                            ? (
                                weightedSum /
                                weightTotal
                            )
                            : 0;


                value =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            value
                        )
                    );


                const index =
                    (
                        sy *
                        sampleWidth +
                        sx
                    ) *
                    4;


                /*
                 * Escala monocromática:
                 *
                 *     0   = preto
                 *     255 = branco
                 *
                 * Esta imagem ainda não representa a cor final.
                 */
                const intensity =
                    Math.round(
                        (
                            value /
                            100
                        ) *
                        255
                    );


                scalarData[index] =
                    intensity;


                scalarData[index + 1] =
                    intensity;


                scalarData[index + 2] =
                    intensity;


                scalarData[index + 3] =
                    255;

            }

        }


        scalarContext.putImageData(
            scalarImage,
            0,
            0
        );


        /* ==========================================================
           SUPERSAMPLING

           Amplia a grade para a resolução do território sem
           desenhar retângulos. A interpolação de imagem ocorre
           enquanto o pixel ainda representa apenas FRI.
        ========================================================== */

        const fieldCanvas =
            document.createElement(
                "canvas"
            );


        fieldCanvas.width =
            regionWidth;


        fieldCanvas.height =
            regionHeight;


        const fieldContext =
            fieldCanvas.getContext(
                "2d",
                {
                    willReadFrequently:
                        true
                }
            );


        if (!fieldContext) {

            return;

        }


        fieldContext.imageSmoothingEnabled =
            true;


        fieldContext.imageSmoothingQuality =
            "high";


        fieldContext.drawImage(
            scalarCanvas,
            0,
            0,
            sampleWidth,
            sampleHeight,
            0,
            0,
            regionWidth,
            regionHeight
        );


        /* ==========================================================
           SUAVIZAÇÃO DO CAMPO FRI

           IMPORTANTE:
           O blur acontece AGORA, antes da conversão para RGB.
           Portanto não existe mistura de verde + cinza + azul
           para formar a antiga massa escura.
        ========================================================== */

        const smoothedCanvas =
            document.createElement(
                "canvas"
            );


        smoothedCanvas.width =
            regionWidth;


        smoothedCanvas.height =
            regionHeight;


        const smoothedContext =
            smoothedCanvas.getContext(
                "2d",
                {
                    willReadFrequently:
                        true
                }
            );


        if (!smoothedContext) {

            return;

        }


        smoothedContext.imageSmoothingEnabled =
            true;


        smoothedContext.imageSmoothingQuality =
            "high";


        smoothedContext.filter =
            "blur(10px)";


        smoothedContext.drawImage(
            fieldCanvas,
            0,
            0
        );


        smoothedContext.filter =
            "none";


        /* ==========================================================
           MÁSCARA TERRITORIAL

           A máscara é aplicada enquanto a imagem ainda representa
           FRI escalar. Assim pixels externos ficam transparentes
           antes da conversão cromática.
        ========================================================== */

        const maskCanvas =
            document.createElement(
                "canvas"
            );


        maskCanvas.width =
            regionWidth;


        maskCanvas.height =
            regionHeight;


        const maskContext =
            maskCanvas.getContext(
                "2d"
            );


        if (!maskContext) {

            return;

        }


        maskContext.fillStyle =
            "#ffffff";


        maskContext.beginPath();


        const drawRing =
            ring => {

                if (
                    !Array.isArray(
                        ring
                    ) ||
                    !ring.length
                ) {

                    return;

                }


                ring.forEach(
                    (
                        coordinate,
                        index
                    ) => {

                        if (
                            !Array.isArray(
                                coordinate
                            ) ||
                            coordinate.length < 2
                        ) {

                            return;

                        }


                        const lng =
                            Number(
                                coordinate[0]
                            );


                        const lat =
                            Number(
                                coordinate[1]
                            );


                        if (
                            !Number.isFinite(
                                lng
                            ) ||
                            !Number.isFinite(
                                lat
                            )
                        ) {

                            return;

                        }


                        const point =
                            this.map.latLngToContainerPoint(
                                [
                                    lat,
                                    lng
                                ]
                            );


                        const x =
                            point.x -
                            minX;


                        const y =
                            point.y -
                            minY;


                        if (
                            index === 0
                        ) {

                            maskContext.moveTo(
                                x,
                                y
                            );

                        } else {

                            maskContext.lineTo(
                                x,
                                y
                            );

                        }

                    }
                );


                maskContext.closePath();

            };


        this.territoryGeoJson.features.forEach(
            feature => {

                const geometry =
                    feature &&
                    feature.geometry;


                if (!geometry) {

                    return;

                }


                if (
                    geometry.type ===
                    "Polygon"
                ) {

                    geometry.coordinates.forEach(
                        drawRing
                    );

                } else if (
                    geometry.type ===
                    "MultiPolygon"
                ) {

                    geometry.coordinates.forEach(
                        polygon =>
                            polygon.forEach(
                                drawRing
                            )
                    );

                }

            }
        );


        maskContext.fill(
            "evenodd"
        );


        smoothedContext.globalCompositeOperation =
            "destination-in";


        smoothedContext.drawImage(
            maskCanvas,
            0,
            0
        );


        smoothedContext.globalCompositeOperation =
            "source-over";


        /* ==========================================================
           CONVERSÃO FRI → COR

           SOMENTE AGORA o valor escalar é transformado em cor.
           Portanto o gradiente é contínuo e não sofre mistura RGB
           durante o blur.
        ========================================================== */

        const fieldImage =
            smoothedContext.getImageData(
                0,
                0,
                regionWidth,
                regionHeight
            );


        const fieldData =
            fieldImage.data;


        for (
            let index = 0;
            index < fieldData.length;
            index += 4
        ) {

            if (
                fieldData[index + 3] === 0
            ) {

                continue;

            }


            const value =
                Math.max(
                    0,
                    Math.min(
                        100,
                        (
                            fieldData[index] /
                            255
                        ) *
                        100
                    )
                );


            const color =
                this.getFRIGradientColor(
                    value
                );


            const rgb =
                this.hexToRgb(
                    color
                );


            fieldData[index] =
                rgb.r;


            fieldData[index + 1] =
                rgb.g;


            fieldData[index + 2] =
                rgb.b;


            /*
             * A superfície é translúcida para preservar a
             * cartografia e os limites municipais.
             */
            fieldData[index + 3] =
                180;

        }


        smoothedContext.putImageData(
            fieldImage,
            0,
            0
        );


        /* ==========================================================
           RENDERIZAÇÃO FINAL
        ========================================================== */

        context.globalAlpha =
            1;


        context.imageSmoothingEnabled =
            true;


        context.imageSmoothingQuality =
            "high";


        context.drawImage(
            smoothedCanvas,
            minX,
            minY,
            regionWidth,
            regionHeight
        );


        context.globalAlpha =
            1;

    },

    hexToRgb(
        hex
    ) {

        const normalized =
            String(hex || "")
                .replace(
                    "#",
                    ""
                );

        if (
            normalized.length !== 6
        ) {

            return {
                r: 0,
                g: 0,
                b: 0
            };

        }

        return {
            r: parseInt(
                normalized.slice(0, 2),
                16
            ),
            g: parseInt(
                normalized.slice(2, 4),
                16
            ),
            b: parseInt(
                normalized.slice(4, 6),
                16
            )
        };

    },


    getFRIGradientColor(
        value
    ) {

        const stops = [

            [0, "#355c7d"],
            [20, "#4f86a8"],
            [40, "#287a40"],
            [60, "#9a6a00"],
            [80, "#a94c17"],
            [100, "#a52f2f"]

        ];

        const numeric =
            Math.max(
                0,
                Math.min(
                    100,
                    Number(value)
                )
            );

        for (
            let index = 1;
            index < stops.length;
            index += 1
        ) {

            const previous =
                stops[index - 1];

            const current =
                stops[index];

            if (
                numeric <= current[0]
            ) {

                const ratio =
                    (
                        numeric -
                        previous[0]
                    ) /
                    (
                        current[0] -
                        previous[0]
                    );

                return this.interpolateHexColor(
                    previous[1],
                    current[1],
                    ratio
                );

            }

        }

        return stops[
            stops.length - 1
        ][1];

    },


    interpolateHexColor(
        start,
        end,
        ratio
    ) {

        const parse =
            hex => {

                const value =
                    hex.replace(
                        "#",
                        ""
                    );

                return [
                    parseInt(
                        value.slice(0, 2),
                        16
                    ),
                    parseInt(
                        value.slice(2, 4),
                        16
                    ),
                    parseInt(
                        value.slice(4, 6),
                        16
                    )
                ];

            };

        const a =
            parse(start);

        const b =
            parse(end);

        const mix =
            channel =>
                Math.round(
                    channel[0] +
                    (
                        channel[1] -
                        channel[0]
                    ) * ratio
                );

        return `#${[mix([a[0], b[0]]), mix([a[1], b[1]]), mix([a[2], b[2]])].map(channel => channel.toString(16).padStart(2, "0")).join("")}`;

    },


    /* ======================================================
       CRIAR ÍCONE DO MARCADOR
    ====================================================== */

    createMarkerIcon(
        point
    ) {

        const severity =
            this.normalizeSeverity(
                point && point.severity
            );

        const iconClass =
            severity ||
            "none";

        const markerStyle =
            this.getMarkerStyle(
                point
            );

        return L.divIcon({

            className:
                "agroclima-marker-wrapper",

            html: `
                <div
                    class="agroclima-marker ${iconClass}"
                    style="background:${markerStyle.color};"
                    aria-label="Indicador climático"
                    title="Indicador climático">

                    <i class="bi bi-geo-alt-fill"></i>

                </div>
            `,

            iconSize:
                [
                    34,
                    34
                ],

            iconAnchor:
                [
                    17,
                    17
                ],

            popupAnchor:
                [
                    0,
                    -17
                ]

        });

    },


    /* ======================================================
       COR DO MARCADOR CONFORME A CAMADA ATIVA

       A legenda e o marcador devem representar a mesma
       variável visual. O popup continua exibindo a
       severidade separadamente.
    ====================================================== */

    getMarkerStyle(
        point
    ) {

        if (!point) {
            return { color: "#777777" };
        }

        if (this.activeLayer === "precipitacao") {
            const classification =
                this.getPrecipitationClass(
                    point.precipitation
                );

            return (
                this.precipitationStyles[
                    classification
                ] ||
                this.precipitationStyles.none
            );
        }

        if (this.activeLayer === "temperatura") {
            const classification =
                this.getTemperatureClass(
                    point.temperature
                );

            return (
                this.temperatureStyles[
                    classification
                ] ||
                this.temperatureStyles.unavailable
            );
        }

        if (this.activeLayer === "geadas") {
            const severity =
                this.normalizeSeverity(
                    point.severity
                );

            return (
                this.frostStyles[
                    severity
                ] ||
                this.frostStyles.none
            );
        }

        return {
            color: this.territoryStyle.color
        };
    },


    /* ======================================================
       ATUALIZAR CORES DOS MARCADORES
    ====================================================== */

    refreshMarkerIcons() {

        if (!this.markerLayer) {
            return;
        }

        this.markerLayer.eachLayer(
            marker => {

                if (!marker.__agroclimaPoint) {
                    return;
                }

                marker.setIcon(
                    this.createMarkerIcon(
                        marker.__agroclimaPoint
                    )
                );

            }
        );
    },


    /* ======================================================
       POPUP DOS MARCADORES
    ====================================================== */

    buildPopup(
        point
    ) {

        const altitude =
            point.altitude !== null &&
            point.altitude !== undefined &&
            point.altitude !== ""
                ? `${point.altitude} m`
                : "--";


        const fri =
            point.fri !== null &&
            point.fri !== undefined
                ? point.fri
                : "--";


        const confidence =
            point.confidence !== null &&
            point.confidence !== undefined
                ? point.confidence
                : "--";


        const severity =
            this.normalizeSeverity(
                point.severity
            );


        const severityLabel =
            this.getSeverityLabel(
                severity
            );


        const nome =
            this.escapeHtml(
                point.nome ||
                "Município"
            );


        const estado =
            this.escapeHtml(
                point.estado ||
                ""
            );


        const latitude =
            Number(
                point.latitude
            );


        const longitude =
            Number(
                point.longitude
            );


        const latitudeText =
            Number.isFinite(
                latitude
            )
                ? latitude.toFixed(4)
                : "--";


        const longitudeText =
            Number.isFinite(
                longitude
            )
                ? longitude.toFixed(4)
                : "--";


        return `
            <div class="agroclima-popup">

                <div class="agroclima-popup-title">
                    ${nome}
                </div>

                <div class="agroclima-popup-location">
                    ${estado}
                </div>

                <div class="agroclima-popup-grid">

                    <div class="agroclima-popup-item">

                        <span class="agroclima-popup-label">
                            Altitude
                        </span>

                        <span class="agroclima-popup-value">
                            ${altitude}
                        </span>

                    </div>


                    <div class="agroclima-popup-item">

                        <span class="agroclima-popup-label">
                            FRI
                        </span>

                        <span class="agroclima-popup-value">
                            ${fri}
                        </span>

                    </div>


                    <div class="agroclima-popup-item">

                        <span class="agroclima-popup-label">
                            Confiança
                        </span>

                        <span class="agroclima-popup-value">
                            ${confidence}
                        </span>

                    </div>


                    <div class="agroclima-popup-item">

                        <span class="agroclima-popup-label">
                            Coordenadas
                        </span>

                        <span class="agroclima-popup-value">
                            ${latitudeText},
                            ${longitudeText}
                        </span>

                    </div>

                </div>


                ${this.buildLayerIndicator(point)}


                <span
                    class="agroclima-popup-risk"
                    style="
                        background:${this.getSeverityBackground(severity)};
                        color:${this.getSeverityColor(severity)};
                    "
                >
                    ${severityLabel}
                </span>

            </div>
        `;

    },


    /* ======================================================
       INDICADOR DA CAMADA ATIVA NO POPUP
    ====================================================== */

    buildLayerIndicator(point) {

        if (!point) {
            return "";
        }

        let label = "Condição atual";
        let value = "--";
        let status = "";

        if (this.activeLayer === "geadas") {

            label = "Geada";
            value = point.frost ? "Ocorrência identificada" : "Sem ocorrência";
            status = point.frost_occurrences !== null && point.frost_occurrences !== undefined
                ? `${point.frost_occurrences} ocorrência(s)`
                : "";

        } else if (this.activeLayer === "temperatura") {

            label = "Temperatura";
            value = Number.isFinite(Number(point.temperature))
                ? `${Number(point.temperature).toFixed(1)} °C`
                : "Sem dado";
            status = this.getTemperatureLabel(point.temperature);

        } else if (this.activeLayer === "precipitacao") {

            label = "Precipitação 24h";
            value = Number.isFinite(Number(point.precipitation))
                ? `${Number(point.precipitation).toFixed(1)} mm`
                : "Sem dado";
            status = this.getPrecipitationLabel(point.precipitation);

        } else {

            label = "Monitoramento";
            value = "Dados agroclimáticos disponíveis";
            status = point.intelligence_available === false
                ? "Inteligência indisponível"
                : "Dados atualizados";

        }

        return `
            <div class="agroclima-popup-item" style="margin-top:8px;">
                <span class="agroclima-popup-label">${this.escapeHtml(label)}</span>
                <span class="agroclima-popup-value">${this.escapeHtml(value)}</span>
                <span class="agroclima-popup-label">${this.escapeHtml(status)}</span>
            </div>
        `;

    },


    /* ======================================================
       NORMALIZAR NOME
    ====================================================== */

    normalizeName(
        value
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return "";

        }


        return String(
            value
        )
            .normalize(
                "NFD"
            )
            .replace(
                /[\u0300-\u036f]/g,
                ""
            )
            .toLowerCase()
            .trim();

    },


    /* ======================================================
       NORMALIZAR SEVERIDADE
    ====================================================== */

    normalizeSeverity(
        severity
    ) {

        if (
            !severity
        ) {

            return "none";

        }


        const value =
            String(
                severity
            )
                .toLowerCase()
                .trim();


        if (
            value === "critical" ||
            value === "critico" ||
            value === "crítico"
        ) {

            return "critical";

        }


        if (
            value === "high" ||
            value === "alto"
        ) {

            return "alert";

        }


        if (
            value === "medium" ||
            value === "moderado" ||
            value === "medio" ||
            value === "médio"
        ) {

            return "attention";

        }


        if (
            value === "low" ||
            value === "baixo"
        ) {

            return "normal";

        }


        if (
            value === "none" ||
            value === "sem risco" ||
            value === "sem_risco"
        ) {

            return "none";

        }


        return "none";

    },


    /* ======================================================
       LABEL DA SEVERIDADE
    ====================================================== */

    getSeverityLabel(
        severity
    ) {

        const labels = {

            normal:
                "BAIXO",

            attention:
                "MODERADO",

            alert:
                "ALTO",

            critical:
                "CRÍTICO",

            none:
                "SEM RISCO"

        };


        return (
            labels[
                severity
            ] ||
            labels.none
        );

    },


    /* ======================================================
       COR DE FUNDO DA SEVERIDADE
    ====================================================== */

    getSeverityBackground(
        severity
    ) {

        const colors = {

            normal:
                "#e8f5ec",

            attention:
                "#fff4d6",

            alert:
                "#fff0e5",

            critical:
                "#fde7e7",

            none:
                "#f0f0f0"

        };


        return (
            colors[
                severity
            ] ||
            colors.none
        );

    },


    /* ======================================================
       COR DA SEVERIDADE
    ====================================================== */

    getSeverityColor(
        severity
    ) {

        const colors = {

            normal:
                "#287a40",

            attention:
                "#9a6a00",

            alert:
                "#a94c17",

            critical:
                "#a52f2f",

            none:
                "#666"

        };


        return (
            colors[
                severity
            ] ||
            colors.none
        );

    },


    /* ======================================================
       BOTÕES DAS CAMADAS
    ====================================================== */

    bindLayerButtons() {

        const buttons =
            document.querySelectorAll(
                "[data-map-layer]"
            );


        if (
            !buttons.length
        ) {

            return;

        }


        buttons.forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        buttons.forEach(
                            item => {

                                item.classList.remove(
                                    "active"
                                );

                            }
                        );


                        button.classList.add(
                            "active"
                        );


                        this.activeLayer =
                            button.dataset.mapLayer;


                        this.changeLayer(
                            this.activeLayer
                        );

                    }
                );

            }
        );

    },


    /* ======================================================
       ALTERAR CAMADA
    ====================================================== */

    changeLayer(
        layer
    ) {

        this.activeLayer =
            layer;


        if (
            this.territoryLayer
        ) {

            this.territoryLayer.bringToBack();

        }


        if (
            layer !== "geadas"
        ) {

            this.hideFRISurface();

        }


        /* ==================================================
           MUNICÍPIOS
        ================================================== */

        if (
            layer ===
            "municipios"
        ) {

            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        1
                    );

                }
            );


            this.updateTerritoryStyle();
            this.refreshMarkerIcons();
            this.refreshMapPopups();
            this.updateLegend();

            return;

        }


        /* ==================================================
           GEADAS
        ================================================== */

        if (
            layer ===
            "geadas"
        ) {

            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        1
                    );

                }
            );


            this.updateTerritoryStyle();
            this.refreshMarkerIcons();
            this.refreshMapPopups();
            this.updateLegend();
            this.refreshFRISurface();

            return;

        }


        /* ==================================================
           TEMPERATURA
        ================================================== */

        if (
            layer ===
            "temperatura"
        ) {

            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        1
                    );

                }
            );


            this.updateTerritoryStyle();
            this.refreshMarkerIcons();
            this.refreshMapPopups();
            this.updateLegend();

            return;

        }


        /* ==================================================
           PRECIPITAÇÃO
        ================================================== */

        if (
            layer ===
            "precipitacao"
        ) {

            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        1
                    );

                }
            );


            this.updateTerritoryStyle();
            this.refreshMarkerIcons();
            this.refreshMapPopups();
            this.updateLegend();

            return;

        }


        console.warn(
            "[AGROCLIMA] Camada de mapa não reconhecida:",
            layer
        );

    },


    /* ======================================================
       SEGURANÇA HTML
    ====================================================== */

    escapeHtml(
        value
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return "";

        }


        return String(
            value
        )

            .replaceAll(
                "&",
                "&amp;"
            )

            .replaceAll(
                "<",
                "&lt;"
            )

            .replaceAll(
                ">",
                "&gt;"
            )

            .replaceAll(
                '"',
                "&quot;"
            )

            .replaceAll(
                "'",
                "&#039;"
            );

    }

};


/* ==========================================================
   AGROCLIMA CAFÉ
   DASHBOARD V3
   CHART CONTROLLER — FASE 2

   Responsabilidades:
   - Ler os dados fornecidos pelo DashboardService
   - Inicializar o gráfico de evolução climática
   - Exibir temperatura média
   - Exibir média móvel de 7 dias
   - Disponibilizar precipitação como série secundária
   - Controlar os períodos do painel

   IMPORTANTE:
   Nenhuma regra de inteligência climática é calculada aqui.
   Os dados são fornecidos pelo backend através de json_script.
========================================================== */


const ChartController = {

    chart: null,

    initialized: false,

    activePeriod: null,


    init() {

        if (this.initialized) {

            return;

        }


        const canvas =
            document.getElementById("weatherChart");


        if (!canvas) {

            console.info(
                "[AGROCLIMA] Canvas #weatherChart não encontrado."
            );

            return;

        }


        if (typeof Chart === "undefined") {

            console.error(
                "[AGROCLIMA] Chart.js não está disponível."
            );

            return;

        }


        /* ==================================================
           SÉRIES DISPONIBILIZADAS PELO BACKEND

           Cada período possui sua própria série histórica.
           O JavaScript somente seleciona e apresenta os
           dados; nenhuma regra climática é calculada aqui.
        ================================================== */

        /*
         * O template V3 publica CADA PERÍODO em um único json_script:
         *
         *   chart-period-hoje
         *   chart-period-7-dias
         *   chart-period-30-dias
         *   chart-period-historico
         *
         * Portanto, não devemos procurar IDs derivados como
         * "-temperatura" ou "-precipitacao". Esses elementos não existem
         * no template atual.
         *
         * O objeto retornado por readPeriod() já contém:
         *   dias
         *   temperatura
         *   precipitacao
         */

        const hoje =
            this.readPeriod(
                "chart-period-hoje"
            );

        const seteDias =
            this.readPeriod(
                "chart-period-7-dias"
            );

        const trintaDias =
            this.readPeriod(
                "chart-period-30-dias"
            );

        const historico =
            this.readPeriod(
                "chart-period-historico"
            );

        this.periods = {

            hoje:
                hoje,

            "7":
                seteDias,

            "7_dias":
                seteDias,

            "30":
                trintaDias,

            "30_dias":
                trintaDias,

            historico:
                historico

        };

        console.info(
            "[AGROCLIMA] Períodos carregados:",
            {
                hoje: this.periods.hoje.dias.length,
                "7_dias": this.periods["7_dias"].dias.length,
                "30_dias": this.periods["30_dias"].dias.length,
                historico: this.periods.historico.dias.length
            }
        );


        /* ==================================================
           COMPATIBILIDADE COM O BLOCO ANTIGO

           Caso a página ainda possua os elementos legados,
           eles continuam sendo aceitos como fallback.
        ================================================== */

        if (!this.periods["7"].dias.length) {

            this.periods["7"] = {

                dias: this.readJson(
                    "chart-dias"
                ),

                temperatura: this.readJson(
                    "chart-temperatura"
                ),

                precipitacao: this.readJson(
                    "chart-precipitacao"
                )

            };

        }


        /*
         * O painel inicia visualmente no período "Hoje".
         * Portanto, o gráfico também deve iniciar com os dados
         * de "Hoje". Caso esse período ainda não possua dados,
         * utiliza 7 dias como fallback, preservando a
         * disponibilidade do gráfico.
         */
        let initialKey = "hoje";


        if (
            !this.periods[initialKey] ||
            !this.periods[initialKey].dias.length
        ) {
            initialKey = "7";
        }


        if (
            !this.periods[initialKey] ||
            !this.periods[initialKey].dias.length
        ) {
            initialKey = "30";
        }


        if (
            !this.periods[initialKey] ||
            !this.periods[initialKey].dias.length
        ) {
            initialKey = "historico";
        }


        const initialPeriod =
            this.periods[initialKey];


        if (!initialPeriod.dias.length) {

            console.warn(
                "[AGROCLIMA] Nenhum dado de evolução climática disponível."
            );

            return;

        }


        this.activePeriod = initialKey;


        this.createChart(
            canvas,
            initialPeriod.dias,
            initialPeriod.temperatura,
            initialPeriod.precipitacao
        );

        /*
         * Sincroniza o resumo com o mesmo período apresentado
         * pelo gráfico.
         */
        this.updatePeriodSummary(
            initialPeriod
        );


        this.bindPeriodButtons();


        /*
         * Mantém o estado visual do botão sincronizado
         * com o período efetivamente apresentado.
         */
        this.setActivePeriodButton(
            initialKey
        );


        this.initialized = true;

    },


    readPeriod(
        daysId,
        temperatureId = null,
        precipitationId = null
    ) {

        /* ==================================================
           FORMATO V3 ATUAL

           O template publica um único json_script por período:

               {
                   dias: [...],
                   temperatura: [...],
                   precipitacao: [...],
                   resumo: {
                       temperatura_media: ...,
                       precipitacao: ...,
                       geadas: ...,
                       tendencia: ...
                   }
               }

           O controlador consome esse objeto diretamente.

           Nenhuma série é criada, completada ou alterada.
        ================================================== */

        const bundled =
            this.readJsonValue(
                daysId
            );

        if (
            bundled &&
            typeof bundled === "object" &&
            !Array.isArray(bundled)
        ) {

            return {

                dias:
                    Array.isArray(bundled.dias)
                        ? bundled.dias
                        : [],

                temperatura:
                    Array.isArray(bundled.temperatura)
                        ? bundled.temperatura
                        : [],

                precipitacao:
                    Array.isArray(bundled.precipitacao)
                        ? bundled.precipitacao
                        : [],

                resumo:
                    bundled.resumo &&
                    typeof bundled.resumo === "object" &&
                    !Array.isArray(bundled.resumo)
                        ? bundled.resumo
                        : {}

            };

        }

        /* ==================================================
           FORMATO LEGADO

           Mantido apenas para compatibilidade com versões
           anteriores do template.
        ================================================== */

        return {

            dias:
                Array.isArray(bundled)
                    ? bundled
                    : [],

            temperatura:
                temperatureId
                    ? this.readJson(
                        temperatureId
                    )
                    : [],

            precipitacao:
                precipitationId
                    ? this.readJson(
                        precipitationId
                    )
                    : [],

            resumo: {}

        };

    },


    readJsonValue(id) {

        const element =
            document.getElementById(id);


        if (!element) {

            return null;

        }


        try {

            return JSON.parse(
                element.textContent
            );

        } catch (error) {

            console.error(
                `[AGROCLIMA] Erro ao interpretar ${id}.`,
                error
            );


            return null;

        }

    },


    readJson(id) {

        const value = this.readJsonValue(
            id
        );


        return Array.isArray(value)
            ? value
            : [];

    },


    normalizeNumber(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }


        const number =
            Number(
                String(value)
                    .replace(",", ".")
            );


        return Number.isFinite(number)
            ? number
            : null;

    },


    buildMovingAverage(values) {

        return values.map(
            (_, index) => {

                const start =
                    Math.max(
                        0,
                        index - 6
                    );


                const window =
                    values
                        .slice(
                            start,
                            index + 1
                        )
                        .filter(
                            value =>
                                value !== null &&
                                Number.isFinite(value)
                        );


                if (!window.length) {

                    return null;

                }


                const average =
                    window.reduce(
                        (sum, value) =>
                            sum + value,
                        0
                    ) / window.length;


                return Number(
                    average.toFixed(1)
                );

            }
        );

    },


    createChart(
        canvas,
        labels,
        temperature,
        precipitation
    ) {

        if (this.chart) {

            this.chart.destroy();

        }


        const safeTemperature =
            labels.map(
                (_, index) =>
                    this.normalizeNumber(
                        temperature[index]
                    )
            );


        const safePrecipitation =
            labels.map(
                (_, index) =>
                    this.normalizeNumber(
                        precipitation[index]
                    )
            );


        const movingAverage =
            this.buildMovingAverage(
                safeTemperature
            );

        console.info(
            "[AGROCLIMA] Dataset final enviado ao Chart.js:",
            {
                labels: labels,
                temperatura: safeTemperature,
                precipitacao: safePrecipitation
            }
        );




        const context =
            canvas.getContext("2d");


        this.chart =
            new Chart(
                context,
                {

                    type: "line",


                    data: {

                        labels: labels,


                        datasets: [

                            {

                                label:
                                    "Temperatura média",

                                data:
                                    safeTemperature,

                                borderColor:
                                    "#F0A51A",

                                backgroundColor:
                                    "rgba(240,165,26,0.08)",

                                borderWidth:
                                    2.4,

                                pointRadius:
                                    2.2,

                                pointHoverRadius:
                                    5,

                                pointBackgroundColor:
                                    "#F0A51A",

                                pointBorderColor:
                                    "#F0A51A",

                                tension:
                                    0.28,

                                fill:
                                    false,

                                yAxisID:
                                    "temperature"

                            },


                            {

                                label:
                                    "Média móvel (7 dias)",

                                data:
                                    movingAverage,

                                borderColor:
                                    "#BEB7AA",

                                backgroundColor:
                                    "transparent",

                                borderWidth:
                                    1.4,

                                borderDash:
                                    [6, 5],

                                pointRadius:
                                    0,

                                pointHoverRadius:
                                    0,

                                tension:
                                    0.25,

                                fill:
                                    false,

                                yAxisID:
                                    "temperature"

                            },


                            {

                                label:
                                    "Precipitação",

                                data:
                                    safePrecipitation,

                                borderColor:
                                    "#4FA3D1",

                                backgroundColor:
                                    "rgba(79,163,209,0.10)",

                                borderWidth:
                                    1.8,

                                pointRadius:
                                    2,

                                pointHoverRadius:
                                    4,

                                pointBackgroundColor:
                                    "#4FA3D1",

                                pointBorderColor:
                                    "#4FA3D1",

                                tension:
                                    0.2,

                                fill:
                                    false,

                                yAxisID:
                                    "precipitation"

                            }

                        ]

                    },


                    options: {

                        responsive:
                            true,

                        maintainAspectRatio:
                            false,


                        animation: {

                            duration:
                                500

                        },


                        interaction: {

                            mode:
                                "index",

                            intersect:
                                false

                        },


                        layout: {

                            padding: {

                                top:
                                    4,

                                right:
                                    8,

                                bottom:
                                    2,

                                left:
                                    4

                            }

                        },


                        plugins: {

                            legend: {

                                display:
                                    true,

                                position:
                                    "top",

                                align:
                                    "start",


                                labels: {

                                    color:
                                        "#3C342B",

                                    usePointStyle:
                                        true,

                                    pointStyle:
                                        "line",

                                    boxWidth:
                                        24,

                                    padding:
                                        16,


                                    font: {

                                        family:
                                            "Inter, sans-serif",

                                        size:
                                            11,

                                        weight:
                                            "500"

                                    }

                                }

                            },


                            tooltip: {

                                backgroundColor:
                                    "#211A14",

                                titleColor:
                                    "#FFFFFF",

                                bodyColor:
                                    "#F4EFE8",

                                borderColor:
                                    "#6F543C",

                                borderWidth:
                                    1,

                                padding:
                                    10,


                                callbacks: {

                                    label:
                                        context => {

                                            const value =
                                                context.parsed.y;


                                            if (
                                                value === null ||
                                                value === undefined
                                            ) {

                                                return (
                                                    `${context.dataset.label}: —`
                                                );

                                            }


                                            if (
                                                context.dataset.yAxisID ===
                                                "precipitation"
                                            ) {

                                                return (
                                                    `${context.dataset.label}: ${value.toFixed(1)} mm`
                                                );

                                            }


                                            return (
                                                `${context.dataset.label}: ${value.toFixed(1)} °C`
                                            );

                                        }

                                }

                            }

                        },


                        scales: {

                            x: {

                                grid: {

                                    color:
                                        "rgba(74,63,52,0.08)",

                                    drawBorder:
                                        false

                                },


                                border: {

                                    display:
                                        false

                                },


                                ticks: {

                                    color:
                                        "#756C61",

                                    maxRotation:
                                        0,

                                    minRotation:
                                        0,

                                    autoSkip:
                                        true,

                                    maxTicksLimit:
                                        8,


                                    font: {

                                        family:
                                            "Inter, sans-serif",

                                        size:
                                            10

                                    }

                                }

                            },


                            temperature: {

                                position:
                                    "left",

                                beginAtZero:
                                    false,


                                grid: {

                                    color:
                                        "rgba(74,63,52,0.08)",

                                    drawBorder:
                                        false

                                },


                                border: {

                                    display:
                                        false

                                },


                                ticks: {

                                    color:
                                        "#756C61",

                                    callback:
                                        value =>
                                            `${value}°C`,


                                    font: {

                                        family:
                                            "Inter, sans-serif",

                                        size:
                                            10

                                    }

                                }

                            },


                            precipitation: {

                                position:
                                    "right",

                                beginAtZero:
                                    true,

                                grid: {

                                    drawOnChartArea:
                                        false,

                                    drawBorder:
                                        false

                                },

                                border: {

                                    display:
                                        false

                                },

                                ticks: {

                                    display:
                                        true,

                                    color:
                                        "#4F86A8",

                                    padding:
                                        6,

                                    callback:
                                        value =>
                                            `${value} mm`,

                                    font: {

                                        family:
                                            "Inter, sans-serif",

                                        size:
                                            10

                                    }

                                }

                            }

                        }

                    }

                }
            );


        window.weatherChart =
            this.chart;

    },


    /* ======================================================
       RESUMO DO PERÍODO

       O resumo é fornecido pelo backend dentro de cada
       período do DashboardService/ChartService.

       O JavaScript apenas apresenta os valores recebidos.
       Não recalcula geadas ou tendência e não cria valores
       estáticos no frontend.

       Como fallback de compatibilidade, temperatura e
       precipitação podem ser calculadas a partir das séries
       quando o campo correspondente do resumo não existir.
    ====================================================== */

    updatePeriodSummary(
        period
    ) {

        if (!period) {
            return;
        }

        const summaryItems =
            document.querySelectorAll(
                ".chart-summary .summary-item"
            );

        if (!summaryItems.length) {
            return;
        }

        const summary =
            period.resumo &&
            typeof period.resumo === "object"
                ? period.resumo
                : {};

        const temperatures =
            Array.isArray(period.temperatura)
                ? period.temperatura
                    .map(value => Number(value))
                    .filter(Number.isFinite)
                : [];

        const precipitation =
            Array.isArray(period.precipitacao)
                ? period.precipitacao
                    .map(value => Number(value))
                    .filter(Number.isFinite)
                : [];

        /*
         * ==================================================
         * 1 — TEMPERATURA MÉDIA
         *
         * Prioridade absoluta para o valor consolidado pelo
         * backend. O cálculo da série é somente fallback.
         * ==================================================
         */

        let temperatureAverage =
            Number(summary.temperatura_media);

        if (
            !Number.isFinite(
                temperatureAverage
            )
        ) {

            temperatureAverage =
                temperatures.length
                    ? temperatures.reduce(
                        (total, value) =>
                            total + value,
                        0
                    ) / temperatures.length
                    : null;

        }

        if (summaryItems[0]) {

            const valueElement =
                summaryItems[0].querySelector(
                    "strong"
                );

            if (valueElement) {

                valueElement.textContent =
                    Number.isFinite(
                        temperatureAverage
                    )
                        ? `${temperatureAverage.toLocaleString(
                            "pt-BR",
                            {
                                minimumFractionDigits: 1,
                                maximumFractionDigits: 1
                            }
                        )}°C`
                        : "--";

            }

        }

        /*
         * ==================================================
         * 2 — PRECIPITAÇÃO ACUMULADA
         *
         * Prioridade absoluta para o valor consolidado pelo
         * backend. O cálculo da série é somente fallback.
         * ==================================================
         */

        let precipitationTotal =
            Number(summary.precipitacao);

        if (
            !Number.isFinite(
                precipitationTotal
            )
        ) {

            precipitationTotal =
                precipitation.length
                    ? precipitation.reduce(
                        (sum, value) =>
                            sum + value,
                        0
                    )
                    : null;

        }

        if (summaryItems[1]) {

            const valueElement =
                summaryItems[1].querySelector(
                    "strong"
                );

            if (valueElement) {

                valueElement.textContent =
                    Number.isFinite(
                        precipitationTotal
                    )
                        ? `${precipitationTotal.toLocaleString(
                            "pt-BR",
                            {
                                minimumFractionDigits: 1,
                                maximumFractionDigits: 1
                            }
                        )} mm`
                        : "--";

            }

        }

        /*
         * ==================================================
         * 3 — GEADAS
         *
         * O valor deve vir exclusivamente do resumo
         * produzido pelo backend.
         *
         * Não existe valor estático ou fallback inventado.
         * ==================================================
         */

        const frostValue =
            Number(summary.geadas);

        if (summaryItems[2]) {

            const valueElement =
                summaryItems[2].querySelector(
                    "strong"
                );

            if (valueElement) {

                valueElement.textContent =
                    Number.isFinite(
                        frostValue
                    )
                        ? String(
                            summary.geadas
                        )
                        : "--";

            }

        }

        /*
         * ==================================================
         * 4 — TENDÊNCIA
         *
         * Também é fornecida pelo backend.
         * ==================================================
         */

        if (summaryItems[3]) {

            const valueElement =
                summaryItems[3].querySelector(
                    "strong"
                );

            if (valueElement) {

                valueElement.textContent =
                    summary.tendencia
                        ? String(
                            summary.tendencia
                        )
                        : "--";

            }

        }

        console.info(
            "[AGROCLIMA] Resumo do período atualizado:",
            {
                temperatura_media:
                    Number.isFinite(
                        temperatureAverage
                    )
                        ? temperatureAverage
                        : null,

                precipitacao:
                    Number.isFinite(
                        precipitationTotal
                    )
                        ? precipitationTotal
                        : null,

                geadas:
                    Number.isFinite(
                        frostValue
                    )
                        ? summary.geadas
                        : null,

                tendencia:
                    summary.tendencia ?? null

            }
        );

    },


    /* ======================================================
       RESOLVER PERÍODO DO BOTÃO

       O atributo data-period é a fonte funcional preferencial.
       A leitura do texto permanece apenas como fallback de
       compatibilidade com o template legado.

       Contrato recomendado no template:

           data-period="hoje"
           data-period="7"
           data-period="30"
           data-period="historico"

       Dessa forma, alteração de copy, tradução ou identidade
       visual não altera o comportamento do controlador.
    ====================================================== */

    getPeriodFromButton(
        button
    ) {

        if (!button) {

            return "7";

        }


        const dataPeriod =
            button.dataset
                ? button.dataset.period
                : null;


        if (dataPeriod) {

            const normalized =
                String(dataPeriod)
                    .trim()
                    .toLowerCase();

            const aliases = {
                hoje: "hoje",
                "7": "7",
                "7_dias": "7",
                "7-dias": "7",
                "30": "30",
                "30_dias": "30",
                "30-dias": "30",
                historico: "historico",
                "histórico": "historico"
            };


            if (aliases[normalized]) {

                return aliases[normalized];

            }

        }


        /*
         * Compatibilidade com o template anterior.
         * Este caminho será removido somente quando o template
         * estiver definitivamente migrado para data-period.
         */
        const label =
            button.textContent
                .trim()
                .toLowerCase();


        if (label === "hoje") {

            return "hoje";

        }


        if (label === "7 dias") {

            return "7";

        }


        if (label === "30 dias") {

            return "30";

        }


        if (label === "histórico" || label === "historico") {

            return "historico";

        }


        return "7";

    },


    bindPeriodButtons() {

        const chartPanel =
            document.getElementById("weatherChart")
                ? document.getElementById("weatherChart").closest(".dashboard-panel")
                : null;

        if (!chartPanel) {
            return;
        }

        const buttons =
            chartPanel.querySelectorAll(
                ".panel-actions .btn-panel"
            );


        if (!buttons.length) {

            return;

        }


        buttons.forEach(
            button => {

                /*
                 * Materializa o contrato funcional no DOM quando
                 * o template ainda não fornece data-period.
                 * Em templates novos, o valor declarado pelo HTML
                 * é preservado.
                 */
                const period =
                    this.getPeriodFromButton(
                        button
                    );


                if (
                    button.dataset &&
                    !button.dataset.period
                ) {

                    button.dataset.period =
                        period;

                }


                button.addEventListener(
                    "click",
                    () => {

                        const period =
                            this.getPeriodFromButton(
                                button
                            );


                        const data =
                            this.periods[period];


                        /*
                         * Valida o período antes de alterar o
                         * estado visual do botão. Assim, um período
                         * sem dados não deixa a interface
                         * aparentemente selecionada sem atualizar
                         * o gráfico.
                         */
                        if (
                            !data ||
                            !Array.isArray(data.dias) ||
                            !data.dias.length
                        ) {

                            console.warn(
                                "[AGROCLIMA] Período sem dados:",
                                period
                            );

                            return;

                        }


                        const canvas =
                            document.getElementById(
                                "weatherChart"
                            );


                        if (!canvas) {

                            return;

                        }


                        console.info(
                            "[AGROCLIMA] Dados do período antes do gráfico:",
                            period,
                            {
                                dias: data.dias,
                                temperatura: data.temperatura,
                                precipitacao: data.precipitacao
                            }
                        );


                        this.createChart(
                            canvas,
                            data.dias,
                            data.temperatura,
                            data.precipitacao
                        );

                        /*
                         * Mantém os cards-resumo sincronizados
                         * com o período efetivamente selecionado.
                         */
                        this.updatePeriodSummary(
                            data
                        );


                        this.activePeriod = period;


                        this.setActivePeriodButton(
                            period
                        );


                        console.info(
                            "[AGROCLIMA] Período selecionado:",
                            period,
                            "| Registros:",
                            data.dias.length
                        );

                    }
                );

            }
        );

    },


    /*
     * ======================================================
     * BOTÃO DO PERÍODO ATIVO
     *
     * Mantém a seleção visual sincronizada com os dados
     * realmente apresentados no gráfico.
     * ======================================================
     */

    setActivePeriodButton(
        period
    ) {

        const chartPanel =
            document.getElementById("weatherChart")
                ? document.getElementById("weatherChart").closest(".dashboard-panel")
                : null;

        if (!chartPanel) {
            return;
        }

        const buttons =
            chartPanel.querySelectorAll(
                ".panel-actions .btn-panel"
            );


        if (!buttons.length) {

            return;

        }


        buttons.forEach(
            button => {

                button.classList.remove(
                    "active"
                );


                const buttonPeriod =
                    this.getPeriodFromButton(
                        button
                    );


                if (
                    buttonPeriod === period
                ) {

                    button.classList.add(
                        "active"
                    );

                }

            }
        );

    },


    resize() {

        if (
            this.chart &&
            typeof this.chart.resize === "function"
        ) {

            this.chart.resize();

        }

    }

};


/* ==========================================================
   AGROCLIMA CAFÉ
   DASHBOARD V3
   RANKING CONTROLLER — FASE FINAL

   Responsabilidades:
   - Controlar Top 10 / Todos do Ranking.
   - Preservar integralmente a ordenação entregue pelo backend.
   - Não calcular FRI, severidade ou confiança.
   - Não interferir nos botões do gráfico.
========================================================== */

const RankingController = {

    initialized: false,

    init() {

        if (this.initialized) {
            return;
        }

        const panel =
            document.querySelector(".ranking-panel");

        if (!panel) {
            return;
        }

        const list =
            panel.querySelector(".ranking-list");

        if (!list) {
            return;
        }

        const rows = Array.from(
            list.querySelectorAll(".ranking-item")
        );

        /*
         * O Ranking é apresentado em ordem decrescente de FRI.
         * O valor é apenas lido do backend; nenhuma regra de
         * inteligência é recalculada no frontend.
         */
        rows.sort((a, b) => {
            const scoreA = Number(a.dataset.rankingScore);
            const scoreB = Number(b.dataset.rankingScore);

            const safeA = Number.isFinite(scoreA) ? scoreA : -Infinity;
            const safeB = Number.isFinite(scoreB) ? scoreB : -Infinity;

            return safeB - safeA;
        });

        rows.forEach((row, index) => {
            list.appendChild(row);

            const position =
                row.querySelector(".ranking-position");

            if (position) {
                if (index === 0) {
                    position.textContent = "🥇";
                } else if (index === 1) {
                    position.textContent = "🥈";
                } else if (index === 2) {
                    position.textContent = "🥉";
                } else {
                    position.textContent = `${index + 1}º`;
                }
            }
        });

        const buttons = Array.from(
            panel.querySelectorAll(
                "[data-ranking-filter]"
            )
        );

        if (!buttons.length) {
            return;
        }

        const applyFilter = filter => {

            const limit =
                filter === "top10"
                    ? 10
                    : rows.length;

            rows.forEach(
                (row, index) => {
                    row.hidden = index >= limit;
                }
            );

            buttons.forEach(
                button => {
                    const active =
                        button.dataset.rankingFilter === filter;

                    button.classList.toggle(
                        "active",
                        active
                    );

                    button.setAttribute(
                        "aria-pressed",
                        active ? "true" : "false"
                    );
                }
            );

            panel.dataset.rankingFilter = filter;
        };

        buttons.forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        applyFilter(
                            button.dataset.rankingFilter === "all"
                                ? "all"
                                : "top10"
                        );
                    }
                );
            }
        );

        applyFilter("top10");
        this.initialized = true;
    }
};

/* ==========================================================
   REDIMENSIONAMENTO
========================================================== */

window.addEventListener(
    "resize",
    () => {

        ChartController.resize();

    }
);


/* ==========================================================
   INICIALIZAÇÃO
========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        MapController.init();

        ChartController.init();

        RankingController.init();

    }
);