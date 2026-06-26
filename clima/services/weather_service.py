"""
==========================================================
Weather Service

==========================================================
"""

from clima.models import Provider

from .openmeteo_provider import OpenMeteoProvider


class WeatherService:

    """
    Serviço central da plataforma climática.
    """

    def __init__(self):

        self.providers = {

            Provider.OPEN_METEO: OpenMeteoProvider(),

        }

    def current_weather(

        self,

        municipio,

        provider=Provider.OPEN_METEO

    ):

        service = self.providers.get(provider)

        if service is None:

            raise ValueError(

                f"Provider '{provider}' não suportado."

            )

        return service.current_weather(municipio)