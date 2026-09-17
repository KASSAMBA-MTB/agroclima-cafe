/* ============================================================
   AGROCLIMA CAFÉ — POPUP MUNICIPAL

   Módulo de apresentação do contrato municipal canônico.

   Responsabilidade:
   - receber um map_point já enriquecido pelo backend;
   - apresentar os dados disponíveis de forma padronizada;
   - aplicar somente formatação visual/textual;
   - explicitar ausência de dados.

   Não responsabilidade:
   - consultar API;
   - consultar banco de dados;
   - calcular FRI;
   - calcular severidade;
   - calcular classificação térmica;
   - calcular indicadores pluviométricos;
   - criar decisões agroclimáticas.

   Integração posterior:
   dashboard_v3.js deverá delegar a construção do popup a este
   módulo, preservando o map_point como fonte única de dados.
============================================================ */

(function (window) {

    "use strict";


    const MODULE_NAME = "AgroClimaMunicipalPopup";

    const MISSING = "Não disponível";


    /* ========================================================
       UTILITÁRIOS DE SEGURANÇA E FORMATAÇÃO
    ======================================================== */

    function escapeHtml(value) {

        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

    }


    function isFiniteNumber(value) {

        if (value === null || value === undefined || value === "") {
            return false;
        }

        const number = Number(value);

        return Number.isFinite(number);

    }


    function formatNumber(value, decimals) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return Number(value).toLocaleString(
            "pt-BR",
            {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }
        );

    }


    function formatInteger(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return Number(value).toLocaleString("pt-BR", {
            maximumFractionDigits: 0
        });

    }


    function formatTemperature(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 1)} °C`;

    }


    function formatMillimeters(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 1)} mm`;

    }


    function formatPercentage(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 1)} %`;

    }


    function formatPressure(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 1)} hPa`;

    }


    function formatWind(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 1)} km/h`;

    }


    function formatDegrees(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return `${formatNumber(value, 0)}°`;

    }


    function formatCoordinates(value) {

        if (!isFiniteNumber(value)) {
            return MISSING;
        }

        return Number(value).toFixed(4);

    }


    function formatDateTime(value) {

        if (!value) {
            return MISSING;
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return escapeHtml(value);
        }

        return date.toLocaleString("pt-BR", {
            dateStyle: "short",
            timeStyle: "short"
        });

    }


    function formatClock(value) {

        if (!value) {
            return MISSING;
        }

        const text = String(value).trim();

        if (!text) {
            return MISSING;
        }

        const date = new Date(text);

        if (Number.isNaN(date.getTime())) {
            return text;
        }

        return date.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit"
        });

    }


    function formatDaylight(seconds) {

        if (!isFiniteNumber(seconds)) {
            return MISSING;
        }

        const totalSeconds = Math.max(0, Math.round(Number(seconds)));
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);

        return `${hours}h ${String(minutes).padStart(2, "0")}min`;

    }


    function formatBoolean(value, trueLabel, falseLabel) {

        if (value === true || value === 1 || value === "true") {
            return trueLabel;
        }

        if (value === false || value === 0 || value === "false") {
            return falseLabel;
        }

        return MISSING;

    }


    function normalizeText(value) {

        if (value === null || value === undefined) {
            return "";
        }

        const text = String(value).trim();

        return text;

    }


    /* ========================================================
       LABELS DE APRESENTAÇÃO

       Estas tabelas somente traduzem valores recebidos para
       textos de interface. Não produzem decisões agroclimáticas.
    ======================================================== */

    const severityLabels = {
        none: "Sem risco",
        low: "Baixo",
        moderate: "Moderado",
        medium: "Moderado",
        high: "Alto",
        critical: "Crítico",
        baixo: "Baixo",
        moderado: "Moderado",
        medio: "Moderado",
        médio: "Moderado",
        alto: "Alto",
        critico: "Crítico",
        crítico: "Crítico"
    };


    const weatherConditionLabels = {
        CLEAR: "Céu limpo",
        MAINLY_CLEAR: "Predominantemente limpo",
        PARTLY_CLOUDY: "Parcialmente nublado",
        CLOUDY: "Nublado",
        FOG: "Neblina",
        RAIN: "Chuva",
        DRIZZLE: "Garoa",
        SNOW: "Neve",
        THUNDERSTORM: "Tempestade",
        SHOWERS: "Pancadas de chuva"
    };


    function formatSeverity(point) {

        if (!point) {
            return MISSING;
        }

        /*
         * CONTRATO CANÔNICO:
         *
         * Este campo representa exclusivamente a severidade do FRI.
         * A severidade de um alerta meteorológico é outro domínio e
         * não pode sobrescrever a severidade do indicador de risco
         * de geada.
         *
         * Portanto, a apresentação do FRI utiliza somente point.severity.
         */
        const raw = normalizeText(point.severity);

        if (!raw) {
            return MISSING;
        }

        return severityLabels[raw.toLowerCase()] || raw;

    }


    function formatWeatherCondition(value) {

        const raw = normalizeText(value);

        if (!raw) {
            return MISSING;
        }

        return weatherConditionLabels[raw.toUpperCase()] || raw;

    }


    function formatTemperatureClass(point) {

        if (!point) {
            return MISSING;
        }

        const label = normalizeText(point.temperature_class_label);

        if (label) {
            return label;
        }

        return MISSING;

    }


    function formatFri(point) {

        if (!point || !isFiniteNumber(point.fri)) {
            return MISSING;
        }

        return formatInteger(point.fri);

    }


    function formatConfidence(point) {

        if (!point || !isFiniteNumber(point.confidence)) {
            return MISSING;
        }

        return formatNumber(point.confidence, 2);

    }


    /* ========================================================
       ELEMENTOS VISUAIS DO POPUP — ETAPA 1

       Conceito visual alinhado à concepção aprovada:
       - cartão único;
       - cabeçalho limpo;
       - faixa de status;
       - grade principal em seis áreas;
       - resumo rápido;
       - rodapé técnico;
       - nenhuma informação é calculada aqui.

       A organização visual abaixo somente transforma o
       map_point canônico em uma apresentação compacta.
     ======================================================== */

    function buildHeader(point) {

        const nome =
            escapeHtml(
                normalizeText(point && point.nome) ||
                "Município"
            );

        const estado =
            escapeHtml(
                normalizeText(point && point.estado)
            );

        return `
            <div class="agroclima-popup-header">

                <div class="agroclima-popup-heading">

                    <div class="agroclima-popup-title">
                        ${nome} — ${estado}
                    </div>

                    <div class="agroclima-popup-subtitle">
                        Condição Agroclimática Atual
                    </div>

                </div>

                <div
                    class="agroclima-popup-close"
                    aria-hidden="true">
                    ×
                </div>

            </div>
        `;
    }


    function buildItem(label, value, extraClass) {

        const className =
            extraClass
                ? `agroclima-popup-item ${extraClass}`
                : "agroclima-popup-item";

        return `
            <div class="${className}">

                <span class="agroclima-popup-label">
                    ${escapeHtml(label)}
                </span>

                <span class="agroclima-popup-value">
                    ${escapeHtml(value)}
                </span>

            </div>
        `;
    }


    function buildCompactValue(label, value, extraClass) {

        const className =
            extraClass
                ? `agroclima-popup-compact-value ${extraClass}`
                : "agroclima-popup-compact-value";

        return `
            <div class="${className}">

                <span class="agroclima-popup-compact-label">
                    ${escapeHtml(label)}
                </span>

                <span class="agroclima-popup-compact-number">
                    ${escapeHtml(value)}
                </span>

            </div>
        `;
    }


    function buildStatusBadge(
        label,
        value,
        extraClass
    ) {

        const className =
            extraClass
                ? `agroclima-popup-status ${extraClass}`
                : "agroclima-popup-status";

        return `
            <div class="${className}">

                <span class="agroclima-popup-status-label">
                    ${escapeHtml(label)}
                </span>

                <span class="agroclima-popup-status-value">
                    ${escapeHtml(value)}
                </span>

            </div>
        `;
    }


    function buildStatusBar(point) {

        const thermal =
            formatTemperatureClass(point);

        const fri =
            formatFri(point);

        const severity =
            formatSeverity(point);

        const confidence =
            formatConfidence(point);

        return `
            <div class="agroclima-popup-status-bar">

                ${buildStatusBadge(
                    "Condição térmica",
                    thermal,
                    "thermal"
                )}

                ${buildStatusBadge(
                    "FRI",
                    fri,
                    "fri"
                )}

                ${buildStatusBadge(
                    "Severidade",
                    severity,
                    "severity"
                )}

                ${buildStatusBadge(
                    "Confiança",
                    confidence,
                    "confidence"
                )}

            </div>
        `;
    }


    function buildCard(
        title,
        content,
        iconClass,
        extraClass
    ) {

        const className =
            extraClass
                ? `agroclima-popup-card ${extraClass}`
                : "agroclima-popup-card";

        const icon =
            iconClass
                ? `
                    <span class="agroclima-popup-card-icon">
                        <i class="${escapeHtml(iconClass)}"></i>
                    </span>
                  `
                : "";

        return `
            <section class="${className}">

                <div class="agroclima-popup-card-header">

                    ${icon}

                    <span class="agroclima-popup-card-title">
                        ${escapeHtml(title)}
                    </span>

                </div>

                <div class="agroclima-popup-card-body">
                    ${content}
                </div>

            </section>
        `;
    }


    function buildThermalCard(point) {

        const temperature =
            formatTemperature(
                point && point.temperature
            );

        const classification =
            formatTemperatureClass(point);

        const fri =
            formatFri(point);

        const severity =
            formatSeverity(point);

        const confidence =
            formatConfidence(point);

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Temperatura",
                    temperature,
                    "primary"
                )}

                ${buildCompactValue(
                    "Classificação",
                    classification,
                    "primary"
                )}

            </div>

            <div class="agroclima-popup-three-columns">

                ${buildCompactValue(
                    "FRI",
                    fri,
                    "decision"
                )}

                ${buildCompactValue(
                    "Severidade",
                    severity,
                    "decision"
                )}

                ${buildCompactValue(
                    "Confiança",
                    confidence,
                    "decision"
                )}

            </div>
        `;

        return buildCard(
            "Condição térmica",
            content,
            "bi bi-thermometer-half",
            "thermal-card"
        );
    }


    function getAccumulatedPrecipitation(point) {

        if (!point) {
            return null;
        }

        // Contrato canônico: o acumulado disponível exibido no popup
        // corresponde ao mesmo acumulado oficial das últimas 24 horas.
        // Não consultar campos paralelos nem criar uma segunda janela
        // temporal no frontend.
        return point.precipitation_24h_mm ?? null;
    }


    function buildPrecipitationCard(point) {

        const accumulated =
            getAccumulatedPrecipitation(point);

        const precipitation1h =
            formatMillimeters(
                point && point.precipitation_1h_mm
            );

        const precipitation24h =
            formatMillimeters(
                point && point.precipitation_24h_mm
            );

        /*
         * A classificação pluviométrica é produzida exclusivamente
         * pelo backend. Este módulo apenas apresenta o rótulo recebido.
         */
        const precipitation24hClassLabel =
            point && point.precipitation_24h_class_label
                ? point.precipitation_24h_class_label
                : MISSING;

        const accumulatedText =
            formatMillimeters(accumulated);

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "1h",
                    precipitation1h
                )}

                ${buildCompactValue(
                    "24h",
                    precipitation24h
                )}

            </div>

            ${buildItem(
                "Classificação 24h",
                precipitation24hClassLabel,
                "compact-full"
            )}

            ${buildItem(
                "Acumulado disponível",
                accumulatedText,
                "compact-full"
            )}
        `;

        return buildCard(
            "Precipitação",
            content,
            "bi bi-cloud-rain",
            "precipitation-card"
        );
    }


    function buildMeteorologyCard(point) {

        const humidity =
            formatPercentage(
                point && point.humidity
            );

        const pressure =
            formatPressure(
                point && point.pressure
            );

        const cloudCover =
            formatPercentage(
                point && point.cloud_cover
            );

        const condition =
            formatWeatherCondition(
                point && point.weather_condition
            );

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Umidade",
                    humidity,
                    "primary"
                )}

                ${buildCompactValue(
                    "Pressão",
                    pressure,
                    "primary"
                )}

            </div>

            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Nebulosidade",
                    cloudCover
                )}

                ${buildCompactValue(
                    "Condição do tempo",
                    condition
                )}

            </div>
        `;

        return buildCard(
            "Meteorologia",
            content,
            "bi bi-wind",
            "meteorology-card"
        );
    }


    function buildWindCard(point) {

        const wind =
            formatWind(
                point && point.wind_speed
            );

        const direction =
            formatDegrees(
                point && point.wind_direction
            );

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Velocidade",
                    wind,
                    "primary"
                )}

                ${buildCompactValue(
                    "Direção",
                    direction,
                    "primary"
                )}

            </div>
        `;

        return buildCard(
            "Vento",
            content,
            "bi bi-wind",
            "wind-card"
        );
    }


    function buildEnvironmentCard(point) {

        const uv =
            formatNumber(
                point && point.uv_index_max,
                1
            );

        const sunrise =
            formatClock(
                point && point.sunrise
            );

        const sunset =
            formatClock(
                point && point.sunset
            );

        const daylight =
            formatDaylight(
                point && point.daylight_duration_seconds
            );

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Índice UV máximo",
                    uv
                )}

                ${buildCompactValue(
                    "Duração do dia",
                    daylight
                )}

            </div>

            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Nascer do sol",
                    sunrise
                )}

                ${buildCompactValue(
                    "Pôr do sol",
                    sunset
                )}

            </div>
        `;

        return buildCard(
            "Ambiente",
            content,
            "bi bi-leaf",
            "environment-card"
        );
    }


    function buildLocationCard(point) {

        const altitude =
            isFiniteNumber(
                point && point.altitude
            )
                ? `${formatNumber(point.altitude, 0)} m`
                : MISSING;

        const latitude =
            formatCoordinates(
                point && point.latitude
            );

        const longitude =
            formatCoordinates(
                point && point.longitude
            );

        const coordinates =
            latitude !== MISSING &&
            longitude !== MISSING
                ? `${latitude}, ${longitude}`
                : MISSING;

        const content = `
            ${buildItem(
                "Coordenadas",
                coordinates,
                "compact-full"
            )}

            ${buildItem(
                "Altitude",
                altitude,
                "compact-full"
            )}
        `;

        return buildCard(
            "Localização",
            content,
            "bi bi-geo-alt",
            "location-card"
        );
    }


    function buildQuickSummary(point) {

        const temperature =
            formatTemperature(
                point && point.temperature
            );

        const precipitation =
            formatMillimeters(
                point && point.precipitation_24h_mm
            );

        const wind =
            formatWind(
                point && point.wind_speed
            );

        const humidity =
            formatPercentage(
                point && point.humidity
            );

        const pressure =
            formatPressure(
                point && point.pressure
            );

        const condition =
            formatWeatherCondition(
                point && point.weather_condition
            );

        const content = `
            <div class="agroclima-popup-summary-grid">

                ${buildCompactValue(
                    "Temperatura",
                    temperature,
                    "primary"
                )}

                ${buildCompactValue(
                    "Chuva (24h)",
                    precipitation
                )}

                ${buildCompactValue(
                    "Vento",
                    wind
                )}

                ${buildCompactValue(
                    "Umidade",
                    humidity
                )}

                ${buildCompactValue(
                    "Pressão",
                    pressure
                )}

                ${buildCompactValue(
                    "Condição",
                    condition
                )}

            </div>
        `;

        return buildCard(
            "Resumo rápido",
            content,
            "bi bi-clipboard2-check",
            "summary-card"
        );
    }


    /* ========================================================
       RODAPÉ TÉCNICO

       O rodapé apresenta apenas metadados já existentes no
       map_point. Nenhuma informação é inferida ou calculada.
     ======================================================== */

    function buildTechnicalFooter(point) {

        if (!point) {
            return "";
        }

        const altitude =
            isFiniteNumber(
                point.altitude
            )
                ? `${formatNumber(point.altitude, 0)} m`
                : MISSING;

        const latitude =
            formatCoordinates(
                point.latitude
            );

        const longitude =
            formatCoordinates(
                point.longitude
            );

        const coordinates =
            latitude !== MISSING &&
            longitude !== MISSING
                ? `${latitude}, ${longitude}`
                : MISSING;

        const retrieved =
            formatDateTime(
                point.retrieved_at
            );

        const observed =
            formatDateTime(
                point.observed_at
            );

        const source =
            normalizeText(
                point.source
            );

        const quality =
            normalizeText(
                point.quality_status
            );

        const technicalItems = [];

        technicalItems.push(
            buildCompactValue(
                "Altitude",
                altitude,
                "footer-value"
            )
        );

        technicalItems.push(
            buildCompactValue(
                "Coordenadas",
                coordinates,
                "footer-value"
            )
        );

        technicalItems.push(
            buildCompactValue(
                "Atualizado em",
                retrieved,
                "footer-value"
            )
        );

        if (observed !== MISSING) {
            technicalItems.push(
                buildCompactValue(
                    "Observado em",
                    observed,
                    "footer-value"
                )
            );
        }

        if (quality) {
            technicalItems.push(
                buildCompactValue(
                    "Qualidade",
                    quality,
                    "footer-value"
                )
            );
        }

        if (source) {
            technicalItems.push(
                buildCompactValue(
                    "Fonte",
                    source,
                    "footer-value"
                )
            );
        }

        return `
            <div class="agroclima-popup-footer">

                ${technicalItems.join("")}

            </div>
        `;
    }


    /* ========================================================
       CONTRATO VISUAL

       A grade mantém seis áreas informativas compactas:

       1. Condição térmica
       2. Precipitação
       3. Meteorologia
       4. Ambiente
       5. Localização
       6. Resumo rápido

       A ordem segue a concepção visual aprovada e não altera
       o significado nem a origem dos dados.
     ======================================================== */

    function buildMainGrid(point) {

        return `
            <div class="agroclima-popup-main-grid">

                ${buildThermalCard(point)}

                ${buildPrecipitationCard(point)}

                ${buildMeteorologyCard(point)}

                ${buildWindCard(point)}

                ${buildEnvironmentCard(point)}

                ${buildLocationCard(point)}

            </div>
        `;
    }


    /* ========================================================
       METADADOS DE OBSERVAÇÃO

       Mantido como função interna para compatibilidade com
       versões anteriores do módulo. A apresentação principal
       utiliza o rodapé técnico.
     ======================================================== */

    function buildObservationMeta(point) {

        if (!point) {
            return "";
        }

        const observed =
            formatDateTime(
                point.observed_at
            );

        const retrieved =
            formatDateTime(
                point.retrieved_at
            );

        const quality =
            normalizeText(
                point.quality_status
            );

        const source =
            normalizeText(
                point.source
            );

        const hasObserved =
            observed !== MISSING;

        const hasRetrieved =
            retrieved !== MISSING;

        const hasQuality =
            Boolean(quality);

        const hasSource =
            Boolean(source);

        if (
            !hasObserved &&
            !hasRetrieved &&
            !hasQuality &&
            !hasSource
        ) {
            return "";
        }

        return `
            <div class="agroclima-popup-meta">

                ${hasObserved
                    ? buildItem(
                        "Observado em",
                        observed
                    )
                    : ""}

                ${hasRetrieved
                    ? buildItem(
                        "Atualizado em",
                        retrieved
                    )
                    : ""}

                ${hasQuality
                    ? buildItem(
                        "Qualidade",
                        quality
                    )
                    : ""}

                ${hasSource
                    ? buildItem(
                        "Fonte",
                        source
                    )
                    : ""}

            </div>
        `;
    }


    /* ========================================================
       POPUPS ESPECÍFICOS POR CAMADA

       A camada ativa define somente a apresentação dos dados.
       O map_point continua sendo a única fonte de valores.
       Nenhuma regra agroclimática é calculada neste módulo.
    ======================================================== */

    function buildScenarioHeader(point, subtitle) {

        const nome =
            escapeHtml(
                normalizeText(point && point.nome) ||
                "Município"
            );

        const estado =
            escapeHtml(
                normalizeText(point && point.estado)
            );

        return `
            <div class="agroclima-popup-header">

                <div class="agroclima-popup-heading">

                    <div class="agroclima-popup-title">
                        ${nome} — ${estado}
                    </div>

                    <div class="agroclima-popup-subtitle">
                        ${escapeHtml(subtitle)}
                    </div>

                </div>

                <div
                    class="agroclima-popup-close"
                    aria-hidden="true">
                    ×
                </div>

            </div>
        `;
    }


    function buildGeadasPopup(point) {

        const frostStatus =
            point && point.frost
                ? "Registro de geada"
                : "Sem registro de geada";

        const occurrences =
            isFiniteNumber(point && point.frost_occurrences)
                ? formatInteger(point.frost_occurrences)
                : MISSING;

        const lastDate =
            formatDateTime(
                point && point.frost_last_date
            );

        const minimum =
            formatTemperature(
                point && point.frost_temperature_minimum
            );

        const historicalDays =
            isFiniteNumber(point && point.historical_frost_days)
                ? formatInteger(point.historical_frost_days)
                : MISSING;

        const historicalTotal =
            isFiniteNumber(point && point.historical_total_days)
                ? formatInteger(point.historical_total_days)
                : MISSING;

        const frequency =
            formatPercentage(
                isFiniteNumber(point && point.historical_frost_frequency)
                    ? Number(point.historical_frost_frequency)
                    : null
            );

        const episodes =
            isFiniteNumber(point && point.historical_frost_episodes)
                ? formatInteger(point.historical_frost_episodes)
                : MISSING;

        const factors =
            Array.isArray(point && point.frost_factors) &&
            point.frost_factors.length
                ? point.frost_factors
                    .map(item => escapeHtml(item))
                    .join(", ")
                : MISSING;

        const content = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Situação",
                    frostStatus,
                    "primary"
                )}

                ${buildCompactValue(
                    "Ocorrências",
                    occurrences,
                    "decision"
                )}

            </div>
        `;

        const historicalContent = `
            <div class="agroclima-popup-three-columns">

                ${buildCompactValue(
                    "Dias com geada",
                    historicalDays
                )}

                ${buildCompactValue(
                    "Episódios",
                    episodes
                )}

                ${buildCompactValue(
                    "Frequência",
                    frequency
                )}

            </div>
        `;

        const lastContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Última ocorrência",
                    lastDate
                )}

                ${buildCompactValue(
                    "Mínima registrada",
                    minimum,
                    "primary"
                )}

            </div>
        `;

        const riskContent = `
            <div class="agroclima-popup-three-columns">

                ${buildCompactValue(
                    "FRI",
                    formatFri(point),
                    "decision"
                )}

                ${buildCompactValue(
                    "Severidade",
                    formatSeverity(point),
                    "decision"
                )}

                ${buildCompactValue(
                    "Confiança",
                    formatConfidence(point),
                    "decision"
                )}

            </div>
        `;

        const currentContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Temperatura",
                    formatTemperature(point && point.temperature),
                    "primary"
                )}

                ${buildCompactValue(
                    "Umidade",
                    formatPercentage(point && point.humidity)
                )}

            </div>
        `;

        const factorsCard = buildCard(
            "Fatores associados",
            `<div class="agroclima-popup-scenario-text">${factors}</div>`,
            "bi bi-list-check",
            "factors-card"
        );

        return `
            <div class="agroclima-popup agroclima-popup-scenario-geadas">

                ${buildScenarioHeader(
                    point,
                    "Monitoramento de Geadas"
                )}

                <div class="agroclima-popup-main-grid">
                    ${buildCard("Situação da geada", content, "bi bi-snow2", "frost-status-card")}
                    ${buildCard("Histórico de geadas", historicalContent, "bi bi-calendar3", "frost-history-card")}
                    ${buildCard("Última referência", lastContent, "bi bi-thermometer-snow", "frost-last-card")}
                    ${buildCard("Risco agroclimático", riskContent, "bi bi-shield-exclamation", "frost-risk-card")}
                    ${buildCard("Condição atual", currentContent, "bi bi-cloud-sun", "frost-current-card")}
                    ${factorsCard}
                </div>

            </div>
        `;
    }


    function buildTemperaturaPopup(point) {

        const thermalContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Temperatura atual",
                    formatTemperature(point && point.temperature),
                    "primary"
                )}

                ${buildCompactValue(
                    "Classificação",
                    formatTemperatureClass(point),
                    "primary"
                )}

            </div>
        `;

        const apparentContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Temperatura aparente",
                    formatTemperature(point && point.apparent_temperature)
                )}

                ${buildCompactValue(
                    "Ponto de orvalho",
                    formatTemperature(point && point.dew_point)
                )}

            </div>
        `;

        const humidityContent = `
            ${buildCompactValue(
                "Umidade relativa",
                formatPercentage(point && point.humidity),
                "compact-full primary"
            )}
        `;

        const skyContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Nebulosidade",
                    formatPercentage(point && point.cloud_cover)
                )}

                ${buildCompactValue(
                    "Condição",
                    formatWeatherCondition(point && point.weather_condition)
                )}

            </div>
        `;

        const windContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Velocidade",
                    formatWind(point && point.wind_speed)
                )}

                ${buildCompactValue(
                    "Direção",
                    formatDegrees(point && point.wind_direction)
                )}

            </div>
        `;

        return `
            <div class="agroclima-popup agroclima-popup-scenario-temperatura">

                ${buildScenarioHeader(
                    point,
                    "Monitoramento de Temperatura"
                )}

                <div class="agroclima-popup-main-grid">
                    ${buildCard("Condição térmica", thermalContent, "bi bi-thermometer-half", "thermal-card")}
                    ${buildCard("Sensação térmica", apparentContent, "bi bi-thermometer-sun", "temperature-apparent-card")}
                    ${buildCard("Umidade", humidityContent, "bi bi-droplet", "temperature-humidity-card")}
                    ${buildCard("Condição do céu", skyContent, "bi bi-cloud-sun", "temperature-sky-card")}
                    ${buildCard("Vento", windContent, "bi bi-wind", "temperature-wind-card")}
                    ${buildLocationCard(point)}
                </div>

            </div>
        `;
    }


    function buildPrecipitacaoPopup(point) {

        const rainNow =
            point && point.rain_now === true
                ? "Chuva agora"
                : point && point.rain_now === false
                    ? "Sem chuva agora"
                    : MISSING;

        const precipitation24hClassLabel =
            point && point.precipitation_24h_class_label
                ? point.precipitation_24h_class_label
                : MISSING;

        const precipitationContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Última hora",
                    formatMillimeters(point && point.precipitation_1h_mm),
                    "primary"
                )}

                ${buildCompactValue(
                    "Últimas 24h",
                    formatMillimeters(point && point.precipitation_24h_mm),
                    "primary"
                )}

            </div>

            ${buildCompactValue(
                "Classificação 24h",
                precipitation24hClassLabel,
                "compact-full"
            )}
        `;

        const rainContent = `
            ${buildCompactValue(
                "Situação atual",
                rainNow,
                "compact-full"
            )}
        `;

        const conditionContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Nebulosidade",
                    formatPercentage(point && point.cloud_cover)
                )}

                ${buildCompactValue(
                    "Condição",
                    formatWeatherCondition(point && point.weather_condition)
                )}

            </div>
        `;

        const humidityContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Umidade",
                    formatPercentage(point && point.humidity)
                )}

                ${buildCompactValue(
                    "Pressão",
                    formatPressure(point && point.pressure)
                )}

            </div>
        `;

        const windContent = `
            <div class="agroclima-popup-two-columns">

                ${buildCompactValue(
                    "Velocidade",
                    formatWind(point && point.wind_speed)
                )}

                ${buildCompactValue(
                    "Direção",
                    formatDegrees(point && point.wind_direction)
                )}

            </div>
        `;

        /*
         * O acumulado pluviométrico oficial disponível no contrato
         * municipal é precipitation_24h_mm.
         *
         * A popup não cria um segundo campo de acumulado.
         * Ela somente apresenta o valor oficial recebido do backend.
         */
        const accumulated =
            formatMillimeters(
                point && point.precipitation_24h_mm
            );

        return `
            <div class="agroclima-popup agroclima-popup-scenario-precipitacao">

                ${buildScenarioHeader(
                    point,
                    "Monitoramento de Precipitação"
                )}

                <div class="agroclima-popup-main-grid">
                    ${buildCard("Precipitação", precipitationContent, "bi bi-cloud-rain", "precipitation-card")}
                    ${buildCard("Chuva agora", rainContent, "bi bi-cloud-drizzle", "rain-now-card")}
                    ${buildCard("Condição meteorológica", conditionContent, "bi bi-cloud-sun", "precipitation-condition-card")}
                    ${buildCard("Umidade e pressão", humidityContent, "bi bi-droplet-half", "precipitation-atmosphere-card")}
                    ${buildCard("Vento", windContent, "bi bi-wind", "precipitation-wind-card")}
                    ${buildCard("Acumulado 24h", buildCompactValue("Acumulado", accumulated, "compact-full"), "bi bi-cloud-rain-heavy", "precipitation-accumulated-card")}
                </div>

            </div>
        `;
    }


    function buildMunicipiosPopup(point) {

        return `
            <div class="agroclima-popup agroclima-popup-scenario-municipios">

                ${buildHeader(point)}

                ${buildMainGrid(point)}

            </div>
        `;
    }


    /* ========================================================
       CONTRATO PÚBLICO

       v1.3.0: a camada ativa seleciona a apresentação do popup.
       municipios mantém os seis cards aprovados; geadas, temperatura
       e precipitacao recebem estruturas específicas e não reutilizam
       informações de cenários que não lhes pertencem.
    ======================================================== */

    function build(point, activeLayer) {

        if (!point || typeof point !== "object") {

            return `
                <div class="agroclima-popup">

                    <div class="agroclima-popup-header">

                        <div class="agroclima-popup-heading">

                            <div class="agroclima-popup-title">
                                Município
                            </div>

                            <div class="agroclima-popup-subtitle">
                                Condição Agroclimática Atual
                            </div>

                        </div>

                    </div>

                    <div class="agroclima-popup-empty">
                        Dados municipais não disponíveis.
                    </div>

                </div>
            `;
        }

        const layer =
            normalizeText(activeLayer).toLowerCase() ||
            "municipios";

        if (layer === "geadas") {
            return buildGeadasPopup(point);
        }

        if (layer === "temperatura") {
            return buildTemperaturaPopup(point);
        }

        if (layer === "precipitacao") {
            return buildPrecipitacaoPopup(point);
        }

        return buildMunicipiosPopup(point);
    }


    function getName() {
        return MODULE_NAME;
    }


    window[MODULE_NAME] = {
        build,
        getName,
        version: "1.3.0",
        missingLabel: MISSING
    };


    /* ========================================================
       TESTE ETAPA 2 — POPUP COM SEIS CARTÕES FIXOS

       Renderização prevista:
       - linha 1: condição térmica | precipitação | meteorologia;
       - linha 2: vento | ambiente | localização;
       - sem resumo rápido na composição final;
       - sem faixa de status na composição final;
       - sem rodapé técnico na composição final;
       - nenhum recálculo de dados ou indicadores.
     ======================================================== */


    /* ========================================================
       DIAGNÓSTICO CONTROLADO
    ======================================================== */

    if (window.console && typeof window.console.info === "function") {

        window.console.info(
            "[AGROCLIMA] Módulo de popup municipal carregado."
        );

    }


})(window);


