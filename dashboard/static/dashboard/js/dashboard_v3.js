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
                0.45

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
                0.45

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
                0.50

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
                0.55

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
                0.35

        }

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
            450;


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


        this.initialized =
            true;


        this.bindLayerButtons();


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


            return (
                this.frostStyles[
                    severity
                ] ||
                this.frostStyles.none
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
                                ? 0.65
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


                const severity =
                    this.normalizeSeverity(
                        point.severity
                    );


                const icon =
                    this.createMarkerIcon(
                        severity
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
       CRIAR ÍCONE DO MARCADOR
    ====================================================== */

    createMarkerIcon(
        severity
    ) {

        const iconClass =
            severity ||
            "none";


        return L.divIcon({

            className:
                "agroclima-marker-wrapper",

            html: `
                <div
                    class="agroclima-marker ${iconClass}"
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
                "SEM CLASSIFICAÇÃO"

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


            return;

        }


        /* ==================================================
           TEMPERATURA
        ================================================== */

        if (
            layer ===
            "temperatura"
        ) {

            console.info(
                "[AGROCLIMA] Camada de temperatura aguardando indicador climático municipal."
            );


            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        0.45
                    );

                }
            );


            this.updateTerritoryStyle();


            return;

        }


        /* ==================================================
           PRECIPITAÇÃO
        ================================================== */

        if (
            layer ===
            "precipitacao"
        ) {

            console.info(
                "[AGROCLIMA] Camada de precipitação aguardando indicador climático municipal."
            );


            this.markerLayer.eachLayer(
                marker => {

                    marker.setOpacity(
                        0.45
                    );

                }
            );


            this.updateTerritoryStyle();


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

        this.periods = {

            hoje: this.readPeriod(
                "chart-period-hoje-dias",
                "chart-period-hoje-temperatura",
                "chart-period-hoje-precipitacao"
            ),

            "7": this.readPeriod(
                "chart-period-7-dias",
                "chart-period-7-temperatura",
                "chart-period-7-precipitacao"
            ),

            "30": this.readPeriod(
                "chart-period-30-dias",
                "chart-period-30-temperatura",
                "chart-period-30-precipitacao"
            ),

            historico: this.readPeriod(
                "chart-period-historico-dias",
                "chart-period-historico-temperatura",
                "chart-period-historico-precipitacao"
            )

        };


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


        if (!this.periods[initialKey].dias.length) {
            initialKey = "7";
        }


        if (!this.periods[initialKey].dias.length) {
            initialKey = "30";
        }


        if (!this.periods[initialKey].dias.length) {
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
        temperatureId,
        precipitationId
    ) {

        return {

            dias: this.readJson(
                daysId
            ),

            temperatura: this.readJson(
                temperatureId
            ),

            precipitacao: this.readJson(
                precipitationId
            )

        };

    },


    readJson(id) {

        const element =
            document.getElementById(id);


        if (!element) {

            return [];

        }


        try {

            const value =
                JSON.parse(
                    element.textContent
                );


            return Array.isArray(value)
                ? value
                : [];


        } catch (error) {

            console.error(
                `[AGROCLIMA] Erro ao interpretar ${id}.`,
                error
            );


            return [];

        }

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
                                    1.6,

                                pointRadius:
                                    1.5,

                                tension:
                                    0.25,

                                fill:
                                    false,

                                hidden:
                                    true,

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
                                        false

                                }

                            }

                        }

                    }

                }
            );


        window.weatherChart =
            this.chart;

    },


    bindPeriodButtons() {

        const buttons =
            document.querySelectorAll(
                ".panel-actions .btn-panel"
            );


        if (!buttons.length) {

            return;

        }


        buttons.forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const label =
                            button.textContent
                                .trim()
                                .toLowerCase();

                        let period =
                            "7";


                        if (label === "hoje") {

                            period = "hoje";


                        } else if (
                            label === "7 dias"
                        ) {

                            period = "7";


                        } else if (
                            label === "30 dias"
                        ) {

                            period = "30";


                        } else if (
                            label === "histórico"
                        ) {

                            period = "historico";

                        }


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


                        this.createChart(
                            canvas,
                            data.dias,
                            data.temperatura,
                            data.precipitacao
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

        const buttons =
            document.querySelectorAll(
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


                const label =
                    button.textContent
                        .trim()
                        .toLowerCase();


                let buttonPeriod =
                    "7";


                if (label === "hoje") {

                    buttonPeriod = "hoje";


                } else if (
                    label === "7 dias"
                ) {

                    buttonPeriod = "7";


                } else if (
                    label === "30 dias"
                ) {

                    buttonPeriod = "30";


                } else if (
                    label === "histórico"
                ) {

                    buttonPeriod = "historico";

                }


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

    }
);