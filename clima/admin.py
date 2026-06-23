from django.contrib import admin
from .models import Clima


@admin.register(Clima)
class ClimaAdmin(admin.ModelAdmin):

    list_display = (
        'municipio',
        'temperatura',
        'umidade',
        'pressao',
        'velocidade_vento',
        'precipitacao',
        'data_coleta'
    )

    search_fields = (
        'municipio__nome',
    )

    list_filter = (
        'municipio',
        'data_coleta'
    )

    ordering = (
        '-data_coleta',
    )

    list_per_page = 20