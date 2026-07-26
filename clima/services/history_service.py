"""
==========================================================
AgroClima Café

History Service
==========================================================
"""

from datetime import timedelta

from django.utils import timezone

from clima.models import (
    Provider,
    WeatherStation,
)

from .weather_service import WeatherService


class HistoryService:

    def __init__(self):

        self.weather = WeatherService()

    def latest(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):

        return self.weather.latest(
            municipio,
            provider,
        )

    def current(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):

        return self.weather.update_current_weather(
            municipio,
            provider,
        )

    def station(
        self,
        municipio,
        provider=Provider.OPEN_METEO,
    ):

        station, _ = WeatherStation.objects.get_or_create(
            municipio=municipio,
            provider=provider,
            defaults={
                "ativa": True,
            },
        )

        return station

    def chart_data(
        self,
        municipio,
        days=7,
        provider=Provider.OPEN_METEO,
    ):
        """
        Gera dados para o gráfico do dashboard.

        Enquanto não existir histórico persistido,
        replica a última observação para preencher
        os últimos dias.
        """

        dto = self.weather.latest(
            municipio,
            provider,
        )

        if dto is None:

            return {
                "dias": [],
                "temperatura": [],
                "precipitacao": [],
                "umidade": [],
            }

        dias = []

        temperatura = []

        precipitacao = []

        umidade = []

        hoje = timezone.localdate()

        for i in range(days - 1, -1, -1):

            data = hoje - timedelta(days=i)

            dias.append(data.strftime("%d/%m"))

            temperatura.append(float(dto.temperature))

            precipitacao.append(float(dto.precipitation))

            umidade.append(float(dto.humidity))

        return {
            "dias": dias,
            "temperatura": temperatura,
            "precipitacao": precipitacao,
            "umidade": umidade,
        }