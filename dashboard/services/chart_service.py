"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: chart_service.py

Autor...........: Walter Junio Pontes Teixeira
Polo............: São João da Boa Vista - SP
Ano.............: 2026

Descrição.......:
Serviço responsável pelo fornecimento dos dados utilizados pelos gráficos
do Dashboard Principal.

Responsabilidades:
- Consolidar os períodos do gráfico;
- Preservar os dados fornecidos pelo HistoryService;
- Preparar o resumo correspondente a cada período;
- Não executar regras de inteligência climática;
- Não inventar ocorrências históricas de geada.

Versão..........: 2.3
===============================================================================
"""

from statistics import mean

from clima.services.history_service import HistoryService


class ChartService:
    """
    Serviço responsável pelos dados históricos utilizados
    nos gráficos da Dashboard.
    """

    def __init__(self):

        self.history = HistoryService()

    # ==========================================================
    # DADOS DO GRÁFICO
    # ==========================================================

    def get_chart(
        self,
        days=7,
    ):
        """
        Mantém compatibilidade com chamadas existentes.

        Retorna o período solicitado.
        """

        data = self.history.chart_data(
            municipio=None,
            days=days,
        )

        return self._format(
            data
        )

    # ==========================================================
    # PERÍODOS DO DASHBOARD
    # ==========================================================

    def get_chart_periods(self):
        """
        Prepara todas as séries utilizadas pelos controles
        de período do gráfico.

        Cada período possui sua própria série e seu próprio
        resumo consolidado.

        Hoje:
            somente o dia atual.

        7 dias:
            últimos 7 dias.

        30 dias:
            últimos 30 dias.

        Histórico:
            todo o histórico disponível no banco.
        """

        hoje = self.history.chart_data(
            municipio=None,
            days=1,
        )

        sete_dias = self.history.chart_data(
            municipio=None,
            days=7,
        )

        trinta_dias = self.history.chart_data(
            municipio=None,
            days=30,
        )

        historico = self.history.chart_data(
            municipio=None,
            days=None,
        )

        return {

            "hoje": self._format(
                hoje
            ),

            "7_dias": self._format(
                sete_dias
            ),

            "30_dias": self._format(
                trinta_dias
            ),

            "historico": self._format(
                historico
            ),

        }

    # ==========================================================
    # FORMATAÇÃO
    # ==========================================================

    @classmethod
    def _format(
        cls,
        data,
    ):
        """
        Normaliza os dados recebidos do HistoryService.

        Além das séries utilizadas pelo gráfico, prepara um
        resumo correspondente exatamente ao período consultado.
        """

        if not data:

            return cls._empty()

        dias = data.get(
            "dias",
            [],
        )

        temperatura = data.get(
            "temperatura",
            [],
        )

        precipitacao = data.get(
            "precipitacao",
            [],
        )

        umidade = data.get(
            "umidade",
            [],
        )

        vento = data.get(
            "vento",
            [],
        )

        indice_agroclima = data.get(
            "indice_agroclima",
            [],
        )

        return {

            # ==================================================
            # SÉRIES DO GRÁFICO
            # ==================================================

            "dias": dias,

            "temperatura": temperatura,

            "precipitacao": precipitacao,

            "umidade": umidade,

            "vento": vento,

            "indice_agroclima": indice_agroclima,

            # ==================================================
            # RESUMO DO PERÍODO
            # ==================================================

            "resumo": cls._build_summary(
                temperatura=temperatura,
                precipitacao=precipitacao,
            ),

        }

    # ==========================================================
    # RESUMO DO PERÍODO
    # ==========================================================

    @classmethod
    def _build_summary(
        cls,
        temperatura,
        precipitacao,
    ):
        """
        Consolida os indicadores disponíveis na série.

        Temperatura:
            média dos valores válidos do período.

        Precipitação:
            acumulado dos valores válidos do período.

        Geadas:
            permanece None enquanto o HistoryService não possuir
            uma fonte histórica real de ocorrências de geada.

        Tendência:
            classificação descritiva baseada na série de
            temperatura disponível.
        """

        temperaturas_validas = (
            cls._valid_numbers(
                temperatura
            )
        )

        precipitacoes_validas = (
            cls._valid_numbers(
                precipitacao
            )
        )

        # ======================================================
        # TEMPERATURA MÉDIA
        # ======================================================

        temperatura_media = None

        if temperaturas_validas:

            temperatura_media = round(
                mean(
                    temperaturas_validas
                ),
                1,
            )

        # ======================================================
        # PRECIPITAÇÃO ACUMULADA
        # ======================================================

        precipitacao_total = None

        if precipitacoes_validas:

            precipitacao_total = round(
                sum(
                    precipitacoes_validas
                ),
                1,
            )

        # ======================================================
        # RESUMO
        # ======================================================

        return {

            "temperatura_media": (
                temperatura_media
            ),

            "precipitacao": (
                precipitacao_total
            ),

            # --------------------------------------------------
            # Não inventar ocorrência histórica.
            #
            # O modelo histórico atual não fornece esse dado.
            # --------------------------------------------------

            "geadas": None,

            # --------------------------------------------------
            # Tendência da temperatura.
            # --------------------------------------------------

            "tendencia": (
                cls._temperature_trend(
                    temperaturas_validas
                )
            ),

        }

    # ==========================================================
    # TENDÊNCIA DE TEMPERATURA
    # ==========================================================

    @staticmethod
    def _temperature_trend(
        values,
    ):
        """
        Classifica a tendência da série de temperatura.

        Critério atual:

            diferença < 0,5 °C
                Estável

            diferença >= 0,5 °C
                Alta

            diferença <= -0,5 °C
                Queda

        A comparação é feita entre o primeiro e o último
        valor válido da série.
        """

        if not values:

            return None

        if len(values) < 2:

            return "Estável"

        primeiro = values[0]

        ultimo = values[-1]

        diferenca = ultimo - primeiro

        # ======================================================
        # ESTÁVEL
        # ======================================================

        if abs(diferenca) < 0.5:

            return "Estável"

        # ======================================================
        # ALTA
        # ======================================================

        if diferenca > 0:

            return "Alta"

        # ======================================================
        # QUEDA
        # ======================================================

        return "Queda"

    # ==========================================================
    # VALIDAÇÃO NUMÉRICA
    # ==========================================================

    @staticmethod
    def _valid_numbers(
        values,
    ):
        """
        Retorna somente valores numéricos válidos.

        None e valores não conversíveis são ignorados.
        """

        if not values:

            return []

        valid = []

        for value in values:

            if value is None:

                continue

            try:

                valid.append(
                    float(value)
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

        return valid

    # ==========================================================
    # RETORNO PADRÃO
    # ==========================================================

    @staticmethod
    def _empty():

        return {

            "dias": [],

            "temperatura": [],

            "precipitacao": [],

            "umidade": [],

            "vento": [],

            "indice_agroclima": [],

            "resumo": {

                "temperatura_media": None,

                "precipitacao": None,

                "geadas": None,

                "tendencia": None,

            },

        }