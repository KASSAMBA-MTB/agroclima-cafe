import logging
from datetime import datetime

from django.core.management.base import BaseCommand

from clima.services.update_service import UpdateService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Atualiza as observações meteorológicas atuais de todos os municípios."

    def handle(self, *args, **options):
        inicio = datetime.now().astimezone()
        self.stdout.write(f"Início da coleta: {inicio.isoformat()}")

        try:
            resultado = UpdateService().update_all()
        except Exception:
            logger.exception("Falha geral na coleta meteorológica.")
            self.stderr.write(self.style.ERROR("Falha geral na coleta. Consulte o log."))
            raise

        municipios = resultado.get("municipios", 0)
        erros = resultado.get("erros", 0)

        mensagem = (
            f"Coleta finalizada: {municipios} município(s) atualizado(s); "
            f"{erros} erro(s)."
        )

        if erros:
            self.stderr.write(self.style.WARNING(mensagem))
        else:
            self.stdout.write(self.style.SUCCESS(mensagem))

        if erros:
            raise RuntimeError(mensagem)
