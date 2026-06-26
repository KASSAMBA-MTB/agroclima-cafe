"""
==========================================================
AgroClima Café

Base Indicator

Classe base para todos os indicadores do
Índice AgroClima.

==========================================================
"""

from abc import ABC, abstractmethod


class BaseIndicator(ABC):

    """
    Classe abstrata para indicadores climáticos.
    """

    @abstractmethod
    def score(self, value):

        """
        Retorna um score entre 0 e 100.
        """

        raise NotImplementedError