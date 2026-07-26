/* ==========================================================
   AGROCLIMA CAFÉ
   Dashboard V3
   Parte 1
   ========================================================== */

"use strict";

/* ==========================================================
   CONFIGURAÇÕES
========================================================== */

const Dashboard = {

    config:{

        refreshInterval:300000, // 5 minutos

        animationDuration:600

    },

    chart:null,

    map:null,

    markers:[],

    initialized:false,

    /* ======================================================
       INICIALIZAÇÃO
    ====================================================== */

    init(){

        if(this.initialized){

            return;

        }

        console.log("Dashboard V3 iniciada.");

        this.cache();

        this.bindEvents();

        this.animateCards();

        this.highlightButtons();

        this.startClock();

        this.initialized=true;

    },

    /* ======================================================
       CACHE DOS ELEMENTOS
    ====================================================== */

    cache(){

        this.periodButtons=document.querySelectorAll(".btn-panel");

        this.kpiCards=document.querySelectorAll(".kpi-card");

        this.dashboardPanels=document.querySelectorAll(".dashboard-panel");

        this.chartCanvas=document.getElementById("weatherChart");

        this.mapContainer=document.getElementById("map-container");

    },

    /* ======================================================
       EVENTOS
    ====================================================== */

    bindEvents(){

        this.periodButtons.forEach(button=>{

            button.addEventListener("click",(event)=>{

                this.changePeriod(event);

            });

        });

        window.addEventListener("resize",()=>{

            this.onResize();

        });

    },

    /* ======================================================
       ALTERAÇÃO DE PERÍODO
    ====================================================== */

    changePeriod(event){

        this.periodButtons.forEach(btn=>{

            btn.classList.remove("active");

        });

        event.target.classList.add("active");

        const period=event.target.textContent.trim();

        console.log("Período:",period);

        this.loadDashboard(period);

    },

    /* ======================================================
       CARREGAMENTO
    ====================================================== */

    loadDashboard(period){

        console.log("Carregando Dashboard:",period);

        /*
            Futuramente:

            fetch("/dashboard/api?period="+period)

            .then()

            atualizar KPIs

            atualizar gráfico

            atualizar mapa

            atualizar ranking

            atualizar alertas

        */

    },

    /* ======================================================
       ANIMAÇÕES
    ====================================================== */

    animateCards(){

        this.kpiCards.forEach((card,index)=>{

            card.style.opacity="0";

            card.style.transform="translateY(20px)";

            setTimeout(()=>{

                card.style.transition=".5s";

                card.style.opacity="1";

                card.style.transform="translateY(0)";

            },index*120);

        });

    },

    /* ======================================================
       HOVER
    ====================================================== */

    highlightButtons(){

        this.dashboardPanels.forEach(panel=>{

            panel.addEventListener("mouseenter",()=>{

                panel.style.boxShadow="0 14px 28px rgba(0,0,0,.12)";

            });

            panel.addEventListener("mouseleave",()=>{

                panel.style.boxShadow="";

            });

        });

    },

    /* ======================================================
       RELÓGIO
    ====================================================== */

    startClock(){

        setInterval(()=>{

            console.log("Dashboard ativa.");

        },this.config.refreshInterval);

    },

    /* ======================================================
       REDIMENSIONAMENTO
    ====================================================== */

    onResize(){

        if(this.chart){

            this.chart.resize();

        }

        if(this.map){

            this.map.invalidateSize();

        }

    }

};

/* ==========================================================
   UTILITÁRIOS
========================================================== */

const Utils={

    formatNumber(value){

        return new Intl.NumberFormat("pt-BR").format(value);

    },

    formatDecimal(value){

        return new Intl.NumberFormat(

            "pt-BR",

            {

                minimumFractionDigits:1,

                maximumFractionDigits:1

            }

        ).format(value);

    },

    formatDate(date){

        return new Intl.DateTimeFormat(

            "pt-BR",

            {

                day:"2-digit",

                month:"2-digit",

                year:"numeric"

            }

        ).format(date);

    },

    formatHour(date){

        return new Intl.DateTimeFormat(

            "pt-BR",

            {

                hour:"2-digit",

                minute:"2-digit"

            }

        ).format(date);

    }

};

/* ==========================================================
   DOM READY
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    ()=>{

        Dashboard.init();

    }

);
/* ==========================================================
   CHART CONTROLLER
   Dashboard V3
   Parte 2
========================================================== */

