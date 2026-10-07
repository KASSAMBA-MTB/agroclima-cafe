# ARQUIVO: agroclima/urls.py
# TIPO: código Python — substituir o conteúdo atual.
# G7.5 — inclusão da rota operacional do app clima.
#
# Alteração única:
#     include("clima.urls")
#
# A rota da Dashboard permanece exatamente preservada.

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "",
        include("dashboard.urls"),
    ),
    path(
        "clima/",
        include("clima.urls"),
    ),
]
