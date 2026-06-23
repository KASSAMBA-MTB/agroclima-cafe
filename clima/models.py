from django.db import models
from municipios.models import Municipio


class Clima(models.Model):

    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        related_name='climas'
    )

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

    data_coleta = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Clima'
        verbose_name_plural = 'Dados Climáticos'

    def __str__(self):
        return f'{self.municipio} - {self.temperatura}°C'