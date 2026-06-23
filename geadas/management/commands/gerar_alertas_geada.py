from datetime import date

from django.core.management.base import BaseCommand

from clima.models import Clima
from geadas.models import Geada


class Command(BaseCommand):

    help = 'Gera alertas automáticos de geada'

    def handle(self, *args, **kwargs):

        municipios_processados = 0

        climas = (
            Clima.objects
            .select_related('municipio')
            .order_by('municipio', '-data_coleta')
        )

        municipios_analisados = []

        for clima in climas:

            if clima.municipio.id in municipios_analisados:
                continue

            municipios_analisados.append(
                clima.municipio.id
            )

            temperatura = float(clima.temperatura)

            if temperatura <= 1:
                nivel = 'CRITICO'
                risco = 100

            elif temperatura <= 3:
                nivel = 'ALTO'
                risco = 75

            elif temperatura <= 5:
                nivel = 'MEDIO'
                risco = 50

            else:
                nivel = 'BAIXO'
                risco = 10

            Geada.objects.create(
                municipio=clima.municipio,
                temperatura_prevista=temperatura,
                risco=risco,
                nivel_alerta=nivel,
                data_previsao=date.today()
            )

            municipios_processados += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'{clima.municipio.nome} -> {nivel}'
                )
            )

        self.stdout.write('\n' + '=' * 50)

        self.stdout.write(
            self.style.SUCCESS(
                f'Alertas gerados: {municipios_processados}'
            )
        )