/* ============================================================
   AUDITORIA ETAPA 1 — CARTÃO MUNICIPAL ALINHADO

   Arquitetura:
   - recebe somente map_point;
   - não consulta API;
   - não consulta banco;
   - não recalcula FRI;
   - não recalcula severidade;
   - não recalcula classificação térmica;
   - não cria indicador agroclimático;
   - mantém comportamento seguro para ausência de dados.

   Apresentação:
   - cabeçalho;
   - grade principal 3 x 2;
   - seis cartões fixos: condição térmica, precipitação,
     meteorologia, vento, ambiente e localização;
   - resumo rápido não é renderizado;
   - faixa de status não é renderizada;
   - rodapé técnico não é renderizado;
   - formatação pt-BR;
   - escaping HTML preservado.

   Teste de composição:
   - linha 1: condição térmica | precipitação | meteorologia;
   - linha 2: vento | ambiente | localização;
   - vento possui cartão próprio, sem duplicação em meteorologia;
   - o conteúdo reduzido tem como objetivo diminuir a área total
     ocupada pelo popup sobre o mapa.

   Compatibilidade:
   - severity = "none" é apresentado como "Sem risco";
   - a severidade do alerta não sobrescreve a severidade canônica do FRI;
   - AgroClimaMunicipalPopup.build permanece a API pública;
   - buildObservationMeta permanece disponível internamente;
   - campos do map_point permanecem os mesmos;
   - precipitation_accumulated_mm continua opcional;
   - nenhuma classificação é duplicada no frontend.

   Regra de entrega:
   - esta versão mantém ou supera a quantidade de linhas
     do arquivo original auditado.
============================================================ */

