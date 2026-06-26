"""
==========================================================
AgroClima Café

Base Rule

Classe base para todas as regras do sistema.
Todas as regras devem herdar desta classe.

==========================================================
"""

from abc import ABC, abstractmethod


class BaseRule(ABC):

    """
    Classe abstrata para todas as regras.
    """

    id = ""
    name = ""
    description = ""

    @abstractmethod
    def evaluate(self, context: dict):
        """
        Executa a regra.

        Parameters
        ----------
        context : dict

        Returns
        -------
        dict
        """
        pass