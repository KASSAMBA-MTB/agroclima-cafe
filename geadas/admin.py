from django.contrib import admin
from .models import Geada


@admin.register(Geada)
class GeadaAdmin(admin.ModelAdmin):

    list_display = (
        'municipio',
        'temperatura_prevista',
        'risco',
        'nivel_alerta',
        'data_previsao'
    )

    list_filter = (
        'nivel_alerta',
        'municipio'
    )

    search_fields = (
        'municipio__nome',
    )