/* ============================================================
   AUDITORIA — CORREÇÃO DO ACUMULADO PLUVIOMÉTRICO

   Correção:
   - elimina a dependência de precipitation_accumulated_mm;
   - utiliza precipitation_24h_mm, campo oficial do map_point;
   - não calcula precipitação no frontend;
   - não cria indicador agroclimático;
   - mantém a popup como camada de apresentação.

   Cadeia:
   Open-Meteo → WeatherDTO → DashboardService →
   AgroClimateIndicatorService → map_point →
   AgroClimaMunicipalPopup → apresentação.

   Resultado:
   - "Últimas 24h" mostra precipitation_24h_mm;
   - "Acumulado 24h" mostra o mesmo valor oficial;
   - se o backend fornecer 14,6 mm, ambos apresentarão 14,6 mm;
   - "Não disponível" somente aparece quando o backend realmente
     não fornecer precipitation_24h_mm.

   Integridade do arquivo:
   - versão original auditada: 1880 linhas;
   - versão corrigida: quantidade igual ou superior;
   - nenhuma alteração realizada na lógica do backend.
============================================================ */


/* ============================================================
   AUDITORIA — CORREÇÃO DO ACUMULADO DISPONÍVEL

   Correção aplicada:
   - "Acumulado disponível" utiliza exclusivamente
     precipitation_24h_mm;
   - o valor é o mesmo acumulado oficial de 24 horas já exibido
     pelo cartão "24h";
   - campos precipitation_accumulated_mm e
     precipitacao_acumulada_mm deixam de participar desta apresentação;
   - nenhuma precipitação é calculada no frontend;
   - ausência permanece como "Não disponível" por meio do contrato
     existente de formatação.

   Cadeia preservada:
   Fonte → Provider → DTO → Persistência → Indicadores → map_point
   → Popup municipal → apresentação.

   Resultado esperado para Águas da Prata:
   24h = 21,2 mm
   Acumulado disponível = 21,2 mm

   FRI e severidade permanecem independentes da precipitação.
============================================================ */
