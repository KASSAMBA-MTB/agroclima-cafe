from django.contrib import admin
from .models import Clima


@admin.register(Clima)
class ClimaAdmin(admin.ModelAdmin):

    list_display = (
        'municipio',
        'temperatura',
        'umidade',
        'data_coleta'
    )

    search_fields = (
        'municipio__nome',
    )

    list_filter = (
        'municipio',
        'data_coleta'
    )