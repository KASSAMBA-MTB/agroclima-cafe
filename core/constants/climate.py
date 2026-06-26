"""
==========================================================
AgroClima Café

Climate Constants

Constantes oficiais utilizadas em toda a plataforma.

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP

==========================================================
"""

# ==========================================================
# PESOS DO ÍNDICE AGROCLIMA (IAC)
# ==========================================================

TEMPERATURE_WEIGHT = 0.30

HUMIDITY_WEIGHT = 0.20

PRECIPITATION_WEIGHT = 0.20

FROST_WEIGHT = 0.20

HAIL_WEIGHT = 0.10


# ==========================================================
# TEMPERATURA (°C)
# ==========================================================

TEMPERATURE_SCORE = [

    ((18, 23), 100),

    ((16, 18), 90),

    ((23, 25), 85),

    ((12, 16), 70),

    ((25, 28), 65),

    ((-100, 12), 40),

    ((28, 100), 40)

]


# ==========================================================
# UMIDADE RELATIVA (%)
# ==========================================================

HUMIDITY_SCORE = [

    ((60, 80), 100),

    ((50, 60), 85),

    ((80, 90), 80),

    ((40, 50), 60),

    ((90, 100), 55),

    ((0, 40), 40)

]


# ==========================================================
# PRECIPITAÇÃO (mm/semana)
# ==========================================================

PRECIPITATION_SCORE = [

    ((20, 40), 100),

    ((10, 20), 90),

    ((40, 60), 85),

    ((5, 10), 65),

    ((60, 80), 60),

    ((80, 10000), 40)

]


# ==========================================================
# RISCO DE GEADA
# ==========================================================

FROST_SCORE = {

    "low": 100,

    "medium": 70,

    "high": 40,

    "critical": 0

}


# ==========================================================
# RISCO DE GRANIZO
# ==========================================================

HAIL_SCORE = {

    "low": 100,

    "medium": 70,

    "high": 40,

    "critical": 0

}


# ==========================================================
# CLASSIFICAÇÃO DO IAC
# ==========================================================

IAC_LEVELS = [

    (90, 100, "Excelente"),

    (80, 89.99, "Muito Favorável"),

    (70, 79.99, "Favorável"),

    (60, 69.99, "Moderado"),

    (40, 59.99, "Desfavorável"),

    (0, 39.99, "Crítico")

]


# ==========================================================
# CORES OFICIAIS DO DASHBOARD
# ==========================================================

IAC_COLORS = {

    "Excelente": "#2E7D32",

    "Muito Favorável": "#4CAF50",

    "Favorável": "#8BC34A",

    "Moderado": "#FFC107",

    "Desfavorável": "#FF9800",

    "Crítico": "#E53935"

}


# ==========================================================
# ÍCONES OFICIAIS
# ==========================================================

IAC_ICONS = {

    "Excelente": "bi-check-circle-fill",

    "Muito Favorável": "bi-award-fill",

    "Favorável": "bi-graph-up",

    "Moderado": "bi-exclamation-circle-fill",

    "Desfavorável": "bi-exclamation-triangle-fill",

    "Crítico": "bi-exclamation-octagon-fill"

}