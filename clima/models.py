"""
==========================================================
AgroClima Café

App: Clima

Models

Modelos responsáveis pelo domínio climático da plataforma.

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from django.db import models


class WeatherStation(models.Model):
    """
    Estação meteorológica (real ou virtual).
    """

    nome = models.CharField(
        max_length=100,
        verbose_name="Nome"
    )

    municipio = models.CharField(
        max_length=100,
        verbose_name="Município"
    )

    estado = models.CharField(
        max_length=2,
        verbose_name="UF"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    altitude = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Altitude em metros"
    )

    ativa = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        verbose_name = "Estação Meteorológica"

        verbose_name_plural = "Estações Meteorológicas"

        ordering = ["municipio"]

    def __str__(self):

        return f"{self.nome} ({self.municipio}/{self.estado})"


# =========================================================


class WeatherObservation(models.Model):
    """
    Observação meteorológica.
    """

    station = models.ForeignKey(

        WeatherStation,

        on_delete=models.CASCADE,

        related_name="observations"

    )

    observation_time = models.DateTimeField()

    temperatura = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    umidade = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    pressao = models.DecimalField(
        max_digits=7,
        decimal_places=2
    )

    velocidade_vento = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    direcao_vento = models.PositiveSmallIntegerField()

    precipitacao = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    cobertura_nuvens = models.PositiveSmallIntegerField()

    codigo_tempo = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        verbose_name = "Observação Climática"

        verbose_name_plural = "Observações Climáticas"

        ordering = ["-observation_time"]

    def __str__(self):

        return f"{self.station} - {self.observation_time}"


# =========================================================


class Forecast(models.Model):
    """
    Previsão meteorológica.
    """

    station = models.ForeignKey(

        WeatherStation,

        on_delete=models.CASCADE,

        related_name="forecasts"

    )

    forecast_date = models.DateField()

    temperatura_minima = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    temperatura_maxima = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    umidade = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    precipitacao = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    probabilidade_geada = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    probabilidade_granizo = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        verbose_name = "Previsão"

        verbose_name_plural = "Previsões"

        ordering = ["forecast_date"]

    def __str__(self):

        return f"{self.station} - {self.forecast_date}"


# =========================================================


class ClimateCache(models.Model):
    """
    Cache dos dados retornados pela API.
    """

    station = models.ForeignKey(

        WeatherStation,

        on_delete=models.CASCADE,

        related_name="cache"

    )

    payload = models.JSONField()

    collected_at = models.DateTimeField()

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        verbose_name = "Cache Climático"

        verbose_name_plural = "Cache Climático"

        ordering = ["-collected_at"]

    def __str__(self):

        return f"{self.station} ({self.collected_at})"