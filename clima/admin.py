"""
==========================================================
AgroClima Café

App: Clima

Admin

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from django.contrib import admin

from .models import (
    WeatherStation,
    ClimateCache,
)


# ==========================================================
# Weather Station
# ==========================================================

@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):

    list_display = (
        "municipio",
        "provider",
        "ativa",
        "criado_em",
    )

    list_filter = (
        "provider",
        "ativa",
        "municipio__estado",
    )

    search_fields = (
        "municipio__nome",
        "municipio__estado",
    )

    ordering = (
        "municipio__nome",
        "provider",
    )

    list_per_page = 25


# ==========================================================
# Climate Cache
# ==========================================================

@admin.register(ClimateCache)
class ClimateCacheAdmin(admin.ModelAdmin):

    list_display = (
        "municipio",
        "provider",
        "collected_at",
        "expires_at",
    )

    list_filter = (
        "provider",
        "municipio__estado",
    )

    search_fields = (
        "municipio__nome",
    )

    ordering = (
        "-collected_at",
    )

    readonly_fields = (
        "payload",
        "collected_at",
        "expires_at",
    )

    list_per_page = 30