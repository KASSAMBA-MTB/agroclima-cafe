"""
==========================================================
AgroClima Café

App: Clima

Admin

==========================================================
"""

from django.contrib import admin

from .models import (
    WeatherStation,
    WeatherObservation,
    ClimateCache,
)


# ==========================================================
# WEATHER STATION
# ==========================================================

@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):

    list_display = (
        "municipio",
        "provider",
        "provider_station_id",
        "ativa",
        "updated_at",
    )

    list_filter = (
        "provider",
        "ativa",
    )

    search_fields = (
        "municipio__nome",
        "provider_station_id",
    )

    autocomplete_fields = (
        "municipio",
    )

    ordering = (
        "municipio__nome",
    )


# ==========================================================
# WEATHER OBSERVATION
# ==========================================================

@admin.register(WeatherObservation)
class WeatherObservationAdmin(admin.ModelAdmin):

    list_display = (
        "station",
        "observation_time",
        "temperature",
        "humidity",
        "precipitation",
        "weather_code",
    )

    list_filter = (
        "station__provider",
        "weather_code",
    )

    search_fields = (
        "station__municipio__nome",
    )

    autocomplete_fields = (
        "station",
    )

    ordering = (
        "-observation_time",
    )

    date_hierarchy = "observation_time"


# ==========================================================
# CLIMATE CACHE
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
    )

    search_fields = (
        "municipio__nome",
    )

    autocomplete_fields = (
        "municipio",
    )

    ordering = (
        "-collected_at",
    )