from django.contrib import admin

from .models import Municipio


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "estado",
        "altitude",
    )

    list_filter = (
        "estado",
    )

    search_fields = (
        "nome",
    )

    ordering = (
        "nome",
    )