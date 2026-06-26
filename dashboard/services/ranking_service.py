"""
==========================================================
AgroClima Café

Ranking Service

Responsável pelo Ranking AgroClima dos municípios.

O ranking é calculado utilizando o
Índice AgroClima (IAC).

Autor:
Walter Junio Pontes Teixeira

Curso:
Ciência de Dados - UNIVESP
==========================================================
"""

from core.intelligence.agroclima_index import AgroClimaIndex


class RankingService:

    """
    Serviço responsável pelo Ranking AgroClima.
    """

    def __init__(self):

        self.iac = AgroClimaIndex()

    def get_ranking(self):

        municipios = [

            {

                "municipio": "São Sebastião da Grama",

                "estado": "SP",

                "temperature": 18.2,

                "humidity": 73,

                "precipitation": 26,

                "frost": "low",

                "hail": "low"

            },

            {

                "municipio": "Divinolândia",

                "estado": "SP",

                "temperature": 17.9,

                "humidity": 71,

                "precipitation": 24,

                "frost": "low",

                "hail": "low"

            },

            {

                "municipio": "Águas da Prata",

                "estado": "SP",

                "temperature": 17.5,

                "humidity": 75,

                "precipitation": 27,

                "frost": "medium",

                "hail": "low"

            },

            {

                "municipio": "Poços de Caldas",

                "estado": "MG",

                "temperature": 18.8,

                "humidity": 69,

                "precipitation": 30,

                "frost": "low",

                "hail": "low"

            },

            {

                "municipio": "Caldas",

                "estado": "MG",

                "temperature": 17.3,

                "humidity": 74,

                "precipitation": 29,

                "frost": "medium",

                "hail": "low"

            }

        ]

        ranking = []

        for cidade in municipios:

            resultado = self.iac.calculate(

                temperature=cidade["temperature"],

                humidity=cidade["humidity"],

                precipitation=cidade["precipitation"],

                frost_level=cidade["frost"],

                hail_level=cidade["hail"]

            )

            ranking.append({

                "municipio": cidade["municipio"],

                "estado": cidade["estado"],

                "indice": resultado["index"],

                "classificacao": resultado["classification"],

                "cor": resultado["color"],

                "icone": resultado["icon"]

            })

        ranking.sort(

            key=lambda municipio: municipio["indice"],

            reverse=True

        )

        for posicao, municipio in enumerate(

            ranking,

            start=1

        ):

            municipio["posicao"] = posicao

        return ranking