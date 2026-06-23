from django.db import models


class Municipio(models.Model):
    nome = models.CharField(
        max_length=100,
        verbose_name="Município"
    )

    estado = models.CharField(
        max_length=2,
        default="SP"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    altitude = models.IntegerField()

    data_cadastro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"

    def __str__(self):
        return self.nome