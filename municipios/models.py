"""
==========================================================
AgroClima Café

App: Clima

Models

Domínio climático da plataforma.

==========================================================
"""

from django.db import models
from django.utils import timezone


# ==========================================================
# PROVEDORES
# ==========================================================

class Provider(models.TextChoices):
    OPEN_METEO = "OPEN_METEO", "Open-Meteo"
    INMET = "INMET", "INMET"
    NOAA = "NOAA", "NOAA"
    CPTEC = "CPTEC", "CPTEC"


# ==========================================================
# ESTAÇÃO METEOROLÓGICA
# ==========================================================

class WeatherStation(models.Model):

    municipio = models.ForeignKey(
        "municipios.Municipio",
        on_delete=models.PROTECT,
        related_name="weather_stations",
        verbose_name="Município",
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPEN_METEO,
        verbose_name="Provedor"
    )

    provider_station_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ID da Estação no Provedor"
    )

    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
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
        ordering = ["municipio__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "provider"],
                name="uq_station_provider"
            )
        ]

    def __str__(self):
        return f"{self.municipio} - {self.get_provider_display()}"


# ==========================================================
# OBSERVAÇÃO CLIMÁTICA
# ==========================================================

class WeatherObservation(models.Model):

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name="Estação"
    )

    observation_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data/Hora"
    )

    temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Temperatura (°C)"
    )

    apparent_temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Sensação Térmica (°C)"
    )

    humidity = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Umidade (%)"
    )

    dew_point = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Ponto de Orvalho (°C)"
    )

    pressure = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name="Pressão (hPa)"
    )

    wind_speed = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Velocidade do Vento (km/h)"
    )

    wind_direction = models.PositiveSmallIntegerField(
        verbose_name="Direção do Vento (°)"
    )

    precipitation = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Precipitação (mm)"
    )

    cloud_cover = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Cobertura de Nuvens (%)"
    )

    weather_code = models.PositiveSmallIntegerField(
        verbose_name="Código Meteorológico"
    )

    solar_radiation = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Radiação Solar"
    )

    uv_index = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Índice UV"
    )

    visibility = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Visibilidade (m)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Observação Climática"
        verbose_name_plural = "Observações Climáticas"
        ordering = ["-observation_time"]

        indexes = [
            models.Index(fields=["observation_time"]),
            models.Index(fields=["weather_code"]),
            models.Index(fields=["station"]),
        ]

    def __str__(self):
        return f"{self.station} - {self.observation_time:%d/%m/%Y %H:%M}"


# ==========================================================
# CACHE DA API
# ==========================================================

class ClimateCache(models.Model):

    municipio = models.ForeignKey(
        "municipios.Municipio",
        on_delete=models.CASCADE,
        related_name="climate_cache",
        verbose_name="Município"
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPEN_METEO,
        verbose_name="Provedor"
    )

    payload = models.JSONField(
        verbose_name="Resposta da API"
    )

    collected_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Coletado em"
    )

    expires_at = models.DateTimeField(
        verbose_name="Expira em"
    )

    class Meta:
        verbose_name = "Cache Climático"
        verbose_name_plural = "Caches Climáticos"
        ordering = ["-collected_at"]

        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["municipio"]),
        ]

    def __str__(self):
        return f"{self.municipio} - {self.get_provider_display()}"