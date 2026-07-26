"""
==========================================================
AgroClima Café

Update Service

==========================================================
"""

import logging

from clima.models import Provider
from clima.services.weather_service import WeatherService
from municipios.models import Municipio


logger = logging.getLogger(__name__)


class UpdateService:

    def __init__(self):

        self.weather = WeatherService()

    def update_all(self):

        atualizados = 0

        erros = 0

        for municipio in Municipio.objects.all():

            try:

                self.weather.update_current_weather(

                    municipio,

                    Provider.OPEN_METEO

                )

                atualizados += 1

            except Exception as exc:

                erros += 1

                logger.exception(

                    "Erro ao atualizar %s: %s",

                    municipio,

                    exc

                )

        return {

            "municipios": atualizados,

            "erros": erros

        }