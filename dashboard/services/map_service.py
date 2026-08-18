"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: map_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
Serviço responsável exclusivamente pelo fornecimento dos dados geográficos
utilizados no mapa interativo da Dashboard.

Responsabilidades:
    • Consultar os municípios monitorados.
    • Normalizar os dados geográficos para o Dashboard.
    • Preparar os campos estruturais que poderão ser enriquecidos
      posteriormente pela DashboardFacade.

Este serviço NÃO:
    • consulta dados meteorológicos;
    • executa regras de geada;
    • calcula FRI;
    • executa inteligência;
    • importa a si próprio.

Versão..........: 2.1
===============================================================================
"""

from municipios.models import Municipio


class MapService:
    """
    Serviço exclusivamente geográfico.

    O MapService fornece a estrutura-base dos pontos do mapa.
    O enriquecimento climático e a inteligência são responsabilidades
    das camadas superiores da arquitetura.
    """

    # ==========================================================
    # PONTOS GEOGRÁFICOS
    # ==========================================================

    def get_points(self):
        """
        Retorna os municípios monitorados como pontos geográficos.

        Retorno:
            [
                {
                    "id": ...,
                    "nome": ...,
                    "estado": ...,
                    "latitude": ...,
                    "longitude": ...,
                    "altitude": ...,
                    "descricao": ...,
                    "fri": None,
                    "severity": None,
                    "confidence": None,
                    "color": None,
                }
            ]
        """

        points = []

        municipios = (
            Municipio.objects
            .all()
            .order_by("nome")
        )

        for municipio in municipios:

            points.append({

                "id": municipio.id,

                "nome": municipio.nome,

                "estado": municipio.estado,

                "latitude": self._to_float(
                    municipio.latitude
                ),

                "longitude": self._to_float(
                    municipio.longitude
                ),

                "altitude": self._to_float(
                    municipio.altitude
                ),

                "descricao": (
                    f"{municipio.nome}/"
                    f"{municipio.estado}"
                ),

                # ==================================================
                # CAMPOS RESERVADOS PARA ENRIQUECIMENTO SUPERIOR
                # ==================================================

                "fri": None,

                "severity": None,

                "confidence": None,

                "color": None,

            })

        return points

    # ==========================================================
    # CONVERSÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _to_float(value):
        """
        Converte valores Decimal/números para float.

        Mantém None quando o campo geográfico não estiver preenchido.
        """

        if value is None:

            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None
