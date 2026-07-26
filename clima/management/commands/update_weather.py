"""
==========================================================
AgroClima Café

Atualização automática do clima

==========================================================
"""

from django.core.management.base import BaseCommand

from clima.services.update_service import UpdateService


class Command(BaseCommand):

    help = "Atualiza automaticamente os dados climáticos."

    def handle(self, *args, **options):

        service = UpdateService()

        resultado = service.update_all()

        self.stdout.write(

            self.style.SUCCESS(

                f"Municípios atualizados: {resultado['municipios']}"

            )

        )

        if resultado["erros"]:

            self.stdout.write(

                self.style.WARNING(

                    f"Erros encontrados: {resultado['erros']}"

                )

            )