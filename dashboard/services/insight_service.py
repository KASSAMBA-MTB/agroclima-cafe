"""
===============================================================================
UNIVERSIDADE VIRTUAL DO ESTADO DE SÃO PAULO - UNIVESP

Curso...........: Bacharelado em Ciência de Dados
Disciplina......: Trabalho de Conclusão de Curso (TCC)
Projeto.........: AgroClima Café
Módulo..........: Dashboard
Arquivo.........: insights_service.py

Descrição.......:
Serviço responsável pela geração automática dos Insights exibidos
no Dashboard Principal.

Versão..........: 1.0
===============================================================================
"""


class InsightsService:
    """
    Gera interpretações automáticas dos indicadores climáticos.
    """

    def get_insights(self, kpis):

        insights = []

        temperatura = kpis.get("temperature", 0)
        precipitacao = kpis.get("precipitation", 0)
        umidade = kpis.get("humidity", 0)
        vento = kpis.get("wind_speed", 0)

        indice = kpis.get("indice_agroclima", 0)
        classificacao = kpis.get("classificacao_agroclima", "--")

        # ==========================================================
        # ÍNDICE AGROCLIMA
        # ==========================================================

        insights.append({

            "level": "primary",

            "icon": "bi-speedometer2",

            "title": "Índice AgroClima",

            "message": (
                f"Situação atual classificada como "
                f"{classificacao} (Índice {indice})."
            )

        })

        # ==========================================================
        # TEMPERATURA
        # ==========================================================

        if temperatura <= 5:

            insights.append({

                "level": "danger",

                "icon": "bi-thermometer-snow",

                "title": "Temperatura crítica",

                "message": (
                    "Condições favoráveis à ocorrência de geadas."
                )

            })

        elif temperatura <= 18:

            insights.append({

                "level": "success",

                "icon": "bi-thermometer-half",

                "title": "Temperatura favorável",

                "message": (
                    "Faixa adequada ao desenvolvimento do cafeeiro."
                )

            })

        elif temperatura >= 32:

            insights.append({

                "level": "warning",

                "icon": "bi-sun",

                "title": "Temperatura elevada",

                "message": (
                    "Pode ocorrer estresse térmico na cultura."
                )

            })

        # ==========================================================
        # PRECIPITAÇÃO
        # ==========================================================

        if precipitacao >= 40:

            insights.append({

                "level": "info",

                "icon": "bi-cloud-rain-heavy",

                "title": "Elevada precipitação",

                "message": (
                    "Monitorar drenagem e possíveis doenças fúngicas."
                )

            })

        elif precipitacao == 0:

            insights.append({

                "level": "warning",

                "icon": "bi-cloud-slash",

                "title": "Ausência de chuva",

                "message": (
                    "Avaliar necessidade de irrigação."
                )

            })

        # ==========================================================
        # UMIDADE
        # ==========================================================

        if umidade < 40:

            insights.append({

                "level": "warning",

                "icon": "bi-droplet-half",

                "title": "Baixa umidade",

                "message": (
                    "Condição favorável ao estresse hídrico."
                )

            })

        elif umidade > 85:

            insights.append({

                "level": "info",

                "icon": "bi-droplet-fill",

                "title": "Alta umidade",

                "message": (
                    "Aumenta a probabilidade de doenças fúngicas."
                )

            })

        # ==========================================================
        # VENTO
        # ==========================================================

        if vento >= 40:

            insights.append({

                "level": "warning",

                "icon": "bi-wind",

                "title": "Ventos intensos",

                "message": (
                    "Recomenda-se monitorar possíveis danos às plantas."
                )

            })

        # ==========================================================
        # SEM INSIGHTS
        # ==========================================================

        if not insights:

            insights.append({

                "level": "success",

                "icon": "bi-check-circle",

                "title": "Situação estável",

                "message": (
                    "Nenhuma condição crítica identificada."
                )

            })

        return insights