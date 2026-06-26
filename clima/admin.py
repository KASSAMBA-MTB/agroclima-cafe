from django.contrib import admin

from .models import (
    WeatherStation,
    WeatherObservation,
    Forecast,
    ClimateCache,
)


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "municipio",
        "estado",
        "altitude",
        "ativa",
    )

    list_filter = (
        "estado",
        "ativa",
    )

    search_fields = (
        "nome",
        "municipio",
    )


@admin.register(WeatherObservation)
class WeatherObservationAdmin(admin.ModelAdmin):

    list_display = (
        "station",
        "observation_time",
        "temperatura",
        "umidade",
        "precipitacao",
    )

    list_filter = (
        "station",
    )

    ordering = (
        "-observation_time",
    )


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):

    list_display = (
        "station",
        "forecast_date",
        "temperatura_minima",
        "temperatura_maxima",
    )

    ordering = (
        "forecast_date",
    )


@admin.register(ClimateCache)
class ClimateCacheAdmin(admin.ModelAdmin):

    list_display = (
        "station",
        "collected_at",
        "expires_at",
    )

    ordering = (
        "-collected_at",
    )