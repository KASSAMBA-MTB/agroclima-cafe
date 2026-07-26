"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: map_service.py

Descrição.......:
Serviço responsável pelo fornecimento dos dados geográficos utilizados
no mapa interativo da Dashboard.

Versão..........: 1.0
===============================================================================
"""

from municipios.models import Municipio


class MapService:
    """
    Serviço responsável pelos dados do mapa.
    """

    def get_points(self):

        points = []

        municipios = Municipio.objects.all().order_by("nome")

        for municipio in municipios:

            points.append({

                "id": municipio.id,

                "nome": municipio.nome,

                "estado": getattr(municipio, "estado", "SP"),

                "latitude": float(municipio.latitude),

                "longitude": float(municipio.longitude),

                "altitude": int(municipio.altitude),

                "descricao": (
                    f"{municipio.nome} "
                    f"({getattr(municipio, 'estado', 'SP')})"
                )

            })

        return points