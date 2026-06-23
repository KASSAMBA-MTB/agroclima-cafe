from django.contrib import admin
from .models import Municipio


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):

    list_display = (
        'nome',
        'estado',
        'altitude',
        'latitude',
        'longitude',
        'data_cadastro'
    )

    search_fields = (
        'nome',
        'estado'
    )

    list_filter = (
        'estado',
    )

    ordering = (
        'nome',
    )