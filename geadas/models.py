from django.db import models
from municipios.models import Municipio


class Geada(models.Model):

    NIVEL_ALERTA = [
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
        ('CRITICO', 'Crítico'),
    ]

    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE
    )

    temperatura_prevista = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    risco = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    nivel_alerta = models.CharField(
        max_length=10,
        choices=NIVEL_ALERTA
    )

    data_previsao = models.DateField()

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f'{self.municipio} - {self.nivel_alerta}'