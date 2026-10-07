# ARQUIVO: clima/urls.py
# TIPO: código Python — novo arquivo.
# G7.5 — rota exclusiva do consumidor operacional Single Run.

from django.urls import path

from clima.views import single_run_forecast

app_name = "clima"

urlpatterns = [
    path(
        "single-run/forecast/",
        single_run_forecast,
        name="single_run_forecast",
    ),
]
