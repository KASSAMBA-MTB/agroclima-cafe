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

Versão..........: 2.0
===============================================================================
"""

from typing import Dict, List, Any


class InsightsService:
    """
    Serviço responsável por interpretar os indicadores climáticos
    e produzir insights utilizados pelo Dashboard.
    """

    def get_insights(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gera automaticamente uma lista de insights a partir dos KPIs.

        Parameters
        ----------
        kpis : dict
            Indicadores climáticos calculados pelo DashboardService.

        Returns
        -------
        list
            Lista de insights.
        """

        insights = []

        temperatura = float(kpis.get("temperature", 0))
        precipitacao = float(kpis.get("precipitation", 0))
        umidade = float(kpis.get("humidity", 0))
        vento = float(kpis.get("wind_speed", 0))
        altitude = float(kpis.get("altitude", 0))

        indice = float(kpis.get("indice_agroclima", 0))
        classificacao = kpis.get(
            "classificacao_agroclima",
            "Indefinida"
        )

        # ==========================================================
        # ÍNDICE AGROCLIMA
        # ==========================================================

        insights.append({

            "level": "primary",

            "icon": "bi-speedometer2",

            "title": "Índice AgroClima",

            "message": (
                f"Situação atual classificada como "
                f"{classificacao} (Índice {indice:.1f})."
            )

        })

        # ==========================================================
        # TEMPERATURA
        # ==========================================================

        if temperatura <= 2:

            insights.append({

                "level": "danger",

                "icon": "bi-thermometer-snow",

                "title": "Risco elevado de geada",

                "message": (
                    "Temperaturas muito baixas podem provocar danos "
                    "às lavouras de café."
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
                    "Pode ocorrer estresse térmico nas plantas."
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
                    "Maior probabilidade de doenças fúngicas."
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
                    "Monitorar possíveis danos às plantas."
                )

            })

        # ==========================================================
        # ALTITUDE
        # ==========================================================

        if altitude >= 1200:

            insights.append({

                "level": "info",

                "icon": "bi-triangle",

                "title": "Região de altitude elevada",

                "message": (
                    "Áreas acima de 1.200 metros apresentam maior "
                    "suscetibilidade à ocorrência de geadas."
                )

            })

        # ==========================================================
        # CLASSIFICAÇÃO DO ÍNDICE AGROCLIMA
        # ==========================================================

        if indice >= 80:

            insights.append({

                "level": "success",

                "icon": "bi-award",

                "title": "Excelente condição climática",

                "message": (
                    "O Índice AgroClima indica cenário altamente "
                    "favorável para o cafeeiro."
                )

            })

        elif indice < 50:

            insights.append({

                "level": "danger",

                "icon": "bi-exclamation-octagon",

                "title": "Condição climática desfavorável",

                "message": (
                    "Recomenda-se acompanhamento intensivo da lavoura."
                )

            })

        # ==========================================================
        # SITUAÇÃO ESTÁVEL
        # ==========================================================

        if len(insights) == 1:

            insights.append({

                "level": "success",

                "icon": "bi-check-circle",

                "title": "Situação estável",

                "message": (
                    "Nenhuma condição crítica foi identificada no momento."
                )

            })

        return insights