from django.db import models


class Municipio(models.Model):

    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Município"
    )

    estado = models.CharField(
        max_length=2,
        default="SP",
        verbose_name="UF"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name="Latitude"
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name="Longitude"
    )

    altitude = models.IntegerField(
        verbose_name="Altitude (m)"
    )

    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Cadastro"
    )

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome}/{self.estado}"