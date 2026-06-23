import requests

from django.core.management.base import BaseCommand

from municipios.models import Municipio
from clima.models import Clima


class Command(BaseCommand):

    help = 'Coleta dados climáticos da Open-Meteo'

    def handle(self, *args, **kwargs):

        municipios = Municipio.objects.all()

        if not municipios.exists():

            self.stdout.write(
                self.style.WARNING(
                    'Nenhum município cadastrado.'
                )
            )
            return

        total = 0

        for municipio in municipios:

            try:

                url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={municipio.latitude}"
                    f"&longitude={municipio.longitude}"
                    "&current="
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "surface_pressure,"
                    "wind_speed_10m,"
                    "precipitation"
                )

                response = requests.get(
                    url,
                    timeout=20
                )

                response.raise_for_status()

                dados = response.json()

                atual = dados.get("current", {})

                temperatura = atual.get("temperature_2m")
                umidade = atual.get("relative_humidity_2m")
                pressao = atual.get("surface_pressure")
                vento = atual.get("wind_speed_10m")
                precipitacao = atual.get(
                    "precipitation",
                    0
                )

                if None in (
                    temperatura,
                    umidade,
                    pressao,
                    vento
                ):
                    raise ValueError(
                        "Dados climáticos incompletos."
                    )

                Clima.objects.create(
                    municipio=municipio,
                    temperatura=temperatura,
                    umidade=umidade,
                    pressao=pressao,
                    velocidade_vento=vento,
                    precipitacao=precipitacao
                )

                total += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {municipio.nome} atualizado"
                    )
                )

            except Exception as erro:

                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Erro em {municipio.nome}: {erro}"
                    )
                )

        self.stdout.write("\n" + "=" * 50)

        self.stdout.write(
            self.style.SUCCESS(
                f"Coletas realizadas: {total}"
            )
        )