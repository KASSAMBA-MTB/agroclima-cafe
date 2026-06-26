"""
==========================================================
Open-Meteo Provider

Estrutura inicial.

Integração será implementada
na Sprint 2.2.

==========================================================
"""

from .provider import WeatherProvider


class OpenMeteoProvider(WeatherProvider):

    def current_weather(self, municipio):

        raise NotImplementedError(

            "Integração Open-Meteo será implementada na Sprint 2.2."

        )