"""
==========================================================
AgroClima Café

Models - Clima

Sprint 1A / Consolidação

Responsável:
Walter Junio Pontes Teixeira
==========================================================
"""

from django.db import models


# ==========================================================
# PROVIDERS
# ==========================================================

class Provider(models.TextChoices):
    """
    Provedores de dados climáticos suportados.
    """

    OPEN_METEO = "OPEN_METEO", "Open-Meteo"
    INMET = "INMET", "INMET"
    CEMADEN = "CEMADEN", "CEMADEN"
    NOAA = "NOAA", "NOAA"


# ==========================================================
# WEATHER STATION
# ==========================================================

class WeatherStation(models.Model):
    """
    Representa uma estação climática associada a um município.

    Latitude, longitude e altitude pertencem ao modelo
    Municipio e não são duplicadas nesta entidade.
    """

    municipio = models.ForeignKey(
        "municipios.Municipio",
        on_delete=models.CASCADE,
        related_name="weather_stations",
        verbose_name="Município",
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPEN_METEO,
        verbose_name="Provedor",
    )

    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        verbose_name = "Estação Climática"
        verbose_name_plural = "Estações Climáticas"

        ordering = [
            "municipio__nome",
            "provider",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "municipio",
                    "provider",
                ],
                name="unique_station_provider",
            )
        ]

    def __str__(self):
        return (
            f"{self.municipio.nome}/"
            f"{self.provider}"
        )


# ==========================================================
# WEATHER OBSERVATION
# ==========================================================

class WeatherObservation(models.Model):
    """
    Observação meteorológica registrada para uma estação.
    """

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name="Estação",
    )

    observation_time = models.DateTimeField(
        verbose_name="Data/hora da observação",
    )

    temperatura = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Temperatura",
    )

    umidade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Umidade",
    )

    pressao = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name="Pressão",
    )

    velocidade_vento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Velocidade do vento",
    )

    direcao_vento = models.PositiveSmallIntegerField(
        verbose_name="Direção do vento",
    )

    precipitacao = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Precipitação",
    )

    cobertura_nuvens = models.PositiveSmallIntegerField(
        verbose_name="Cobertura de nuvens",
    )

    codigo_tempo = models.PositiveSmallIntegerField(
        verbose_name="Código do tempo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        verbose_name = "Observação Climática"
        verbose_name_plural = "Observações Climáticas"

        ordering = [
            "-observation_time",
        ]

        indexes = [
            models.Index(
                fields=["station"],
            ),
            models.Index(
                fields=["observation_time"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "station",
                    "observation_time",
                ],
                name="unique_station_observation",
            )
        ]

    def __str__(self):
        return (
            f"{self.station} - "
            f"{self.observation_time}"
        )


# ==========================================================
# HISTÓRICO METEOROLÓGICO DIÁRIO
# ==========================================================

class HistoricalWeatherDaily(models.Model):
    """
    Série histórica meteorológica diária de uma estação.

    Este modelo é separado de WeatherObservation porque
    representa dados climáticos agregados por dia, enquanto
    WeatherObservation representa observações instantâneas.

    Os dados são provenientes dos providers climáticos e
    podem ser utilizados pelo HistoryService, ChartService
    e demais componentes analíticos do sistema.
    """

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name="historical_weather",
        verbose_name="Estação",
    )

    data = models.DateField(
        verbose_name="Data",
    )

    temperatura_media = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Temperatura média",
    )

    temperatura_minima = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Temperatura mínima",
    )

    temperatura_maxima = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Temperatura máxima",
    )

    precipitacao = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=0,
        verbose_name="Precipitação",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        verbose_name = "Histórico Meteorológico Diário"
        verbose_name_plural = (
            "Históricos Meteorológicos Diários"
        )

        ordering = [
            "data",
        ]

        indexes = [
            models.Index(
                fields=["station"],
            ),
            models.Index(
                fields=["data"],
            ),
            models.Index(
                fields=[
                    "station",
                    "data",
                ],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "station",
                    "data",
                ],
                name="unique_station_historical_daily",
            )
        ]

    def __str__(self):
        return (
            f"{self.station} - "
            f"{self.data}"
        )


# ==========================================================
# FORECAST
# ==========================================================

class Forecast(models.Model):
    """
    Previsão meteorológica para um município/estação.
    """

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name="forecasts",
        verbose_name="Estação",
    )

    forecast_date = models.DateField(
        verbose_name="Data da previsão",
    )

    temperatura_minima = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Temperatura mínima",
    )

    temperatura_maxima = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Temperatura máxima",
    )

    umidade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Umidade",
    )

    precipitacao = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Precipitação",
    )

    probabilidade_geada = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Probabilidade de geada",
    )

    probabilidade_granizo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Probabilidade de granizo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        verbose_name = "Previsão"
        verbose_name_plural = "Previsões"

        ordering = [
            "forecast_date",
        ]

        indexes = [
            models.Index(
                fields=["station"],
            ),
            models.Index(
                fields=["forecast_date"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "station",
                    "forecast_date",
                ],
                name="unique_station_forecast",
            )
        ]

    def __str__(self):
        return (
            f"{self.station} - "
            f"{self.forecast_date}"
        )


# ==========================================================
# CLIMATE CACHE
# ==========================================================

class ClimateCache(models.Model):
    """
    Cache das respostas recebidas dos provedores climáticos.
    """

    municipio = models.ForeignKey(
        "municipios.Municipio",
        on_delete=models.CASCADE,
        related_name="climate_cache",
        verbose_name="Município",
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPEN_METEO,
        verbose_name="Provedor",
    )

    payload = models.JSONField(
        verbose_name="Payload",
    )

    collected_at = models.DateTimeField(
        verbose_name="Coletado em",
    )

    expires_at = models.DateTimeField(
        verbose_name="Expira em",
    )

    class Meta:
        verbose_name = "Cache Climático"
        verbose_name_plural = "Caches Climáticos"

        ordering = [
            "-collected_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "municipio",
                    "provider",
                ],
                name="unique_cache_provider",
            )
        ]

    def __str__(self):
        return (
            f"{self.municipio.nome} - "
            f"{self.provider}"
        )