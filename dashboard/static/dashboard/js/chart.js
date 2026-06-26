/*
==========================================================
AgroClima Café
Dashboard V3
Chart.js
==========================================================
*/

document.addEventListener("DOMContentLoaded", () => {

    initializeWeatherChart();

});

function initializeWeatherChart() {

    const canvas = document.getElementById("weatherChart");

    if (!canvas) {

        return;

    }

    const diasElement = document.getElementById("chart-dias");
    const temperaturaElement = document.getElementById("chart-temperatura");
    const precipitacaoElement = document.getElementById("chart-precipitacao");

    if (!diasElement || !temperaturaElement || !precipitacaoElement) {

        console.warn("Dados do gráfico não encontrados.");

        return;

    }

    const dias = JSON.parse(diasElement.textContent);

    const temperatura = JSON.parse(temperaturaElement.textContent);

    const precipitacao = JSON.parse(precipitacaoElement.textContent);

    new Chart(canvas, {

        type: "line",

        data: {

            labels: dias,

            datasets: [

                {

                    label: "Temperatura Média",

                    data: temperatura,

                    yAxisID: "temperature",

                    borderColor: "#A86A2C",

                    backgroundColor: "rgba(168,106,44,0.12)",

                    borderWidth: 3,

                    pointRadius: 5,

                    pointHoverRadius: 7,

                    pointBorderWidth: 2,

                    fill: true,

                    tension: .35

                },

                {

                    label: "Precipitação",

                    data: precipitacao,

                    yAxisID: "rain",

                    borderColor: "#1D7F95",

                    backgroundColor: "rgba(29,127,149,0.12)",

                    borderWidth: 3,

                    pointRadius: 5,

                    pointHoverRadius: 7,

                    pointBorderWidth: 2,

                    fill: true,

                    tension: .35

                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            animation: {

                duration: 1200

            },

            interaction: {

                mode: "index",

                intersect: false

            },

            plugins: {

                legend: {

                    position: "bottom",

                    labels: {

                        usePointStyle: true,

                        padding: 25,

                        font: {

                            size: 13,

                            weight: "600"

                        }

                    }

                },

                tooltip: {

                    backgroundColor: "#FFFFFF",

                    titleColor: "#333333",

                    bodyColor: "#444444",

                    borderColor: "#DDDDDD",

                    borderWidth: 1,

                    displayColors: true,

                    padding: 12

                }

            },

            scales: {

                x: {

                    grid: {

                        display: false

                    }

                },

                temperature: {

                    type: "linear",

                    position: "left",

                    beginAtZero: false,

                    title: {

                        display: true,

                        text: "Temperatura (°C)",

                        font: {

                            weight: "600"

                        }

                    }

                },

                rain: {

                    type: "linear",

                    position: "right",

                    beginAtZero: true,

                    grid: {

                        drawOnChartArea: false

                    },

                    title: {

                        display: true,

                        text: "Precipitação (mm)",

                        font: {

                            weight: "600"

                        }

                    }

                }

            }

        }

    });

}