"""
==========================================================
Provider Base

==========================================================
"""

from abc import ABC, abstractmethod


class WeatherProvider(ABC):

    @abstractmethod
    def current_weather(self, municipio):

        raise NotImplementedError