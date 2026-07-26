"""
==========================================================
AgroClima Café

Models - Clima

Sprint 1A
==========================================================
"""

from django.db import models


# ==========================================================
# Providers
# ==========================================================

class Provider(models.TextChoices):
    """
    Provedores de dados climáticos suportados.
    """

    OPEN_METEO = "OPEN_METEO", "Open-Meteo"


# ==========================================================
# Weather Station
# ==========================================================

class WeatherStation(models.Model):
    """
    Representa um provedor de dados associado a um município.

    Não armazena latitude, longitude ou altitude.
    Essas informações pertencem exclusivamente ao modelo
    Municipio.
    """

    municipio = models.ForeignKey(
        "municipios.Municipio",
        on_delete=models.CASCADE,
        related_name="weather_stations",
        verbose_name="Município"
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPEN_METEO,
        verbose_name="Provedor"
    )

    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Estação Climática"
        verbose_name_plural = "Estações Climáticas"

        ordering = [
            "municipio__nome",
            "provider"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "municipio",
                    "provider"
                ],
                name="unique_station_provider"
            )
        ]

    def __str__(self):

        return (
            f"{self.municipio.nome}/"
            f"{self.provider}"
        )


# ==========================================================
# Climate Cache
# ==========================================================

class ClimateCache(models.Model):
    """
    Cache das respostas recebidas dos provedores.
    """

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
        verbose_name="Payload"
    )

    collected_at = models.DateTimeField(
        verbose_name="Coletado em"
    )

    expires_at = models.DateTimeField(
        verbose_name="Expira em"
    )

    class Meta:
        verbose_name = "Cache Climático"
        verbose_name_plural = "Caches Climáticos"

        ordering = [
            "-collected_at"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "municipio",
                    "provider"
                ],
                name="unique_cache_provider"
            )
        ]

    def __str__(self):

        return (
            f"{self.municipio.nome} - "
            f"{self.provider}"
        )