const ChartController = {

    chart: null,

    /* ======================================================
       INICIALIZAÇÃO
    ====================================================== */

    init() {

        if (!Dashboard.chartCanvas) {

            console.warn("Canvas do gráfico não encontrado.");

            return;

        }

        const dias = this.getJson("chart-dias");

        const temperatura = this.getJson("chart-temperatura");

        const precipitacao = this.getJson("chart-precipitacao");

        this.createChart(dias, temperatura, precipitacao);

    },

    /* ======================================================
       LER JSON DO DJANGO
    ====================================================== */

    getJson(id) {

        const element = document.getElementById(id);

        if (!element) {

            return [];

        }

        try {

            return JSON.parse(element.textContent);

        }

        catch (error) {

            console.error(error);

            return [];

        }

    },

    /* ======================================================
       CRIAR GRÁFICO
    ====================================================== */

    createChart(labels, temperatura, precipitacao) {

        if (this.chart) {

            this.chart.destroy();

        }

        this.chart = new Chart(

            Dashboard.chartCanvas,

            {

                type: "line",

                data: {

                    labels: labels,

                    datasets: [

                        {

                            label: "Temperatura (°C)",

                            data: temperatura,

                            tension: .35,

                            borderWidth: 3,

                            fill: false,

                            yAxisID: "y"

                        },

                        {

                            label: "Precipitação (mm)",

                            data: precipitacao,

                            tension: .35,

                            borderWidth: 3,

                            fill: false,

                            yAxisID: "y1"

                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {

                        intersect: false,

                        mode: "index"

                    },

                    plugins: {

                        legend: {

                            position: "top"

                        }

                    },

                    scales: {

                        y: {

                            beginAtZero: false,

                            title: {

                                display: true,

                                text: "Temperatura"

                            }

                        },

                        y1: {

                            position: "right",

                            beginAtZero: true,

                            grid: {

                                drawOnChartArea: false

                            },

                            title: {

                                display: true,

                                text: "Precipitação"

                            }

                        }

                    }

                }

            }

        );

        Dashboard.chart = this.chart;

    },

    /* ======================================================
       ATUALIZAÇÃO
    ====================================================== */

    update(labels, temperatura, precipitacao) {

        if (!this.chart) {

            this.createChart(

                labels,

                temperatura,

                precipitacao

            );

            return;

        }

        this.chart.data.labels = labels;

        this.chart.data.datasets[0].data = temperatura;

        this.chart.data.datasets[1].data = precipitacao;

        this.chart.update();

    },

    /* ======================================================
       ALTERAR PERÍODO
    ====================================================== */

    changePeriod(period) {

        console.log("Atualizando gráfico:", period);

        /*
            Futuramente:

            fetch()

            receber novos dados

            this.update(...)
        */

    }

};

/* ==========================================================
   INTEGRAÇÃO COM DASHBOARD
========================================================== */

const originalLoadDashboard = Dashboard.loadDashboard.bind(Dashboard);

Dashboard.loadDashboard = function (period) {

    originalLoadDashboard(period);

    ChartController.changePeriod(period);

};

/* ==========================================================
   INICIALIZAÇÃO
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        ChartController.init();

    }

);
/* ==========================================================
   AGROCLIMA CAFÉ
   Dashboard V3
   Parte 3
==========================================================*/

/* ==========================================================
   MAP CONTROLLER
==========================================================*/

const MapController = {

    initialized: false,

    init() {

        if (!Dashboard.mapContainer) {

            return;

        }

        if (typeof L === "undefined") {

            console.warn("Leaflet não carregado.");

            return;

        }

        Dashboard.map = L.map("map-container", {

            zoomControl: true

        }).setView([-21.97, -46.79], 9);

        L.tileLayer(

            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",

            {

                maxZoom: 19,

                attribution: "&copy; OpenStreetMap"

            }

        ).addTo(Dashboard.map);

        this.initialized = true;

    },

    updateMarkers(points = []) {

        if (!this.initialized) {

            return;

        }

        Dashboard.markers.forEach(marker => {

            Dashboard.map.removeLayer(marker);

        });

        Dashboard.markers = [];

        points.forEach(point => {

            const marker = L.marker([

                point.latitude,

                point.longitude

            ])

            .bindPopup(

                `<strong>${point.nome}</strong><br>${point.descricao}`

            )

            .addTo(Dashboard.map);

            Dashboard.markers.push(marker);

        });

    }

};

/* ==========================================================
   KPI CONTROLLER
==========================================================*/

const KPIController = {

    update(kpis = {}) {

        Object.keys(kpis).forEach(id => {

            const element = document.querySelector(

                `[data-kpi="${id}"]`

            );

            if (!element) {

                return;

            }

            element.textContent = kpis[id];

        });

    }

};

/* ==========================================================
   ALERT CONTROLLER
==========================================================*/

const AlertController = {

    notify(message, type = "info") {

        console.log(

            `[${type.toUpperCase()}] ${message}`

        );

        /*
            Futuramente:

            Toast Bootstrap

            SweetAlert2

            Notificações Web

        */

    }

};

/* ==========================================================
   AUTO REFRESH
==========================================================*/

Dashboard.refresh = function () {

    console.log("Atualizando Dashboard...");

    /*
        Futuramente:

        fetch("/dashboard/api")

        atualizar:

        KPIs

        gráfico

        ranking

        alertas

        mapa

    */

};

Dashboard.autoRefresh = function () {

    setInterval(

        () => {

            this.refresh();

        },

        this.config.refreshInterval

    );

};

/* ==========================================================
   INICIALIZAÇÃO GERAL
==========================================================*/

document.addEventListener(

    "DOMContentLoaded",

    () => {

        MapController.init();

        Dashboard.autoRefresh();

    }

);