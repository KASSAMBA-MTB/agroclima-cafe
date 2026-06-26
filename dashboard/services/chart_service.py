class ChartService:
    """
    Responsável pelos dados dos gráficos do Dashboard.
    """

    def get_chart(self):

        return {

            "dias": [

                "Seg",
                "Ter",
                "Qua",
                "Qui",
                "Sex",
                "Sáb",
                "Dom"

            ],

            "temperatura": [

                16,
                18,
                17,
                19,
                20,
                18,
                17

            ],

            "precipitacao": [

                5,
                3,
                8,
                14,
                6,
                1,
                0

            ]

        }