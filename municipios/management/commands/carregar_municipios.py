from django.core.management.base import BaseCommand
from municipios.models import Municipio


class Command(BaseCommand):

    help = 'Carrega os municípios cafeeiros iniciais do projeto AgroClima Café'

    def handle(self, *args, **kwargs):

        municipios = [

            {
                'nome': 'São João da Boa Vista',
                'estado': 'SP',
                'latitude': -21.9699,
                'longitude': -46.7981,
                'altitude': 767
            },

            {
                'nome': 'Espírito Santo do Pinhal',
                'estado': 'SP',
                'latitude': -22.1900,
                'longitude': -46.7478,
                'altitude': 870
            },

            {
                'nome': 'Águas da Prata',
                'estado': 'SP',
                'latitude': -21.9319,
                'longitude': -46.7178,
                'altitude': 820
            },

            {
                'nome': 'Vargem Grande do Sul',
                'estado': 'SP',
                'latitude': -21.8322,
                'longitude': -46.8925,
                'altitude': 680
            },

            {
                'nome': 'Andradas',
                'estado': 'MG',
                'latitude': -22.0686,
                'longitude': -46.5724,
                'altitude': 913
            },

            {
                'nome': 'Poços de Caldas',
                'estado': 'MG',
                'latitude': -21.7874,
                'longitude': -46.5614,
                'altitude': 1186
            }

        ]

        total_criados = 0
        total_existentes = 0

        for municipio in municipios:

            _, criado = Municipio.objects.get_or_create(
                nome=municipio['nome'],
                defaults={
                    'estado': municipio['estado'],
                    'latitude': municipio['latitude'],
                    'longitude': municipio['longitude'],
                    'altitude': municipio['altitude']
                }
            )

            if criado:
                total_criados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {municipio['nome']} cadastrado."
                    )
                )
            else:
                total_existentes += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"• {municipio['nome']} já existe."
                    )
                )

        self.stdout.write("\n" + "=" * 50)

        self.stdout.write(
            self.style.SUCCESS(
                f"Municípios criados: {total_criados}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Municípios já existentes: {total_existentes}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Carga de municípios concluída com sucesso!"
            )
        )