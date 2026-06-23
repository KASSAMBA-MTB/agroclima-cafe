from django.contrib import admin
from .models import Municipio

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'estado', 'altitude')
    search_fields = ('nome', 'estado')